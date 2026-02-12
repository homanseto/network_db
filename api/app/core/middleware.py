import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logger import logger

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    1. Generates a unique ID (UUID) for every request.
    2. Logs when the request starts and finishes.
    3. Calculates how long the request took.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        
        # Store ID in request state so we can access it later
        request.state.request_id = request_id
        
        start_time = time.time()
        # Log the start of the request
        logger.info(f"REQ_START [{request_id}] - {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            process_time = (time.time() - start_time) * 1000
            # Log successful completion
            logger.info(f"REQ_DONE  [{request_id}] - Status: {response.status_code} - Took: {process_time:.2f}ms")
            
            # Return the ID to the user in the headers (useful for debugging from frontend)
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            # Log failure if the application crashes
            process_time = (time.time() - start_time) * 1000
            logger.error(f"REQ_FAIL  [{request_id}] - Error: {str(e)} - Took: {process_time:.2f}ms")
            raise e  # Re-raise so the Exception Handler can catch it later
