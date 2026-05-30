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


async def _extract_content_from_upload(upload: UploadFile, input_name: str) -> str:
    """Read and convert an uploaded PDF/DOCX file to markdown text."""
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    if upload.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type for {input_name}. Please upload PDF or DOCX files only."
        )

    try:
        content = await upload.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{input_name} file too large. Maximum size is {MAX_FILE_SIZE_MB}MB."
            )

        result = markitdown.convert(io.BytesIO(content))
        return result.text_content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading {input_name} file: {str(e)}")

# CV evaluation endpoint - handles both JSON and file uploads
# Protected by authentication - only org members can access
@api_app.post("/cv/evaluate", response_model=CvEvaluation)
@limiter.limit("5/minute")
async def evaluate_cv(
    request: Request,
    cv_text: Optional[str] = Form(None),
    cv_file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    user: User = Depends(require_auth),
):
    """
    Evaluate a CV from text input or file upload, with an optional
    job description provided as text input or file upload.
    """

    if cv_text is None and cv_file is None:
        raise HTTPException(status_code=400, detail="Either cv_text or cv_file is required")

    if cv_text is not None and cv_file is not None:
        raise HTTPException(status_code=400, detail="Provide either cv_text OR cv_file, not both")

    if jd_text is not None and jd_file is not None:
        raise HTTPException(status_code=400, detail="Provide either jd_text OR jd_file, not both")

    cv_content = cv_text.strip() if cv_text else ""
    jd_content: Optional[str] = jd_text.strip() if jd_text else None

    if cv_file is not None:
        cv_content = await _extract_content_from_upload(cv_file, "CV")

    if jd_file is not None:
        jd_content = await _extract_content_from_upload(jd_file, "job description")

    if not cv_content:
        raise HTTPException(status_code=400, detail="CV content is required")

    if jd_content is not None and not jd_content:
        jd_content = None

    # Evaluate the CV using the LLM evaluator
    last_exc: Exception | None = None
    for attempt in range(1 + settings.llm_retry_count):
        try:
            result = await evaluator.eval(cv_content, jd_content)
            return result
        except Exception as e:
            last_exc = e
            if attempt < settings.llm_retry_count:
                logger.warning(f"CV evaluation attempt {attempt + 1} of {1 + settings.llm_retry_count} failed, retrying...")
            else:
                logger.error(f"CV evaluation failed after {1 + settings.llm_retry_count} attempts.")
    raise HTTPException(status_code=500, detail=f"Error evaluating CV: {str(last_exc)}")

# Mount the API app under the /api path
app.mount("/api", api_app)

# Mount the static files directory to the root path
app.mount("/", StaticFiles(directory="./app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
