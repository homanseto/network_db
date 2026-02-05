from fastapi import FastAPI
from app.routes import system
from app.routes import import_routes
from app.routes import imdf_routes
from app.routes import network_routes

app = FastAPI()

@app.get("/")
def health():
    x = 1 + 5
    return {"status": "Indoor GIS running testing!!", "x": x}

app.include_router(system.router)
app.include_router(import_routes.router)
app.include_router(imdf_routes.router)
app.include_router(network_routes.router)