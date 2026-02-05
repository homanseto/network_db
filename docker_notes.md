**_For debug and development_**
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

each service as oone container

#### Explanation of docker-compose.yml

**_Postgis Service_**

```
postgis:
  image: postgis/postgis:16-3.4
```

## Pull a ready-made image from Docker Hub

This image already contains:
PostgreSQL
PostGIS extension
Spatial libraries
If we removed this, you'd need to build PostGIS manually (painful).

```
container_name: indoor_postgis
```

This gives a fixed name instead of random one.
Without this, Docker would create something like: network-db_postgis_1

```
restart: always
```

If container crashes → restart automatically.
Important for production.

```
environment:
  POSTGRES_DB: gis
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
```

These are environment variables passed into container.
The PostGIS image reads them during startup to:
Create database
Create user
Set password
Without these → default config would be used.

```
ports:
  - "5433:5432"
```

Format:
HOST_PORT:CONTAINER_PORT
So:
Container listens internally on 5432
Your Mac exposes it as 5433
Why?
Because maybe your Mac already uses 5432.
So when you connect from your Mac:localhost:5433
Docker forwards that to container port 5432.

```
volumes:
  - postgis_data:/var/lib/postgresql/data
```

This is persistent storage.
Without this:
If you stop container → database disappears.
With this:
Docker stores DB files in named volume postgis_data.
Think of it as:
A hard drive attached to the container.

```
networks:
  - indoor_net
```

This connects container to a private internal Docker network.
That allows:
api container to talk to postgis container
using hostname postgis

**_API Service (Production)_**

```
api:
  build: ./api
```

Build an image using Dockerfile inside ./api, so Docker build context = api/

```
container_name: indoor_api
```

This is a custom image with fixed name

```
depends_on:
  - postgis
```

This means:
Start postgis first.
It does NOT mean:
Wait until DB ready
Just start order.

```
environment:
  DATABASE_URL: postgresql://postgres:postgres@postgis:5432/gis
```

Important concept:
Inside Docker network:
postgis becomes hostname.
So API connects to DB using: host=postgis
NOT localhost.
Because inside container, localhost = itself.

```
ports:
  - "8001:8000"
```

Container runs FastAPI on 8000.
You expose it as 8001 on your Mac.
So you access: http://localhost:8001

```
volumes:
  - ./data:/data
```

This mounts local folder ./data into container /data.
This is for shapefile uploads/exports.
If API writes file to /data/export.shp,
you will see it in: network-db/data/export.shp

#### Explanation of docker-compose.dev.yml

```
api:
  volumes:
    - ./api/app:/app/app
```

Volume Mount Formal
HOST_PATH : CONTAINER_PATH
so: Mount local folder(network-db/api/app) into container path(/app/app)
./api/app → /app/app
means:
Replace container’s /app/app directory
with my local ./api/app directory.
When Docker mounts a volume, it hides whatever was originally in that container path.
So:
During build → Docker copies code into /app/app
During runtime (dev mode) → volume mount replaces /app/app
It does NOT modify Dockerfile.
It overrides filesystem at runtime.
Container originally has: /app/app/main.py (copied during build), then volume mount says: Use my local folder instead. So container now sees: /app/app/main.py (from my local machine).

refer to Dockerfile:

```
WORKDIR /app
COPY app ./app > COPY <source_on_host> <destination_inside_container>
```

That means:
Take folder named app from your project directory and copy it into /app/app inside container, because WORKING is /app, ./app means /app/app
During build: your code is copied into: /app/app, but in dev mode we mount: ./api/app:/app/app

I edit api/app/main.py and api/app/main.py inside container will be immediately updated.

If We Removed This Volume will slower development, because code is baked into image and changing code requires rebuild.

Dev command:

```
command: >
  python -Xfrozen_modules=off -m debugpy
  --listen 0.0.0.0:5678
  --wait-for-client
  -m uvicorn app.main:app
  --host 0.0.0.0
  --port 8000
  --reload
```

This overrides Dockerfile CMD.

python -m debugpy:
This runs Python and loads the debugpy module.
That means:
Instead of running uvicorn directly, you are wrapping it with a debugger.
Without this, debugging cannot happen.

