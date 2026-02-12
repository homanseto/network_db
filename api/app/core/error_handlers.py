from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.logger import logger
import traceback

async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled error in the entire application.
    Logs the full error (traceback) internally, but sends a safe JSON response to the user.
    """
    # 1. Retrieve the Request ID we set in the middleware
    # Use getattr just in case middleware messed up or request state is empty
    request_id = getattr(request.state, "request_id", "unknown")
    
    # 2. Log the Full Error internally (so we can debug it)
    # We include the traceback so we know exactly which line of code failed.
    error_msg = str(exc)
    logger.error(f"CRITICAL ERROR [{request_id}] - {error_msg}")
    logger.error(traceback.format_exc())

    # 3. Return a clean, user-friendly JSON response
    # We reveal the Request ID so the user can send it to support.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected error occurred on the server.",
            "request_id": request_id,
            # Optional: In development, you might want to show detail, but hide in production
            # "detail": str(exc) 
        }
    )
