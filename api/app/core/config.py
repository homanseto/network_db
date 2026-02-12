import os

class Settings:
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "postgis")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "gis")

settings = Settings()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)


# MongoDB connection string in 3dm-db4
MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb://10.77.159.237:27017/?replicaSet=rs0"  # "mongodb://3dm-db4:27017/?replicaSet=rs0" # It is a special DNS name automatically provided by Docker Desktop (Mac & Windows).
)

# MongoDB connesztion string in local mac machine
# MONGODB_URL = os.getenv(
#     "MONGODB_URL",
#     "mongodb://host.docker.internal:27018"  # "mongodb://3dm-db4:27017/?replicaSet=rs0" # It is a special DNS name automatically provided by Docker Desktop (Mac & Windows).
# )