Uvicorn is:
An ASGI web server for running Python web applications.

It is NOT:
A framework (FastAPI is the framework)
Not your application logic
Not a reverse proxy
It is the engine that runs your app and handles HTTP requests.

The Big Picture: Who Does What?
when someone visits: http://localhost:8000/

Here’s what happens:
Browser
   ↓
TCP request
   ↓
Uvicorn (web server)
   ↓
FastAPI app
   ↓
Your route function
   ↓
Response

Uvicorn handles:
- Opening port 8000
- Listening for HTTP requests
- Parsing HTTP protocol
- Managing connections
- Running your FastAPI app
FastAPI handles:
- Routing
- Validation
- Dependency injection
- Returning JSON

What Does ASGI Mean?
ASGI = Asynchronous Server Gateway Interface
It is a specification that defines how: Web Server  <-->  Python Application

ASGI supports:
- async / await
- WebSockets
- Background tasks
- High concurrency
FastAPI is built on ASGI.
Uvicorn is an ASGI server.

What This Command Really Means in my dockerfile? 
```
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
- uvicorn
Run the ASGI server.
- app.main:app = <module>:<variable>
Specifically:
```
app.main → Python module
app → FastAPI instance inside that module
```
So Python loads:  app/main.py
And looks for: app = FastAPI()
That object is passed to Uvicorn.

--host 0.0.0.0
This means:
Listen on all network interfaces, inside Docker, this is required.
If I used: 127.0.0.1 > The server would not be accessible outside container.

--port 8000
Bind to port 8000 inside container.
Docker maps that to your machine via:
8000:8000


What Happens Internally When Uvicorn Starts?
When Uvicorn starts:
1. Loads your Python module
2. Finds FastAPI app instance
3. Creates event loop (async engine)
4. Opens socket on given host/port
5. Waits for HTTP connections
6. For each request:
   - Creates ASGI scope
   - Passes it to FastAPI
   - Awaits response
   - Sends HTTP response

What Does --reload Do?
In dev mode you use: --reload 
This enables: Auto-restart when Python files change.
Important:
- It watches your filesystem
- When file changes
- It kills worker process
- Starts a new one
That’s why sometimes debug can behave strangely — because reload spawns subprocesses.

Why Debug Mode Uses python -m debugpy -m uvicorn? 

Your dev compose runs:
```
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
-m uvicorn app.main:app --reload
```

What happens:
debugpy wraps Python process
    ↓
starts uvicorn
    ↓
waits for VSCode to attach
    ↓
runs server

So debugpy becomes the "outer layer", uvicorn runs inside it.

Production vs Development Uvicorn

Development Mode: uvicorn app.main:app --reload

Pros:
- Hot reload
- Debug friendly
Cons:
- Slower
- Not optimized
- Not stable for production

Production Mode: uvicorn app.main:app --workers 4
- Spawns multiple worker processes
- Uses multi-core CPU
- No reload
- More stable

What About Concurrency?
```
@app.get("/")
async def route():
```

It can:
- Handle many requests concurrently
- Without blocking
BUT:
If you run heavy CPU operations (like large Shapely processing),
you can block the event loop.
For heavy geometry work, consider:
- Running calculations in service layer
- Or background task
- Or even Celery later


How Uvicorn Fits Into Docker? 
Docker just runs:  CMD uvicorn ...
The container:
1, Starts
2, Uvicorn binds port 8000
3, Docker exposes port
4, Browser connects
If Uvicorn crashes → container stops.
That’s why your container exits when debugpy misconfigured.

What Happens If You Remove UvicornastAPI is just Python code.
It cannot listen to HTTP itself.
You must have:
- Uvicorn
- Hypercorn
- Daphne
Without server, it’s just a Python object.

Think of Uvicorn as:
The waiter in a restaurant.
- Customers (browser) arrive
- Waiter (Uvicorn) takes request
- Kitchen (FastAPI app) prepares response
- Waiter returns response
FastAPI is not the server.
Uvicorn is the server.
