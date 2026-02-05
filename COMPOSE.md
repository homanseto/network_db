# Compose: Development vs Production

When your **development machine** and **production machine** are different, use different compose file combinations so dev has debugging and live reload, and production runs the built image only.

## Role of each file

| File                           | Purpose                                                                                                                                                                     |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **docker-compose.yml**         | Base config: PostGIS + API image, env, volumes (`./data`), ports. API runs **uvicorn** from the Dockerfile (no debugger, code baked in image). **Use this for production.** |
| **docker-compose.dev.yml**     | Dev overlay: mounts `./api/app` for live reload, runs **debugpy** + uvicorn with `--reload`, exposes 8000 and 5678. **Use only on your dev machine.**                       |
| **docker-compose.windows.yml** | Optional: pins `platform: linux/amd64` (for Windows hosts).                                                                                                                 |
| **docker-compose.prod.yml**    | Optional: explicit production overrides (see below).                                                                                                                        |

## Which config to use where

### Development machine (your laptop / dev PC)

Use the **base + dev** overlay so you get live code mount, debugger, and reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- API: http://localhost:8000
- Debugger: port 5678 (attach from VS Code / IDE)
- Code changes: picked up by `--reload` via the `./api/app` volume

Do **not** use the dev overlay on the production server.

### Production machine (server / VM)

Use **only the base** compose so the API runs from the built image, no debugger, no source mount:

```bash
docker compose -f docker-compose.yml up --build -d
```

- API: http://localhost:8001 (or whatever host/port you expose)
- No debugger port, no live mount; code is inside the image
- `restart: always` and env (e.g. `EXPORT_RESULT_DIR`) from base compose

### Optional: explicit production override

If you want a single “production” profile you can add `docker-compose.prod.yml` and use it on the server so production is clearly separate from the base (e.g. different ports or env). Then on production run:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

## Summary

| Environment     | Command                                                                     |
| --------------- | --------------------------------------------------------------------------- |
| **Development** | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` |
| **Production**  | `docker compose -f docker-compose.yml up --build -d`                        |

Same repo; different compose stack depending on the machine.
