# API Design Document

## Document-Segment Driven Role-Oriented Conversational Study System (RQSM-Engine)

**Version:** 1.0  
**Date:** January 29, 2026  
**Framework:** FastAPI  
**Purpose:** RESTful API specification for RQSM-Engine

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Core Endpoints](#core-endpoints)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Usage Examples](#usage-examples)
7. [WebSocket Support](#websocket-support)

---

## API Overview

### Base URL
```
Development: http://localhost:8000
Production: https://api.rqsm-engine.com
```

### API Version
```
v1: /api/v1/
```

### Content Type
```
Content-Type: application/json
Accept: application/json
```

### HTTP Methods
- `GET` - Retrieve resources
- `POST` - Create resources or execute actions
- `PUT` - Update resources
- `DELETE` - Remove resources

---

## Authentication

### MVP: No Authentication
For capstone MVP, authentication is not required.

### Future: JWT-Based Authentication
```http
POST /api/v1/auth/login
Authorization: Bearer <jwt_token>
```

---

## Core Endpoints

### 1. Document Upload

**Endpoint**: `POST /api/v1/documents/upload`

**Purpose**: Upload a document for processing

**Request**:
```http
POST /api/v1/documents/upload HTTP/1.1
Content-Type: multipart/form-data

file: <binary_file_data>
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@chapter1.pdf"
```

**Response**:
```json
{
  "document_id": "doc_abc123",
  "filename": "chapter1.pdf",
  "size_bytes": 524288,
  "status": "uploaded",
  "created_at": "2026-01-29T10:30:00Z"
}
```

**Status Codes**:
- `201 Created` - Document uploaded successfully
- `400 Bad Request` - Invalid file format
- `413 Payload Too Large` - File exceeds size limit
- `500 Internal Server Error` - Processing error

---

### 2. Process Document

**Endpoint**: `POST /api/v1/documents/{document_id}/process`

**Purpose**: Process document into semantic units and assign roles

**Request**:
```http
POST /api/v1/documents/doc_abc123/process HTTP/1.1
Content-Type: application/json

{
  "similarity_threshold": 0.75,
  "min_unit_words": 50,
  "max_unit_words": 500
}
```

**Response**:
```json
{
  "document_id": "doc_abc123",
  "status": "processed",
  "semantic_units": [
    {
      "id": "S1",
      "title": "Introduction",
      "text": "This chapter introduces...",
      "document_section": "introduction",
      "word_count": 150,
      "similarity_score": 0.87
    },
    {
      "id": "S2",
      "title": "Methods",
      "text": "Our approach involves...",
      "document_section": "methodology",
      "word_count": 200,
      "similarity_score": 0.82
    }
  ],
  "role_assignments": {
    "S1": {
      "queue": ["Summarizer", "Explainer", "Example-Generator", "Challenger", "Misconception-Spotter"],
      "scores": {
        "Summarizer": 8.7,
        "Explainer": 8.2,
        "Challenger": 6.5,
        "Example-Generator": 7.1,
        "Misconception-Spotter": 7.8
      }
    },
    "S2": {
      "queue": ["Explainer", "Misconception-Spotter", "Example-Generator", "Summarizer", "Challenger"],
      "scores": { }
    }
  },
  "total_segments": 2,
  "processed_at": "2026-01-29T10:31:00Z"
}
```

**Status Codes**:
- `200 OK` - Document processed successfully
- `404 Not Found` - Document ID not found
- `422 Unprocessable Entity` - Invalid parameters
- `500 Internal Server Error` - Processing error

---

### 3. Start Session

**Endpoint**: `POST /api/v1/sessions/start`

**Purpose**: Initialize a new dialogue session

**Request**:
```http
POST /api/v1/sessions/start HTTP/1.1
Content-Type: application/json

{
  "document_id": "doc_abc123",
  "llm_config": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.0,
    "max_tokens": 500
  }
}
```

**Response**:
```json
{
  "session_id": "sess_xyz789",
  "document_id": "doc_abc123",
  "status": "active",
  "current_segment_id": "S1",
  "current_role": "Summarizer",
  "turn_number": 0,
  "started_at": "2026-01-29T10:32:00Z"
}
```

**Status Codes**:
- `201 Created` - Session started
- `404 Not Found` - Document not processed
- `409 Conflict` - Active session already exists

---

### 4. Get Next Turn

**Endpoint**: `POST /api/v1/sessions/{session_id}/next`

**Purpose**: Advance dialogue to next role and generate response

**Request**:
```http
POST /api/v1/sessions/sess_xyz789/next HTTP/1.1
Content-Type: application/json

{
  "context_window": 5
}
```

**Response**:
```json
{
  "session_id": "sess_xyz789",
  "turn": {
    "turn_number": 1,
    "segment_id": "S1",
    "role": {
      "name": "Summarizer",
      "type": "Summarizer"
    },
    "message": "Let me summarize the key points from this introduction...",
    "timestamp": "2026-01-29T10:32:30Z",
    "metadata": {
      "role_index": 0,
      "segment_index": 0,
      "tokens_used": 127
    }
  },
  "next_role": "Explainer",
  "dialogue_complete": false
}
```

**Status Codes**:
- `200 OK` - Turn generated
- `404 Not Found` - Session not found
- `410 Gone` - Dialogue already complete
- `500 Internal Server Error` - Generation error

---

### 5. Handle Interruption

**Endpoint**: `POST /api/v1/sessions/{session_id}/interrupt`

**Purpose**: Process user interruption and reallocate roles

**Request**:
```http
POST /api/v1/sessions/sess_xyz789/interrupt HTTP/1.1
Content-Type: application/json

{
  "user_input": "Can you give me an example?",
  "confidence_threshold": 0.7
}
```

**Response**:
```json
{
  "session_id": "sess_xyz789",
  "interruption_processed": true,
  "detected_intent": {
    "intent": "Example Request",
    "confidence": 0.92
  },
  "role_reallocation": {
    "previous_queue": ["Explainer", "Challenger", "Summarizer", "Example-Generator", "Misconception-Spotter"],
    "new_queue": ["Example-Generator", "Explainer", "Summarizer", "Challenger", "Misconception-Spotter"],
    "bounded_delay": 3,
    "hysteresis_applied": true
  },
  "current_role": "Example-Generator",
  "transition_lock": 3,
  "turn": {
    "turn_number": 4,
    "segment_id": "S1",
    "role": {
      "name": "Example-Generator",
      "type": "Example-Generator"
    },
    "message": "Here's a concrete example to illustrate this concept...",
    "timestamp": "2026-01-29T10:35:00Z",
    "is_reallocation": true
  }
}
```

**Status Codes**:
- `200 OK` - Interruption handled
- `400 Bad Request` - Low confidence, not triggered
- `404 Not Found` - Session not found

---

### 6. Get Session History

**Endpoint**: `GET /api/v1/sessions/{session_id}/history`

**Purpose**: Retrieve conversation history

**Query Parameters**:
- `limit` (optional): Number of recent turns (default: 10)
- `segment_id` (optional): Filter by segment

**Request**:
```http
GET /api/v1/sessions/sess_xyz789/history?limit=5 HTTP/1.1
```

**Response**:
```json
{
  "session_id": "sess_xyz789",
  "total_turns": 15,
  "turns": [
    {
      "turn_number": 11,
      "segment_id": "S2",
      "role": "Explainer",
      "message": "Let me explain this methodology...",
      "timestamp": "2026-01-29T10:40:00Z",
      "is_reallocation": false
    },
    {
      "turn_number": 12,
      "segment_id": "S2",
      "role": "Example-Generator",
      "message": "For instance, consider...",
      "timestamp": "2026-01-29T10:40:30Z",
      "is_reallocation": false
    }
  ]
}
```

**Status Codes**:
- `200 OK` - History retrieved
- `404 Not Found` - Session not found

---

### 7. Get Session Status

**Endpoint**: `GET /api/v1/sessions/{session_id}`

**Purpose**: Get current session state

**Request**:
```http
GET /api/v1/sessions/sess_xyz789 HTTP/1.1
```

**Response**:
```json
{
  "session_id": "sess_xyz789",
  "document_id": "doc_abc123",
  "status": "active",
  "current_state": {
    "segment_id": "S2",
    "segment_index": 1,
    "role_index": 2,
    "current_role": "Challenger",
    "turn_number": 13,
    "transition_lock": 0,
    "interruption_detected": false
  },
  "statistics": {
    "total_turns": 13,
    "segments_covered": 2,
    "interruptions": 2,
    "roles_used": ["Summarizer", "Explainer", "Challenger", "Example-Generator", "Misconception-Spotter"]
  },
  "started_at": "2026-01-29T10:32:00Z",
  "updated_at": "2026-01-29T10:42:00Z"
}
```

**Status Codes**:
- `200 OK` - Status retrieved
- `404 Not Found` - Session not found

---

### 8. End Session

**Endpoint**: `DELETE /api/v1/sessions/{session_id}`

**Purpose**: Terminate session and cleanup resources

**Request**:
```http
DELETE /api/v1/sessions/sess_xyz789 HTTP/1.1
```

**Response**:
```json
{
  "session_id": "sess_xyz789",
  "status": "terminated",
  "summary": {
    "total_turns": 25,
    "segments_covered": 3,
    "interruptions": 4,
    "duration_seconds": 600
  },
  "terminated_at": "2026-01-29T10:50:00Z"
}
```

**Status Codes**:
- `200 OK` - Session terminated
- `404 Not Found` - Session not found

---

### 9. List Documents

**Endpoint**: `GET /api/v1/documents`

**Purpose**: List all uploaded documents

**Query Parameters**:
- `status` (optional): Filter by status (uploaded, processed, failed)
- `limit` (optional): Max results (default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Request**:
```http
GET /api/v1/documents?status=processed&limit=10 HTTP/1.1
```

**Response**:
```json
{
  "total": 25,
  "limit": 10,
  "offset": 0,
  "documents": [
    {
      "document_id": "doc_abc123",
      "filename": "chapter1.pdf",
      "status": "processed",
      "semantic_units": 5,
      "created_at": "2026-01-29T10:30:00Z"
    },
    {
      "document_id": "doc_def456",
      "filename": "chapter2.pdf",
      "status": "processed",
      "semantic_units": 7,
      "created_at": "2026-01-29T09:15:00Z"
    }
  ]
}
```

**Status Codes**:
- `200 OK` - Documents retrieved

---

### 10. Health Check

**Endpoint**: `GET /api/v1/health`

**Purpose**: Check API health status

**Request**:
```http
GET /api/v1/health HTTP/1.1
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-29T10:50:00Z",
  "services": {
    "database": "connected",
    "llm_client": "operational",
    "embeddings": "operational"
  }
}
```

**Status Codes**:
- `200 OK` - Healthy
- `503 Service Unavailable` - Unhealthy

---

## Data Models

### Document

```json
{
  "document_id": "string (UUID)",
  "filename": "string",
  "size_bytes": "integer",
  "status": "string (uploaded|processing|processed|failed)",
  "semantic_units": "integer (optional)",
  "created_at": "string (ISO 8601)",
  "processed_at": "string (ISO 8601, optional)",
  "error_message": "string (optional)"
}
```

### Semantic Unit

```json
{
  "id": "string",
  "title": "string (optional)",
  "text": "string",
  "document_section": "string",
  "position": "integer",
  "word_count": "integer",
  "similarity_score": "float (0.0-1.0)",
  "metadata": "object"
}
```

### Role

```json
{
  "name": "string",
  "type": "string (enum)",
  "description": "string",
  "priority_weight": "float"
}
```

### Turn

```json
{
  "turn_number": "integer",
  "segment_id": "string",
  "role": "Role object",
  "message": "string",
  "timestamp": "string (ISO 8601)",
  "is_reallocation": "boolean",
  "metadata": "object"
}
```

### Session

```json
{
  "session_id": "string (UUID)",
  "document_id": "string",
  "status": "string (active|paused|completed|terminated)",
  "current_state": "object",
  "statistics": "object",
  "started_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### Intent

```json
{
  "intent": "string (enum: Clarification|Objection|Topic Pivot|Depth Request|Example Request|Summary Request|Other)",
  "confidence": "float (0.0-1.0)"
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object (optional)",
    "timestamp": "string (ISO 8601)"
  }
}
```

### Error Codes

| HTTP Status | Error Code | Description |
|------------|-----------|-------------|
| 400 | `BAD_REQUEST` | Invalid request parameters |
| 401 | `UNAUTHORIZED` | Authentication required |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource conflict |
| 413 | `PAYLOAD_TOO_LARGE` | File size exceeds limit |
| 422 | `UNPROCESSABLE_ENTITY` | Validation error |
| 429 | `TOO_MANY_REQUESTS` | Rate limit exceeded |
| 500 | `INTERNAL_SERVER_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

### Example Error Response

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Document with ID 'doc_invalid' not found",
    "details": {
      "document_id": "doc_invalid",
      "available_ids": ["doc_abc123", "doc_def456"]
    },
    "timestamp": "2026-01-29T10:55:00Z"
  }
}
```

---

## Usage Examples

### Example 1: Complete Dialogue Workflow

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Step 1: Upload document
with open('chapter1.pdf', 'rb') as f:
    response = requests.post(
        f"{BASE_URL}/documents/upload",
        files={'file': f}
    )
    document_id = response.json()['document_id']

# Step 2: Process document
response = requests.post(
    f"{BASE_URL}/documents/{document_id}/process"
)
print(f"Processed {response.json()['total_segments']} segments")

# Step 3: Start session
response = requests.post(
    f"{BASE_URL}/sessions/start",
    json={'document_id': document_id}
)
session_id = response.json()['session_id']

# Step 4: Generate dialogue
for _ in range(10):
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/next")
    turn = response.json()['turn']
    print(f"[{turn['role']['name']}]: {turn['message']}")
    
    if response.json()['dialogue_complete']:
        break

# Step 5: End session
requests.delete(f"{BASE_URL}/sessions/{session_id}")
```

