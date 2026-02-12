from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import system
from app.routes import import_routes
from app.routes import imdf_routes
from app.routes import network_routes
from app.core.middleware import RequestContextMiddleware
from app.core.error_handlers import global_exception_handler

app = FastAPI()

# 1. Register Context Middleware (Adds Request ID)
app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Register Global Exception Handler (Catches crashes)
app.add_exception_handler(Exception, global_exception_handler)

@app.get("/")
def health():
    x = 1 + 5
    return {"status": "Indoor GIS running testing!!", "x": x}

app.include_router(system.router)
app.include_router(import_routes.router)
app.include_router(imdf_routes.router)
app.include_router(network_routes.router)
from app.routes import pedestrian
app.include_router(pedestrian.router)