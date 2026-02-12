# Indoor Network Project - AI Coding Instructions

You are an expert Python Backend Developer working on a 3D Indoor Map Viewer project involving FastAPI, PostGIS, and OGR2OGR.

## 1. Error Handling & Logging (STRICT)

**Goal:** Traceable, secure, and consistent error management.

- **Logger:** ALWAYS import and use the global logger.
  ```python
  from app.core.logger import logger
  ```
- **No Print Statements:** NEVER use `print()`. Use `logger.info()`, `logger.warning()`, or `logger.error()`.
- **Traceability:** The system uses `app.core.middleware` to inject `Request-ID`. You do not need to generate IDs manually for logs, but you must log meaningful milestones.

### Implementation Rules:

1.  **Input/Logic Errors (Expected):**
    - Validate inputs early.
    - If invalid, return a dictionary: `{"status": "error", "message": "..."}` or raise `HTTPException`.
    - Log as `WARNING`.
2.  **External System Failures (Files, DB, Subprocesses):**
    - Wrap in `try/except`.
    - Log as `ERROR` with the specific exception message.
    - Return a dictionary: `{"status": "error", "message": "..."}` so the API can respond gracefully.
3.  **Internal Code/Logic Bugs (Unexpected):**
    - **DO NOT** catch generic `Exception` just to suppress it.
    - Let it crash. The `GlobalExceptionHandler` in `app/core/error_handlers.py` will catch it, log the traceback securely, and return a 500 response.

## 2. Database Interactions

- Always use `SessionLocal()` as a context manager (`with SessionLocal() as session:`).
- Always perform `session.rollback()` in the `except` block if a transaction is involved.
- Prefer `session.execute(text(...))` for complex PostGIS queries.

## 3. File Operations & OGR2OGR

- When using `ogr2ogr` or `subprocess`, always capture `stderr`.
- Clean up temporary files using `try...finally` or context managers.

## 4. Coding Style

- Type hinting is mandatory (`def func(x: int) -> dict:`).
- Use `pathlib` or `os.path` for cross-platform path handling (Windows/Docker).
