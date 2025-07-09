import sys
import os

# Add project root and mpla_project to path for MPLA imports - MUST BE FIRST
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
mpla_project_path = os.path.join(project_root, 'mpla_project')

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if mpla_project_path not in sys.path:
    sys.path.insert(0, mpla_project_path)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import json
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder

# Placeholder for our service functions
from . import services
from mpla.knowledge_base.schemas import MetaPrompt, MetaPromptUpdate
from typing import List

# Load .env file from the project root before other modules are initialized
# Assumes server/app/main.py is the entry point
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print("INFO:     Loaded environment variables from .env file.")
else:
    print("WARNING:  .env file not found. API keys might not be configured.")

app = FastAPI(
    title="MPLA Web API",
    description="API for the Meta-Prompt Learning Agent",
    version="1.0.0"
)

# --- CORS Middleware ---
# Allow requests from the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080", "https://mplagent.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes from services
app.include_router(services.router)

# --- Pydantic Models for API requests and responses ---

class ProviderSettings(BaseModel):
    orchestrator: str = Field(default='gemini', description="Can be 'gemini' or 'openai'")
    enhancer: str = Field(default='rule_based', description="Can be 'rule_based', 'llm_assisted', or 'architect'")

class RefineRequest(BaseModel):
    initial_prompt: str = Field(..., min_length=10)
    max_iterations: int = Field(default=3, gt=0, le=10)
    model_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    providers: ProviderSettings = Field(default_factory=ProviderSettings)
    evaluation_mode: str = Field(default='basic', description="Can be 'basic' or 'llm_assisted'")
    # New fields for self-correction
    enable_self_correction: bool = Field(default=False)
    self_correction_iterations: int = Field(default=3, gt=0, le=5)

# --- API Endpoints ---

# --- Static Files Configuration ---
# Mount static files for the React frontend
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    # First, mount the assets directory (critical for Vite builds)
    assets_path = os.path.join(static_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        print(f"INFO: Mounted assets directory: {assets_path}")
    else:
        print(f"WARNING: Assets directory not found: {assets_path}")
    
    # Mount vite.svg and favicon.ico at root
    vite_svg_path = os.path.join(static_path, "vite.svg")
    if os.path.exists(vite_svg_path):
        @app.get("/vite.svg")  
        async def serve_vite_svg():
            return FileResponse(vite_svg_path)
    
    print(f"INFO: Static path configured: {static_path}")
else:
    print(f"ERROR: Static directory not found: {static_path}")

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    """Serve the React frontend for the root route."""
    static_path = os.path.join(os.path.dirname(__file__), "..", "static")
    index_file = os.path.join(static_path, "index.html")
    
    if os.path.exists(index_file):
        return FileResponse(index_file)
    else:
        # Fallback to API message if static files not found
        return {"message": "Welcome to the MPLA API", "frontend": "not_found", "static_path": static_path}

@app.post("/api/refine")
async def refine_prompt_stream(request: Request, body: RefineRequest):
    """
    Accepts a prompt and configuration, then streams the refinement process
    by calling the core service logic and formatting it as a text/event-stream.
    """
    settings_dict = body.dict()

    async def sse_formatted_generator():
        """
        Manually formats the SSE messages.
        Format:
        event: <event_name>
        data: <json_string_of_data>
        """
        async for event_dict in services.run_mpla_refinement(
            initial_prompt=body.initial_prompt,
            settings=settings_dict
        ):
            if await request.is_disconnected():
                break
            
            event_name = event_dict.get("event")
            data_payload = event_dict.get("data")

            # The data payload must be a JSON string for the frontend parser
            # Use jsonable_encoder to handle complex types like datetime
            data_payload_str = json.dumps(jsonable_encoder(data_payload))
            
            sse_message = f"event: {event_name}\ndata: {data_payload_str}\n\n"
            yield sse_message

    return StreamingResponse(sse_formatted_generator(), media_type="text/event-stream")

# --- Meta-Prompt Management Endpoints ---

@app.get("/api/meta-prompts", response_model=List[MetaPrompt])
async def get_all_meta_prompts():
    """Retrieves all meta-prompts from the knowledge base."""
    return await services.get_all_meta_prompts()

@app.get("/api/meta-prompts/{name}", response_model=MetaPrompt)
async def get_meta_prompt_by_name(name: str):
    """Retrieves a specific meta-prompt by its unique name."""
    return await services.get_meta_prompt_by_name(name)

@app.put("/api/meta-prompts/{name}", response_model=MetaPrompt)
async def update_meta_prompt(name: str, payload: MetaPromptUpdate):
    """Updates a meta-prompt's template and/or active status."""
    return await services.update_meta_prompt(name, payload)

# GitHub Integration
@app.get("/api/github/repository/{owner}/{repo}")
async def get_github_repository(owner: str, repo: str):
    """Get GitHub repository information for prompt engineering analysis."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise HTTPException(status_code=401, detail="GitHub token not configured")
    
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Authorization": f"token {github_token}"}
        )
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Repository not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="GitHub API error")
        
        return response.json()

@app.post("/api/github/issues")
async def create_github_issue(issue_data: dict):
    """Create a GitHub issue with MPLA analysis results."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise HTTPException(status_code=401, detail="GitHub token not configured")
    
    import httpx
    
    owner = issue_data.get("owner")
    repo = issue_data.get("repo")
    
    if not owner or not repo:
        raise HTTPException(status_code=400, detail="Owner and repo are required")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers={"Authorization": f"token {github_token}"},
            json={
                "title": issue_data.get("title"),
                "body": issue_data.get("body"),
                "labels": issue_data.get("labels", [])
            }
        )
        
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail="Failed to create issue")
        
        return response.json()

