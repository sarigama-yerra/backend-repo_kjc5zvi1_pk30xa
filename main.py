import os
import time
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents, update_document_by_id
from schemas import VideoRequest

app = FastAPI(title="AI Video Generator API")

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


@app.get("/")
def read_root():
    return {"message": "AI Video Generator Backend Ready"}


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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
