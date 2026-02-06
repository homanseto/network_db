from fastapi import APIRouter
from sqlalchemy import text
from app.core.database import engine
from app.core.mongodb import client

router = APIRouter()

@router.get("/test-db")
def test_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT pedrouteid, aliasnamen, aliasnamtc, levelid, ST_AsGeoJSON(shape) AS geojson FROM network_test;"))
        rows = result.fetchall()
        columns = result.keys()
        result_list = [dict(zip(columns, row)) for row in rows]
    return {"result": result_list}

@router.get("/test-mongo")
async def test_mongo():
    try:
        # The ismaster command is cheap and does not require auth.
        await client.admin.command('ismaster')
        return {"status": "ok", "mongodb": "connected"}
    except Exception as e:
        return {"status": "error", "mongodb": str(e)}

@router.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}