--listen 0.0.0.0:5678
This tells debugpy:
Open a debugging server on port 5678.
0.0.0.0 means:
Listen on all network interfaces inside the container.
Now the container is waiting for a debugger to connect.

--wait-for-client
This tells debugpy:
Do not continue until VSCode attaches.
So execution pauses here:
debugpy waiting
That’s why HTTP does not work until you attach.

-m uvicorn app.main:app
After debugger attaches, Python runs: uvicorn app.main:app
Which starts FastAPI.

--reload
This enables hot reload.
It means:
If you change code → server restarts automatically.
This works because you mounted your source folder.

In production:
Container runs: uvicorn app.main:app

In dev:
Container runs: debugpy + uvicorn + reload
Production = stable
Development = interactive

Ports in Dev

```
- "8000:8000"
- "5678:5678"
```

8000 → FastAPI
5678 → debugger
VSCode connects to 5678.

**_Dockerfile Explanation_**

```
FROM python:3.11-slim
```

Base OS + Python.

```
RUN apt-get update && apt-get install -y gdal-bin libgdal-dev
```

Installs system-level GIS tools.
Important:
GDAL is NOT a Python library only.
It needs Linux packages.

```
WORKDIR /app
```

Sets working directory.
All next commands operate inside /app.
This sets the current working directory inside the container.
After this line, every relative path is based on: /app

```
COPY requirements.txt .
```

Copies requirements file into container.

```
RUN pip install -r requirements.txt
```

Installs Python dependencies inside container.

```
Installs Python dependencies inside container.

```

COPY app ./app

```
Copies your source code into image.
Only used in production mode.
In dev mode, this gets overridden by volume mount.

Dockerfile = blueprint of machine
docker-compose.yml = how machines are connected
docker-compose.dev.yml = turn machine into workshop mode



default command when container starts.
```

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

```
But in docker-compose.dev.yml:
```

command: >
python -m debugpy --listen 0.0.0.0:5678
-m uvicorn app.main:app
--reload

```
Compose command: overrides Dockerfile CMD, and this is standard Docker behavior.

Priority order:
docker run command
docker-compose command
Dockerfile CMD (default)
So:
Production → uses Dockerfile CMD
Dev → uses compose command


How Does Docker Know What To Override?
Because of how container startup works:
Image is built
Container filesystem is created
Volume mounts applied
Command is executed
Order matters.
So runtime override happens AFTER image is created.

***deploy in window***
If using Windows:
Use Docker Desktop
Enable WSL2 backend (recommended)
Use PowerShell or Git Bash
Volume mounts like: ./api/app:/app/app
still work.


VOLUME:

- <SOURCE>:<TARGET>

- If it does NOT look like a path → Named Volume
Named Volume
Stored inside Docker, and not directly visible in your filesystem
Managed by Docker and Deleted only with -v
From your docker-compose.yml:
```

volumes:

- postgis_data:/var/lib/postgresql/data

```
Docker manages it internally.

Bind Mount (Host Folder Mount)
Uses real folder on your computer, and you can see the files in Finder,
** If container deletes file → file deleted on your machine, and Docker does NOT manage lifecycle
From your dev file:
```

volumes:

- ./api/app:/app/app

