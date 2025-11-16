import os
import time
from typing import Optional, Literal, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents, update_document_by_id, update_documents
from schemas import VideoRequest, Conversation, ChatMessage

app = FastAPI(title="AI Video + Volt Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GeneratePayload(BaseModel):
    prompt: str
    model: Literal["sora2", "veo3"]
    duration_seconds: int = 5
    aspect_ratio: str = "16:9"


class CreateConversationPayload(BaseModel):
    title: Optional[str] = None
    created_by: Optional[str] = None


class SendMessagePayload(BaseModel):
    content: str


@app.get("/")
def read_root():
    return {"message": "Backend Ready: Video Generator + Volt Chat"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, 'name', '✅ Connected')
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# -------------------- Video generation (existing) --------------------

def _simulate_thumbnail(video_url: str) -> str:
    # In a real integration, you would request/generate a thumbnail
    return video_url + "#thumb.jpg"


def process_veo3_job(request_id: str, payload: GeneratePayload):
    """Simulate Veo3 job submission and completion using an API key from env.
    Replace this with a real provider SDK/HTTP flow when available.
    """
    try:
        api_key = os.getenv("VEO3_API_KEY")
        if not api_key:
            update_document_by_id(
                "videorequest",
                request_id,
                {"status": "failed", "error": "VEO3_API_KEY not configured on server"}
            )
            return

        # Mark as processing
        update_document_by_id("videorequest", request_id, {"status": "processing"})

        # Simulate network/processing latency
        time.sleep(2)

        # Here you would call the real Veo3 API using `api_key` and `payload`
        # For now we simulate a successful generation with a mock URL
        mock_video_url = f"https://cdn.example.com/generated/{request_id}.mp4"
        mock_thumb_url = _simulate_thumbnail(mock_video_url)

        update_document_by_id(
            "videorequest",
            request_id,
            {
                "status": "completed",
                "generated_url": mock_video_url,
                "thumbnail_url": mock_thumb_url,
                "error": None,
            },
        )
    except Exception as e:
        update_document_by_id(
            "videorequest",
            request_id,
            {"status": "failed", "error": str(e)[:500]},
        )


@app.post("/api/generate")
def queue_generation(payload: GeneratePayload, background: BackgroundTasks):
    """
    Queue a video generation job. When model is 'veo3', we trigger a background task
    that simulates a provider call using an API key from the environment.
    """
    try:
        record = VideoRequest(
            prompt=payload.prompt,
            model=payload.model,
            duration_seconds=payload.duration_seconds,
            aspect_ratio=payload.aspect_ratio,
            status="queued",
        )
        inserted_id = create_document("videorequest", record)

        # Kick off background processing per model
        if payload.model == "veo3":
            background.add_task(process_veo3_job, inserted_id, payload)
        # For sora2, keep it queued for now (reserved for future integration)

        return {"request_id": inserted_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/requests")
def list_requests(limit: int = 20):
    try:
        docs = get_documents("videorequest", {}, limit)
        # Convert ObjectId to string for JSON
        for d in docs:
            if "_id" in d and isinstance(d["_id"], ObjectId):
                d["_id"] = str(d["_id"])
            # Convert datetimes to isoformat if present
            for k in ["created_at", "updated_at"]:
                if k in d and hasattr(d[k], "isoformat"):
                    d[k] = d[k].isoformat()
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


# -------------------- Volt Chatbot --------------------

def _oid(oid_str: str) -> ObjectId:
    try:
        return ObjectId(oid_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation id")


def process_volt_reply(conversation_id: str, user_text: str):
    """Generate a lightweight assistant reply for Volt.
    This simulates an AI model; replace with a real LLM provider when desired.
    """
    try:
        # Optional: simulate thinking time
        time.sleep(0.8)

        # Simple, friendly heuristic reply
        prefix = "⚡ Volt"
        guidance = (
            "I’m your open-source AI co-pilot. I can help with creative prompts,"
            " coding tips, and product ideas. Ask me anything!"
        )
        if len(user_text.strip()) < 4:
            reply = f"{prefix}: Could you share a bit more detail? {guidance}"
        elif any(k in user_text.lower() for k in ["help", "what can you do", "commands", "features"]):
            reply = (
                f"{prefix}: Here’s what I can do right now:\n"
                "- Brainstorm prompts for your video generator (Veo3/Sora2).\n"
                "- Explain code and APIs in simple terms.\n"
                "- Outline product ideas and next steps.\n"
                "- Keep track of our chat in this conversation."
            )
        else:
            reply = f"{prefix}: {user_text.strip()} — interesting! Here’s a concise suggestion: " \
                    f"break it into steps, try a quick prototype, and iterate. I can sketch steps if you want."

        # Store assistant message
        create_document("chatmessage", ChatMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=reply,
        ))
    except Exception as e:
        # Store failure as assistant message to surface errors in the UI
        create_document("chatmessage", ChatMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=f"⚡ Volt: Oops, I hit an error: {str(e)[:300]}",
        ))


@app.post("/api/chat/conversations")
def create_conversation(payload: CreateConversationPayload):
    title = payload.title or "New Chat"
    conv = Conversation(title=title, created_by=payload.created_by)
    conv_id = create_document("conversation", conv)
    # Seed with a greeting from Volt
    greeting = (
        "⚡ Volt: Hi! I’m Volt, an open-source AI chat companion. "
        "Tell me what you’re building and I’ll help you plan, write, and ship."
    )
    create_document("chatmessage", ChatMessage(
        conversation_id=conv_id,
        role="assistant",
        content=greeting,
    ))
    return {"conversation_id": conv_id, "title": title}


@app.get("/api/chat/conversations")
def list_conversations(limit: int = 20):
    docs = get_documents("conversation", {}, limit)
    for d in docs:
        if "_id" in d and isinstance(d["_id"], ObjectId):
            d["_id"] = str(d["_id"])
        for k in ["created_at", "updated_at"]:
            if k in d and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
    return {"items": docs}


@app.get("/api/chat/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str, limit: int = 100):
    docs = get_documents("chatmessage", {"conversation_id": conversation_id}, limit)
    for d in docs:
        if "_id" in d and isinstance(d["_id"], ObjectId):
            d["_id"] = str(d["_id"])
        for k in ["created_at", "updated_at"]:
            if k in d and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
    # Sort by created_at if present
    docs.sort(key=lambda x: x.get("created_at", 0))
    return {"items": docs}


@app.post("/api/chat/conversations/{conversation_id}/messages")
def send_message(conversation_id: str, payload: SendMessagePayload, background: BackgroundTasks):
    # Ensure conversation exists (simple check)
    try:
        _ = db["conversation"].find_one({"_id": _oid(conversation_id)})
        if _ is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation id")

    # Store user message
    create_document("chatmessage", ChatMessage(
        conversation_id=conversation_id,
        role="user",
        content=payload.content,
    ))

    # Trigger assistant response
    background.add_task(process_volt_reply, conversation_id, payload.content)

    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
