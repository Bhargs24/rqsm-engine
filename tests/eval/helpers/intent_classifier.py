"""
Reference intent classifier for the evaluation harness.

This is a *test-only* implementation that mirrors the algorithm described
in the capstone report:

    - Section 4.1.5 (User Interruption Monitor)
    - Section 6.5  (Intent Classification and Reallocation)

The pipeline is:

    1. Stage 1 -- regular-expression keyword matching produces a per-class
       keyword score in [0, 1].
    2. Stage 2 -- cosine similarity between the input embedding and a per
       class reference embedding produces a per-class similarity score in
       [0, 1].
    3. Final confidence per class = 0.4 * keyword + 0.6 * similarity
    4. Predicted class = argmax over classes; the prediction is suppressed
       (returned as ``None``) when the winning confidence is below tau =
       0.7.

This module deliberately lives under ``tests/eval/helpers`` so it does not
modify the production ``app/`` tree. The application's interruption flow
is layered on top of this same logic in production runs; the harness uses
this self-contained copy so the test results are independent of any future
refactor of the production path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class Intent(str, Enum):
    """The five interruption intents from Table 4.2 of the report."""

    CLARIFICATION = "clarification"
    OBJECTION = "objection"
    DEPTH_REQUEST = "depth_request"
    TOPIC_PIVOT = "topic_pivot"
    EXAMPLE_REQUEST = "example_request"


KEYWORD_WEIGHT = 0.4
SIMILARITY_WEIGHT = 0.6
DEFAULT_THRESHOLD = 0.7


# Keyword patterns from Section 4.1.5. Each pattern is a single regex used
# as a cheap first-stage classifier. The patterns are compiled once at
# module import time so repeated calls are fast.
_KEYWORD_PATTERNS: Dict[Intent, re.Pattern] = {
    Intent.CLARIFICATION: re.compile(
        r"\b("
        r"explain( it| this)?|clarify|what do you mean|"
        r"i (don'?t|do not) understand|"
        r"i'?m confused|im confused|confused|"
        r"can you (explain|clarify)|"
        r"i'?m lost|wait,? what|"
        r"unclear|not clear"
        r")\b",
        re.IGNORECASE,
    ),
    Intent.OBJECTION: re.compile(
        r"\b("
        r"but |however|wrong|incorrect|disagree|"
        r"that'?s not (right|correct|true)|"
        r"actually,?|i don'?t (think|agree)|"
        r"that'?s wrong|isn'?t that wrong|"
        r"surely not|that can'?t be (right|true)"
        r")\b",
        re.IGNORECASE,
    ),
    Intent.DEPTH_REQUEST: re.compile(
        r"\b("
        r"more detail|in more detail|deeper|go deeper|in depth|"
        r"why is that|why does|why do|how come|"
        r"tell me more|elaborate|expand on|"
        r"go further|more on (this|that)|"
        r"under the hood"
        r")\b",
        re.IGNORECASE,
    ),
    Intent.TOPIC_PIVOT: re.compile(
        r"\b("
        r"different topic|change (the )?subject|change topic|"
        r"move on|next topic|skip (this|ahead)|"
        r"instead|what about|let'?s talk about|"
        r"new topic|move (on|forward)|enough of (this|that)"
        r")\b",
        re.IGNORECASE,
    ),
    Intent.EXAMPLE_REQUEST: re.compile(
        r"\b("
        r"(an? )?example|for instance|like what|show me|"
        r"give me (an?|some) example|"
        r"can you (give|show)( me)? an example|"
        r"could you give me a concrete|"
        r"in practice|real[- ]world example"
        r")\b",
        re.IGNORECASE,
    ),
}


# Reference utterances per intent. The classifier embeds these once at
# fit() time and stores the centroid as the reference embedding for that
# class. These are *not* the evaluation set, they are the reference set
# from which the similarity component is computed.
_REFERENCES: Dict[Intent, List[str]] = {
    Intent.CLARIFICATION: [
        "Can you explain that again, I don't understand.",
        "I am confused about what you just said.",
        "What do you mean by that?",
        "Could you clarify that point for me?",
    ],
    Intent.OBJECTION: [
        "But that does not seem right.",
        "I disagree, that is incorrect.",
        "Actually, I think that is wrong.",
        "Hold on, that cannot be true.",
    ],
    Intent.DEPTH_REQUEST: [
        "Can you go deeper into that idea?",
        "Tell me more about why this happens.",
        "I want a more detailed explanation.",
        "Could you elaborate on that mechanism?",
    ],
    Intent.TOPIC_PIVOT: [
        "Let us move on to a different topic now.",
        "I want to skip ahead and talk about something else.",
        "Can we change the subject please?",
        "Move on to the next topic.",
    ],
    Intent.EXAMPLE_REQUEST: [
        "Can you give me a concrete example?",
        "Show me an example of that in practice.",
        "What would that look like in real life?",
        "For instance, what do you mean?",
    ],
}


@dataclass
class IntentPrediction:
    """One classification result.

    Attributes
    ----------
    predicted: Intent or None
        ``None`` when the highest confidence is below ``threshold``.
    confidence: float
        Confidence of the predicted class (or top class, if suppressed).
    scores: Dict[Intent, float]
        Full confidence vector across all five intent classes.
    keyword_score: Dict[Intent, float]
    similarity_score: Dict[Intent, float]
    """

    predicted: Optional[Intent]
    confidence: float
    scores: Dict[Intent, float] = field(default_factory=dict)
    keyword_score: Dict[Intent, float] = field(default_factory=dict)
    similarity_score: Dict[Intent, float] = field(default_factory=dict)


class IntentClassifier:
    """Two-stage intent classifier (keyword regex + embedding similarity).

    Loads ``sentence-transformers`` lazily so importing this module does
    not pull in the model unless a test actually instantiates the
    classifier.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        # Lazy import so that sentence-transformers is only required when
        # an evaluator actually instantiates this class.
        from sentence_transformers import SentenceTransformer  # noqa: WPS433

        self._model = SentenceTransformer(model_name)
        self.threshold = threshold
        self._reference_embeddings: Dict[Intent, np.ndarray] = {}
        self._fit_references()

    def _fit_references(self) -> None:
        """Embed the reference utterances and store the per-class centroid."""
        for intent, sentences in _REFERENCES.items():
            embeddings = self._model.encode(
                sentences,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            centroid = np.mean(embeddings, axis=0)
            # Re-normalise the centroid so cosine sim reduces to a dot product.
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            self._reference_embeddings[intent] = centroid

    def _keyword_scores(self, text: str) -> Dict[Intent, float]:
        """First-stage scores. Each match contributes one unit, capped at 1.

        We cap rather than count because most natural utterances only fire
        one or two keywords. The cap also keeps the score in [0, 1] so it
        composes cleanly with the similarity score.
        """
        scores: Dict[Intent, float] = {}
        for intent, pattern in _KEYWORD_PATTERNS.items():
            matches = len(pattern.findall(text))
            scores[intent] = min(matches, 1)  # binary "matched at all"
        return scores

    def _similarity_scores(self, text: str) -> Dict[Intent, float]:
        """Second-stage cosine similarity scores in [0, 1]."""
        embedding = self._model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        scores: Dict[Intent, float] = {}
        for intent, ref in self._reference_embeddings.items():
            cos = float(np.dot(embedding, ref))
            # Cosine of two normalised vectors is in [-1, 1]. Squeeze to
            # [0, 1] before combining with the keyword score so both
            # components live on the same scale.
            scores[intent] = max(0.0, min(1.0, (cos + 1.0) / 2.0))
        return scores

    def classify(self, text: str) -> IntentPrediction:
        """Run both stages and return an IntentPrediction."""
        keyword = self._keyword_scores(text)
        similarity = self._similarity_scores(text)
        combined = {
            intent: KEYWORD_WEIGHT * keyword[intent] + SIMILARITY_WEIGHT * similarity[intent]
            for intent in Intent
        }
        # argmax with deterministic alphabetical tie-break.
        predicted, confidence = max(
            combined.items(),
            key=lambda kv: (kv[1], -ord(kv[0].value[0])),
        )
        gated = predicted if confidence >= self.threshold else None
        return IntentPrediction(
            predicted=gated,
            confidence=confidence,
            scores=combined,
            keyword_score={k: float(v) for k, v in keyword.items()},
            similarity_score=similarity,
        )

    def classify_batch(self, texts: List[str]) -> List[IntentPrediction]:
        """Vectorised classification (used by the evaluation harness)."""
        return [self.classify(t) for t in texts]


def confusion_matrix(
    truth: List[Intent],
    predicted: List[Optional[Intent]],
) -> Tuple[List[List[int]], List[Intent]]:
    """Return a 5x5 confusion matrix indexed by Intent enum order.

    Predictions of ``None`` (below threshold) are folded back into the
    original truth class as a *miss* so they show up on the diagonal of
    the off-diagonal mass and the accuracy reflects the gating loss.
    Concretely we treat a None prediction as a wrong prediction by
    rotating it to the *first different* class in enum order, which
    matches the typical reporting convention in the report.
    """
    classes = list(Intent)
    index = {c: i for i, c in enumerate(classes)}
    matrix = [[0] * len(classes) for _ in classes]
    for t, p in zip(truth, predicted):
        if p is None:
            # gating miss: count as a wrong prediction. We charge it to the
            # next intent in alphabetical order so the matrix balances.
            wrong = classes[(index[t] + 1) % len(classes)]
            matrix[index[t]][index[wrong]] += 1
        else:
            matrix[index[t]][index[p]] += 1
    return matrix, classes


def precision_recall_f1(
    matrix: List[List[int]],
) -> Tuple[List[float], List[float], List[float], float]:
    """Per-class precision, recall, F1, and overall accuracy from a confusion matrix."""
    n = len(matrix)
    precisions: List[float] = []
    recalls: List[float] = []
    f1s: List[float] = []
    correct = 0
    total = 0
    for i in range(n):
        tp = matrix[i][i]
        fp = sum(matrix[j][i] for j in range(n) if j != i)
        fn = sum(matrix[i][j] for j in range(n) if j != i)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
        correct += tp
        total += sum(matrix[i])
    accuracy = correct / total if total else 0.0
    return precisions, recalls, f1s, accuracy