### Example 2: Handling Interruptions

```python
# During dialogue, user interrupts
response = requests.post(
    f"{BASE_URL}/sessions/{session_id}/interrupt",
    json={'user_input': 'Can you give me an example?'}
)

if response.json()['interruption_processed']:
    intent = response.json()['detected_intent']
    print(f"Intent: {intent['intent']} (confidence: {intent['confidence']})")
    
    turn = response.json()['turn']
    print(f"[{turn['role']['name']}]: {turn['message']}")
```

### Example 3: Retrieving History

```python
# Get recent turns
response = requests.get(
    f"{BASE_URL}/sessions/{session_id}/history",
    params={'limit': 5}
)

history = response.json()
for turn in history['turns']:
    print(f"Turn {turn['turn_number']}: [{turn['role']}] {turn['message'][:50]}...")
```

---

## WebSocket Support (Future Enhancement)

### WebSocket Endpoint

**Endpoint**: `ws://localhost:8000/api/v1/ws/sessions/{session_id}`

**Purpose**: Real-time dialogue streaming

### Connection Flow

```javascript
// Client-side JavaScript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/sessions/sess_xyz789');

ws.onopen = () => {
  console.log('Connected');
  ws.send(JSON.stringify({action: 'next'}));
};

ws.onmessage = (event) => {
  const turn = JSON.parse(event.data);
  console.log(`[${turn.role.name}]: ${turn.message}`);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

### Message Types

**Client → Server**:
```json
{
  "action": "next",
  "payload": {}
}
```

```json
{
  "action": "interrupt",
  "payload": {
    "user_input": "Can you explain more?"
  }
}
```

**Server → Client**:
```json
{
  "type": "turn",
  "payload": {
    "turn_number": 5,
    "role": "Explainer",
    "message": "Let me explain..."
  }
}
```

```json
{
  "type": "reallocation",
  "payload": {
    "intent": "Example Request",
    "new_queue": ["Example-Generator", ...]
  }
}
```

---

## Rate Limiting

### Limits (Future)

| Endpoint | Rate Limit |
|----------|-----------|
| Document Upload | 10 per hour |
| Process Document | 20 per hour |
| Start Session | 50 per hour |
| Next Turn | 1000 per hour |
| Interruption | 500 per hour |

### Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1643472000
```

