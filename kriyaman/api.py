import sys
import os
import shutil
import urllib.parse
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure the backend directory is in the path to support import from server modules if needed
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from kriyaman.services.memory import MemoryService
from kriyaman.services.knowledge import KnowledgeService
from kriyaman.services.runtime import RuntimeService



load_dotenv()

app = FastAPI()

# CORS — allow the Streamlit frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Config ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Instantiate services
memory_service = MemoryService(base_upload_dir="data/docs")
knowledge_service = KnowledgeService(vector_db_path="data/vectordb")
runtime_service = RuntimeService()

class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/query")
def query_rag(req: QueryRequest):
    # Route query via the RuntimeService and ResearchAgent
    agent_response = runtime_service.execute_agent(
        name="research",
        query=req.query,
        session_id=req.session_id
    )
    return agent_response.to_dict()

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form("default")
):
    # Retrieve session workspace directory from memory_service
    session_dir = memory_service.get_session_dir(session_id)
    file_path = os.path.join(session_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Ingest documents using knowledge_service
    docs_ingested = knowledge_service.ingest_documents(session_dir, session_id)

    return {
        "status": "success",
        "filename": file.filename,
        "docs_ingested": docs_ingested,
        "session_id": session_id
    }

@app.get("/login")
def login_with_google():
    redirect_uri = f"{BACKEND_URL}/auth/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online"
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@app.get("/auth/callback")
def auth_callback(code: str):
    redirect_uri = f"{BACKEND_URL}/auth/callback"

    # Exchange code for token
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    )
    res_json = token_response.json()
    id_token = res_json.get("id_token")

    if id_token:
        return RedirectResponse(url=f"{FRONTEND_URL}/?token={id_token}")
    else:
        return {"error": "Authentication failed", "details": res_json}

@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    # Clear uploaded documents from memory service
    memory_cleared = memory_service.clear_session_memory(session_id)

    # Delete Chroma collection from knowledge service
    db_cleared = knowledge_service.delete_collection(session_id)

    return {
        "status": "success",
        "message": f"Session {session_id} deleted.",
        "memory_cleared": memory_cleared,
        "database_cleared": db_cleared
    }
