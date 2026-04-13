"""
main.py - FastAPI application for CV evaluation tool

This module sets up a FastAPI application that serves both a static
frontend and an API for evaluating CVs using the LlmEvaluator class.
It includes endpoints for uploading CVs as text or files, and applies
rate limiting to prevent abuse.
"""

from dotenv import load_dotenv
load_dotenv()

import io
import logging
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from markitdown import MarkItDown
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .llm_evaluator import LlmEvaluator, CvEvaluation
from .config import get_settings, ConfigurationError
from .auth import auth_router, require_auth, User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create a FastAPI instance for the site and another for the API
app = FastAPI(title="CV Evaluation Tool")
api_app = FastAPI(title="CV Evaluation API")

# Initialize rate limiter - 5 requests per minute per IP
limiter = Limiter(key_func=get_remote_address)
api_app.state.limiter = limiter
api_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Get settings
try:
    settings = get_settings()
except ConfigurationError as exc:
    logger.critical(f"Startup failure due to configuration error: {exc}")
    raise SystemExit(1)

# Configure CORS - uses settings to determine allowed origins
# In production, this restricts to the app's domain only
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # Required for cookie-based auth
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount auth routes
api_app.include_router(auth_router)

# Initialize the LLM evaluator
evaluator = LlmEvaluator()

# Initialize MarkItDown for converting uploads to markdown
markitdown = MarkItDown(enable_plugins=False)

# Set max file size
MAX_FILE_SIZE_MB = 30
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# CV evaluation endpoint - handles both JSON and file uploads
# Protected by authentication - only org members can access
@api_app.post("/cv/evaluate", response_model=CvEvaluation)
@limiter.limit("5/minute")
async def evaluate_cv(
    request: Request,
    cv_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    user: User = Depends(require_auth),
):
    """
    Evaluate a CV either from text input or file upload.
    Accepts either form data with cv_text field or a file upload.
    """
    
    if cv_text is None and file is None:
        raise HTTPException(status_code=400, detail="Either cv_text or file upload is required")
    
    if cv_text is not None and file is not None:
        raise HTTPException(status_code=400, detail="Provide either cv_text OR file upload, not both")
    
    cv_content = ""
    
    if cv_text:
        # Handle text input
        cv_content = cv_text
    elif file:
        # Handle file upload
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload PDF or DOCX files only.")
        
        try:
            # Convert the file to markdown for sending to the LLM
            content = await file.read()
            if len(content) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.")
            
            result = markitdown.convert(io.BytesIO(content))
            cv_content = result.text_content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Evaluate the CV using the LLM evaluator
    try:
        result = await evaluator.eval(cv_content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating CV: {str(e)}")

# Mount the API app under the /api path
app.mount("/api", api_app)

# Mount the static files directory to the root path
app.mount("/", StaticFiles(directory="./app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