---

## OpenAPI Specification

### Generate OpenAPI Docs

```bash
# Access interactive API docs
http://localhost:8000/docs

# Access ReDoc
http://localhost:8000/redoc

# Download OpenAPI JSON
http://localhost:8000/openapi.json
```

### Example OpenAPI Schema

```yaml
openapi: 3.0.0
info:
  title: RQSM-Engine API
  version: 1.0.0
  description: Role Queue State Machine Educational Dialogue System

paths:
  /api/v1/documents/upload:
    post:
      summary: Upload Document
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
      responses:
        '201':
          description: Document uploaded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'
        '400':
          description: Bad request
          
components:
  schemas:
    Document:
      type: object
      properties:
        document_id:
          type: string
        filename:
          type: string
        status:
          type: string
```

---

## Implementation Notes

### FastAPI Application Structure

```python
# app/api.py

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="RQSM-Engine API",
    version="1.0.0",
    description="Role Queue State Machine Educational Dialogue System"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    # Implementation
    pass

@app.post("/api/v1/sessions/start")
async def start_session(request: SessionStartRequest):
    # Implementation
    pass

# ... more endpoints
```

### Request/Response Models (Pydantic)

```python
# app/models/api_models.py

from pydantic import BaseModel
from typing import Optional, List

class SessionStartRequest(BaseModel):
    document_id: str
    llm_config: Optional[dict] = None

class TurnResponse(BaseModel):
    session_id: str
    turn: dict
    next_role: str
    dialogue_complete: bool

class InterruptionRequest(BaseModel):
    user_input: str
    confidence_threshold: float = 0.7
```

---

## Security Considerations

### Current (MVP)
- No authentication
- No input validation beyond basic checks
- No rate limiting

### Production Requirements
1. **Authentication**: JWT-based auth
2. **Authorization**: Role-based access control
3. **Input Sanitization**: Validate all inputs
4. **Rate Limiting**: Prevent abuse
5. **HTTPS**: Encrypt all communications
6. **API Keys**: For LLM service calls
7. **File Validation**: Check file types and scan for malware

---

## Conclusion

This API design provides:

1. **RESTful Interface**: Standard HTTP methods and status codes
2. **Clear Contracts**: Well-defined request/response formats
3. **Comprehensive Coverage**: All system operations exposed
4. **Error Handling**: Consistent error responses
5. **Extensibility**: Easy to add new endpoints
6. **Documentation**: OpenAPI/Swagger integration

The API enables external systems to integrate with RQSM-Engine and supports future enhancements like real-time streaming and collaborative features.
