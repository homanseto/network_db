from fastapi import APIRouter
from sqlalchemy import text
from app.core.database import engine

router = APIRouter()

@router.get("/test-db")
def test_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT pedrouteid, aliasnamen, aliasnamtc, levelid, ST_AsGeoJSON(shape) AS geojson FROM network_test;"))
        rows = result.fetchall()
        columns = result.keys()
        result_list = [dict(zip(columns, row)) for row in rows]
    return {"result": result_list}
