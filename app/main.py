"""
RQSM-Engine FastAPI Application
Main entry point for the web service
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import asyncio
import sys
from pathlib import Path

from app.config import settings
from app import __version__
from app.session.runtime import ConversationRuntime
from app.api.models import (
    SessionCreateResponse, StartConversationResponse, UserMessageRequest,
    UserMessageResponse, InterruptRequest, InterruptResponse,
    InterruptMessageRequest, InterruptMessageResponse, ResumeRequest,
    ResumeResponse, NextUnitRequest, NextUnitResponse, SessionStateResponse
)


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/rqsm_engine.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting RQSM-Engine v{__version__}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.app_debug}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Temperature: {settings.llm_temperature}")
    logger.info("=" * 60)
    
    # Ensure required directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("sample_docs").mkdir(exist_ok=True)
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RQSM-Engine")
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="RQSM-Engine API",
    description="Role Queue State Machine Educational Dialogue System",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "name": "RQSM-Engine API",
        "version": __version__,
        "status": "operational",
        "environment": settings.app_env
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.app_env
    }


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive values only)"""
    return {
        "llm_provider": settings.llm_provider,
        "llm_temperature": settings.llm_temperature,
        "llm_max_tokens": settings.llm_max_tokens,
        "role_score_weights": {
            "alpha": settings.role_score_alpha,
            "beta": settings.role_score_beta,
            "gamma": settings.role_score_gamma
        },
        "state_machine": {
            "transition_delay_turns": settings.transition_delay_turns,
            "hysteresis_window_turns": settings.hysteresis_window_turns,
            "reallocation_threshold": settings.reallocation_threshold
        },
        "session": {
            "max_context_window": settings.max_context_window,
            "session_timeout_minutes": settings.session_timeout_minutes
        }
    }


# Initialize conversation runtime singleton
_runtime = ConversationRuntime()


# ============================================================================
# Session Management Endpoints
# ============================================================================

@app.post("/sessions/document", response_model=SessionCreateResponse)
async def create_session_from_document(file: UploadFile = File(...)):
    """
    Upload a document and create a new conversation session.
    Returns session_id for use in subsequent requests.
    """
    try:
        logger.info(f"Upload endpoint received: {file.filename}")
        session = await asyncio.to_thread(_runtime.create_session_from_uploaded_file, file)
        logger.info(f"Created session {session.session_id} from document {file.filename}")
        summary = session.document_summary or {}
        section_counts = {
            section_name: section_data.get("count", 0)
            for section_name, section_data in summary.get("sections", {}).items()
        }

        unit_previews = []
        for unit in session.semantic_units[:3]:
            preview_text = " ".join(unit.text.split())[:220]
            unit_previews.append(
                {
                    "index": unit.position,
                    "title": unit.title or "Untitled",
                    "word_count": unit.word_count,
                    "section_type": unit.document_section,
                    "preview": preview_text,
                }
            )

        return SessionCreateResponse(
            session_id=session.session_id,
            filename=session.filename,
            total_units=session.state_machine.context.total_units,
            roles_assigned=len(session.assignments_by_position),
            state=session.state_machine.get_state_summary(),
            insights={
                "total_words": int(summary.get("total_words", 0)),
                "avg_words_per_unit": float(summary.get("avg_words_per_unit", 0)),
                "avg_cohesion": float(summary.get("avg_cohesion", 0)),
                "sections": section_counts,
                "unit_previews": unit_previews,
            },
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/start", response_model=StartConversationResponse)
async def start_conversation(session_id: str):
    """
    Start the conversation for a session. Assigns roles and initializes state machine.
    """
    try:
        logger.info(f"Starting conversation for session {session_id}...")
        response = await asyncio.to_thread(_runtime.start_conversation, session_id)
        logger.info(f"Conversation started for session {session_id}")
        return StartConversationResponse(**response)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/message", response_model=UserMessageResponse)
async def send_user_message(session_id: str, request: UserMessageRequest):
    """
    Send a user message and get bot response.
    """
    try:
        logger.info(f"User message for session {session_id}: {request.message[:80]}")
        response = await asyncio.to_thread(_runtime.send_user_message, session_id, request.message)
        return UserMessageResponse(**response)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/interrupt", response_model=InterruptResponse)
async def interrupt_conversation(session_id: str, request: InterruptRequest = None):
    """
    Interrupt the current topic. User can then ask a question.
    """
    try:
        response = _runtime.interrupt(session_id)
        logger.info(f"Interrupted session {session_id}")
        return InterruptResponse(**response)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Error interrupting: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/interrupt/message", response_model=InterruptMessageResponse)
async def answer_interruption_question(session_id: str, request: InterruptMessageRequest):
    """
    Answer an interruption question and get bot response.
    """
    try:
        logger.info(f"Interruption answer for session {session_id}")
        response = await asyncio.to_thread(_runtime.answer_interruption, session_id, request.message)
        return InterruptMessageResponse(**response)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Error answering interruption: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/resume", response_model=ResumeResponse)
async def resume_conversation(session_id: str, request: ResumeRequest):
    """
    Resume conversation after interruption.
    from_start=True: restart this topic
    from_start=False: continue from where we left off
    """
    try:
        response = _runtime.resume(session_id, request.from_start)
        logger.info(f"Resumed session {session_id} (from_start={request.from_start})")
        return ResumeResponse(**response)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Error resuming: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/next", response_model=NextUnitResponse)
async def advance_to_next_unit(session_id: str, request: NextUnitRequest = None):
    """
    Advance conversation to the next topic/unit.
    """
    try:
        logger.info(f"Advancing to next unit for session {session_id}...")
        response = await asyncio.to_thread(_runtime.advance_to_next_unit, session_id)
        logger.info(f"Advanced session {session_id} to next unit")
        return NextUnitResponse(**response)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Error advancing to next unit: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sessions/{session_id}", response_model=SessionStateResponse)
async def get_session_state(session_id: str):
    """
    Get the current state of a session.
    """
    try:
        state = _runtime.get_session_state(session_id)
        return SessionStateResponse(**state)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Error getting session state: {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting development server on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )
