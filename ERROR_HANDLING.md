# Error Handling and Logging Strategy

## 1. Overview

This project uses a centralized logging and exception handling strategy designed for microservices/Docker environments.

**Goals:**

1.  **Traceability:** Every request has a unique `Request ID` that allows tracing logs across different components.
2.  **Safety:** Unhandled exceptions (bugs) never crash the server and never leak internal stack traces to the user.
3.  **Consistency:** All logs follow a specific format (`Time | Level | Message`).

---

## 2. Architecture

### A. The Logger (`app/core/logger.py`)

A standard Python logger configured to output to `stdout` (Console). This allows Docker to capture logs naturally.

### B. Middleware (`app/core/middleware.py`)

Intercepts every HTTP request before it reaches your routes.

1.  Generates a UUID (`a1b2-c3d4...`).
2.  Attaches it to `request.state.request_id`.
3.  Logs the `REQ_START` and `REQ_DONE` events with execution time.

### C. Global Exception Handler (`app/core/error_handlers.py`)

Catches any `Exception` that bubbles up to the top level (HTTP 500).

1.  Logs the **Full Traceback** internally (so you can debug).
2.  Returns a **Clean JSON** to the user containing the `request_id`.

---

## 3. How to use in New Code

### 1. Import the Logger

In any file (`services`, `routes`, `models`), import the global logger instance.
Will the error message return to the API response to inform the user of the error?

```python
from app.core.logger import logger
```

### 2. Log Meaningful Events

- **INFO:** High-level milestones (e.g., "Started import", "File saved", "Email sent").
  ```python
  logger.info(f"Processing network import for venue: {display_name}")
  ```
- **WARNING:** Recoverable issues (e.g., "Config missing, using default", "Row skipped").
  ```python
  logger.warning(f"Row {id} has no geometry. Skipping.")
  ```
- **ERROR:** Specific failures you catch (e.g., "DB Connect failed", "File not found").
  ```python
  logger.error(f"Ogr2ogr conversion failed: {stderr_output}")
  ```

### 3. Error Handling Rules (Try/Catch)

#### ❌ DATA: Don't Catch Bugs

Do not wrap logic in generic try/catch blocks just to suppress errors.

```python
# BAD
try:
    result = x / y
except:
    return None # We will never know if y was 0 or x was a string.
```

#### ✅ DO: Catch External System Failures

Catch errors when interacting with files, databases, or shell commands.

```python
# GOOD
try:
    subprocess.run(["ogr2ogr", ...], check=True)
except subprocess.CalledProcessError as e:
    logger.error(f"Conversion failed: {e.stderr}")
    return {"status": "error", "message": "File conversion failed"}
```

---

## 4. Debugging Guide

When a user reports an error, they will provide a **Request ID** (e.g., `abc-123`) from the error response.

1.  Open your logs (Terminal or Docker).
2.  Search/Grep for that ID: `abc-123`.
3.  You will see the entire lifecycle:
    - `INFO: REQ_START [abc-123] ...`
    - `INFO: Processing file...`
    - `ERROR: CRITICAL ERROR [abc-123] - Division by zero...`
    - `INFO: REQ_FAIL [abc-123] ...`

---

## 5. Security & API Response Strategy

### A. Expected Errors (Logic/Validation)

When you catch an error explicitly (e.g., "File not found", "Validation Error"), the API returns specific details.

- **User Sees:** `{"status": "error", "message": "Shapefile missing in zip"}`
- **Reason:** The user has the power to fix this mistake.

### B. Unexpected Errors (System Crashes)

When the system crashes (HTTP 500) due to a bug or infrastructure failure, the Global Handler acts as a security shield.

- **User Sees:** `{"status": "error", "message": "An unexpected error occurred.", "request_id": "abc-123"}`
- **Developer Log:** `CRITICAL ERROR ... [Full Stack Trace / Line Numbers] ...`
- **Security Best Practice:**
  - **Hide Implementation:** We never show stack traces to the public. They reveal file paths, library versions, and database schemas that attackers can exploit.
  - **Safe Feedback:** Users get a "Ticket Number" (Request ID) to report, keeping the feedback loop helpful without leaking secrets.
