# 1. Start with a lightweight Linux version that has Python 3.11 installed.
FROM python:3.11-slim

# 2. Run Linux commands to install system tools (like GDAL for maps)
# These are installing into the LINUX system, not your Windows system.
# Install GDAL + build deps
# install (gdal-bin)ogr2ogr <-- This installs ogr2ogr
RUN apt-get update && apt-get install -y \
    gdal-bin \ 
    libgdal-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# 3. Install Python libraries (FastAPI, SQLAlchemy, etc.) INSIDE the container.
# Your local Windows Python environment does not have these, which is why 
# you might see red squiggly lines in VS Code unless you install them locally too.
RUN pip install --no-cache-dir -r requirements.txt  --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

COPY app ./app

# 4. The default command to start the app (this gets overridden by docker-compose.dev.yml)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