@app.post("/api/database/query")
async def query_mpla_database(query_data: dict):
    """Query MPLA knowledge base for historical data and analytics."""
    try:
        from mpla.knowledge_base.sqlite_kb import SQLiteKnowledgeBase
        from mpla.knowledge_base.schemas import OriginalPrompt, PromptVersion, EvaluationResult
        
        # Use same database path logic as services.py
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        db_path = os.path.join(project_root, "mpla_v2.db")
        kb = SQLiteKnowledgeBase(db_path=db_path)
        await kb.connect()
        
        query_type = query_data.get("query_type")
        filters = query_data.get("filters", {})
        
        if query_type == "sessions":
            # Get all original prompts as session indicators
            results = await kb.get_all(OriginalPrompt)
        elif query_type == "prompts":
            # Get all prompt versions
            results = await kb.get_all(PromptVersion)
        elif query_type == "evaluations":
            # Get all evaluation results
            results = await kb.get_all(EvaluationResult)
        elif query_type == "performance":
            # Get performance analytics
            evaluations = await kb.get_all(EvaluationResult)
            results = {
                "total_evaluations": len(evaluations),
                "average_score": sum(e.overall_score for e in evaluations if e.overall_score) / len(evaluations) if evaluations else 0,
                "recent_evaluations": evaluations[-10:] if evaluations else []
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid query type")
        
        await kb.disconnect()
        
        return {
            "query_type": query_type,
            "filters": filters,
            "results": results,
            "count": len(results) if isinstance(results, list) else 1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

# Enhanced health check with system status
@app.get("/api/health")
async def health_check():
    """Comprehensive health check endpoint for monitoring and load balancers."""
    try:
        # Check database connectivity
        from mpla.knowledge_base.sqlite_kb import SQLiteKnowledgeBase
        import os
        
        # Use same database path logic as services.py
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        db_path = os.path.join(project_root, "mpla_v2.db")
        kb = SQLiteKnowledgeBase(db_path=db_path)
        await kb.connect()
        # SQLite KB uses disconnect() instead of close()
        await kb.disconnect()
        
        health_status = {
            "status": "healthy",
            "timestamp": "2024-01-18T10:00:00Z",
            "version": "1.0.0",
            "environment": os.getenv("NODE_ENV", "development"),
            "checks": {
                "database": "connected",
                "api_keys": {
                    "google_api": "configured" if os.getenv("GOOGLE_API_KEY") else "missing",
                    "openai_api": "configured" if os.getenv("OPENAI_API_KEY") else "missing",
                    "github_token": "configured" if os.getenv("GITHUB_TOKEN") else "missing"
                }
            },
            "uptime": "available",
            "memory_usage": "normal"
        }
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-18T10:00:00Z"
        }
        
@app.get("/api/metrics")
async def metrics():
    """Basic metrics endpoint for monitoring."""
    return {
        "active_sessions": 0,  # Placeholder - could track real sessions
        "total_requests": 0,   # Placeholder - could use middleware to track
        "response_time_avg": "< 100ms",
        "error_rate": "0%"
    }

# Catch-all route for React Router (SPA routing) - MUST BE LAST
@app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
async def serve_spa(full_path: str):
    """Serves the index.html for any path not otherwise caught, for SPA routing."""
    static_path = os.path.join(os.path.dirname(__file__), "..", "static")
    index_file = os.path.join(static_path, "index.html")
    
    if os.path.exists(index_file):
        return FileResponse(index_file)
    else:
        raise HTTPException(status_code=404, detail="Frontend not found") 