import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgis:5432/gis"
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