```
This is NOT a Docker-managed volume.
This is a bind mount to your actual filesystem.


When I run  `docker compose down`

It does:
Stop containers > Remove containers > Remove network
It does NOT remove:
Named volumes
Bind mounts (because they are just folders on your Mac)
This is by design.

Why Docker Does Not Delete Volumes Automatically
Because volumes usually contain: Databases, Persistent data, Uploaded files
If Docker deleted them automatically, you would lose your database every time.
That would be disastrous.
So Docker protects volumes by default.

if I run `docker compose down -v`, the -v means: Also remove named volumes defined in this compose file.

command:
`docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`
Files are processed left → right
Later files override or extend earlier ones.
So in your case:
docker-compose.yml = base definition
docker-compose.dev.yml = overrides or adds changes

when you pass multiple compose files in one command, they are merged in order, and later files override earlier ones where they overlap.

Docker conceptually builds something like: final_config = merge(base, dev)
If both define the same key:
Simple values → replaced
Maps (like environment) → merged
Lists (like ports) → often merged unless fully redefined
That’s why sometimes ports accumulate.

Why Not Just Put Everything In dev File?
Because then you lose:
Clean production config
Reusable base system
Clear separation of concerns
In real projects, you often have:
docker-compose.yml          ← base
docker-compose.dev.yml      ← development overrides
docker-compose.prod.yml     ← production overrides
docker-compose.ci.yml       ← CI pipeline overrides


## Network

There are 2 different network worlds
Host Machine(Your Mac/Windows)
. pgAdmin runs
. Your browser runs
. You type localhost
Docker Internal Network
Inside that network:
. api container
. postgis container


In docker-compose:
ports:
  - "5433:5432"
> means:
Your computer (host) port 5433
        ↓
Container port 5432

So Docker opens port 5433 on your machine.
That is why from your laptop you use:
Host: localhost > localhost means “this computer”
Port: 5433 > Port 5433 is forwarded to container

Why Not Use postgis as Host?
Because postgis is only resolvable inside Docker network.

From your Mac terminal: ping postgis > it will fail.
But inside the API container: ping postgis > it works.
Because Docker creates internal DNS.

pgAdmin
   ↓
localhost:5433
   ↓
Docker forwards
   ↓
postgis container:5432

inside container
api container
   ↓
postgis:5432


###### docker concept ######

Docker has 5 important object types:
Image → blueprint (read-only template) = blueprints
Container → running instance of image = temporary
Volume → persistent storage = persistent
Network → virtual internal network = communication layer
Compose project → group of containers + network + volumes
Keep that in mind.


1) docker compose build
What it does
Builds Docker images defined in your compose file.
It:
- Reads build: ./api
- Finds the Dockerfile
- Executes Dockerfile instructions
- Creates or updates the image
It does NOT:
- Start containers
- Create networks
- Create volumes
It only builds images.
When you need it
- You changed requirements.txt
- You changed Dockerfile
- You changed system libraries
- You want fresh rebuild

Important detail
Docker uses layer caching.
If only your code changed:
- It rebuilds only the last layer
- Fast
If requirements.txt changed:
- It reruns pip install
- Slower

2) docker compose up
This is the most commonly used command.
It does:
- Build images if needed (if not built yet)
- Create network (if not exists)
- Create volumes (if not exists)
- Create containers
- Start containers
So up = bring the whole system up.

If you add --build: docker compose up --build
It forces rebuild before starting
equivalent to:
```

docker compose build
docker compose up

```
If you add -d
```

docker compose up -d

```
Runs in detached mode (background).

3) docker compose down
This does:
- Stop containers
- Remove containers
- Remove the compose-created network
It does NOT remove:
- Images
- Named volumes (unless you use -v)


Example(What Actually Happens Internally)
Let’s say you run: docker compose up

Docker creates:
```

Project: network-db

Containers:

- network-db-api
- network-db-postgis

Network:

- network-db_default

Volumes:

- network-db_postgis_data

```
when you run: docker compose down
Docker removes:
- network-db-api container
- network-db-postgis container
- network-db_default network
But keeps:
- network-db_postgis_data volume
- images


Why Volumes Are NOT Removed Automatically?
Because volumes usually contain:
- Databases
- Uploaded files
- Important data
If Docker removed volumes automatically, your database would disappear every time.
That would be catastrophic.
So Docker protects data by default.

When Should You Remove Volumes?
- You remove volumes when:
- You want to reset database
- You changed database schema
- You want clean testing environment
- You suspect corrupted data

```

docker compose down -v
docker compose up --build

```
4) 🔁 docker compose restart
Restarts containers without rebuilding.

5) 🛠 docker compose exec
Run command inside container.
```

docker compose exec api bash

```
6) 🗑 docker system prune
Removes:
- Stopped containers
- Unused networks
- Unused images
- Build cache
- Be careful.

Summary Table
Command	    Containers	Network	    Volumes	              Images
build	      ❌ 	       ❌	         ❌	                  ✅
up	        ✅	         ✅	         (create if missing)	 (uses image)
up --build	✅	         ✅	         (create if missing)	 rebuild
down	      ❌ remove   ❌ remove	   ❌ keep	              ❌ keep
down -v	    ❌ remove   ❌ remove	   ❌ remove	            ❌ keep


get into the docker:
psotgis:
docker compose exec postgis psql -U postgres
api:
docker compose exec api bash


```
