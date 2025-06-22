from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import os
from dotenv import load_dotenv

# Placeholder for our service functions
from . import services

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
    allow_origins=["http://localhost:5173"],  # The default Vite dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for API requests and responses ---

class ProviderSettings(BaseModel):
    orchestrator: str = Field(default='gemini', description="Can be 'gemini' or 'openai'")
    enhancer: str = Field(default='rule_based', description="Can be 'rule_based', 'llm_assisted', or 'architect'")

class RefineRequest(BaseModel):
    initial_prompt: str = Field(..., min_length=10)
    max_iterations: int = Field(default=3, gt=0, le=10)
    model_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    providers: ProviderSettings = Field(default_factory=ProviderSettings)
    # New fields for self-correction
    enable_self_correction: bool = Field(default=False)
    self_correction_iterations: int = Field(default=3, gt=0, le=5)

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the MPLA API"}

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
        async for result_str in services.run_mpla_refinement(
            initial_prompt=body.initial_prompt,
            settings=settings_dict
        ):
            if await request.is_disconnected():
                break
            
            # result_str is '{"event": "...", "data": ...}'
            event_dict = json.loads(result_str)
            event_name = event_dict.get("event")
            data_payload = event_dict.get("data")

            # The data payload must be a JSON string for the frontend parser
            if isinstance(data_payload, (dict, list)):
                data_payload_str = json.dumps(data_payload)
            else:
                data_payload_str = str(data_payload)
            
            sse_message = f"event: {event_name}\ndata: {data_payload_str}\n\n"
            yield sse_message

    return StreamingResponse(sse_formatted_generator(), media_type="text/event-stream")

# Placeholder for a simple health check
@app.get("/api/health")
def health_check():
    return {"status": "ok"} 