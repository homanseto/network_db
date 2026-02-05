import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgis:5432/gis"
)
MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb://host.docker.internal:27018" # It is a special DNS name automatically provided by Docker Desktop (Mac & Windows).
)
