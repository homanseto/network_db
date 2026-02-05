# Deploying on Windows

The **same Dockerfile and docker-compose files** used on macOS work on Windows. You do **not** need different Dockerfile or compose content; Docker Desktop runs Linux containers on Windows.

**Dev on Windows, production elsewhere:** `docker-compose.dev.yml` works on Windows the same as on Mac. Use it only on your Windows dev machine for debugpy and live reload; run production (without the dev overlay) on your deployment server. No extra config needed.

## Prerequisites

1. **Docker Desktop for Windows**
   - Install from [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/).
   - Use the **WSL 2** backend (recommended).

2. **Project location**
   - Keep the repo in a path that Docker Desktop can mount, e.g.:
     - `C:\Users\<you>\Projects\network-db`, or
     - A folder under WSL (e.g. `\\wsl$\Ubuntu\home\...`).
   - Avoid paths Docker cannot share (e.g. some network drives) if you use volume mounts like `./data`.

## Commands (same as on Mac)

**Production-style (no debugger):**

```bash
docker compose -f docker-compose.yml up --build
```

**Development (with debugpy and hot reload):**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

**Optional – Windows override (pins Linux amd64):**  
If you want to force the same image platform on Windows, use the Windows override:

```bash
docker compose -f docker-compose.yml -f docker-compose.windows.yml up --build
```

Or with dev:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.windows.yml up --build
```

## Ports

- API: **8000** (dev) or **8001** (base compose).
- PostGIS: **5433** (host) → 5432 (container).
- Debugger (dev): **5678**.

## If something fails on Windows

- Ensure **Linux containers** are selected (Docker Desktop tray icon → “Switch to Linux containers”).
- Ensure the project (and `./data` if used) is under a supported path (see above).
- If you see path or permission errors, try moving the project to `C:\Users\<you>\...` and run again.
