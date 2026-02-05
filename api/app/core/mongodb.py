# app/core/mongodb.py

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import MONGODB_URL

client = AsyncIOMotorClient(MONGODB_URL)

mongo_db = client["IndoorMap"]
