from __future__ import annotations

import asyncio
import hashlib
import hmac
import importlib.util
import json
import logging
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from studio_ai_lab.config import Settings
from studio_ai_lab.engine import EngineUnavailable, UnconfiguredEngine, VideoEngine
from studio_ai_lab.media import make_private_directory, save_upload, user_directory
from studio_ai_lab.store import JobStore

logger = logging.getLogger("studio_ai_lab")
PACKAGE_DIR = Path(__file__).parent
MAX_MULTIPART_OVERHEAD = 1024 * 1024


def public_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"],
        "status": job["status"],
        "configuration": job["config"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "progress": None,
        "error": job["error"],
        "output_url": (
            f"/v1/jobs/{job['id']}/output" if job["status"] == "succeeded" else None
        ),
    }


def gpu_resources() -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {"cuda_available": False, "devices": [], "reason": "PyTorch not installed"}
    try:
        import torch

        if not torch.cuda.is_available():
            return {"cuda_available": False, "devices": []}
        devices = []
        for index in range(torch.cuda.device_count()):
            free_bytes, total_bytes = torch.cuda.mem_get_info(index)
            devices.append(
                {
                    "index": index,
                    "name": torch.cuda.get_device_name(index),
                    "total_memory_bytes": total_bytes,
                    "free_memory_bytes": free_bytes,
                }
            )
        return {"cuda_available": True, "devices": devices}
    except Exception:
        logger.exception("Unable to inspect CUDA resources")
        return {"cuda_available": False, "devices": [], "reason": "CUDA probe failed"}


def create_app(
    settings: Settings | None = None,
    engine: VideoEngine | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    make_private_directory(settings.data_dir)
    store = JobStore(settings.data_dir / "jobs.sqlite3")
    video_engine = engine or UnconfiguredEngine()
    app = FastAPI(title="Dubai Studio AI Lab", version="0.1.0")
    app.state.settings = settings
    app.state.store = store
    app.state.engine = video_engine
    app.state.worker_tasks = {}

    async def authenticated_user(authorization: str | None = Header(default=None)) -> str:
        if not settings.api_tokens:
            raise HTTPException(
                status_code=503, detail="API authentication is not configured"
            )
        scheme, separator, supplied = (authorization or "").partition(" ")
        if not separator or scheme.lower() != "bearer" or not supplied:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        matched_user = None
        for user_id, expected in settings.api_tokens.items():
            if hmac.compare_digest(supplied, expected):
                matched_user = user_id
        if matched_user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return matched_user

    @app.middleware("http")
    async def limit_upload_request(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/v1/jobs":
            raw_length = request.headers.get("content-length")
            if raw_length is None:
                return JSONResponse(
                    status_code=411, content={"detail": "Content-Length is required"}
                )
            try:
                content_length = int(raw_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid length"})
            max_request = (
                2 * settings.max_image_bytes
                + settings.max_audio_bytes
                + MAX_MULTIPART_OVERHEAD
            )
            if content_length < 0 or content_length > max_request:
                return JSONResponse(
                    status_code=413, content={"detail": "Request body is too large"}
                )
        return await call_next(request)

    async def process_job(job_id: str, owner_id: str) -> None:
        job = store.start(job_id, owner_id)
        if job is None:
            return
        worker_task = asyncio.current_task()
        if worker_task is not None:
            app.state.worker_tasks[job_id] = worker_task
        owner_dir = user_directory(settings.data_dir, owner_id)
        input_names = ("image", "audio", "product_image")
        inputs = {
            name: settings.data_dir / relative
            for name, relative in zip(input_names, job["asset_paths"])
        }
        output_dir = owner_dir / "outputs" / job_id
        try:
            make_private_directory(output_dir)
            output = await video_engine.generate(job["config"], inputs, output_dir)
            resolved_output = output.resolve()
            if (
                not resolved_output.is_relative_to(output_dir.resolve())
                or not resolved_output.is_file()
                or resolved_output.suffix.lower() != ".mp4"
            ):
                raise RuntimeError("Video engine returned an invalid MP4 output")
            relative_output = resolved_output.relative_to(settings.data_dir).as_posix()
            if not store.complete(job_id, owner_id, relative_output):
                resolved_output.unlink(missing_ok=True)
        except EngineUnavailable as exc:
            store.fail(job_id, owner_id, str(exc))
        except asyncio.CancelledError:
            shutil.rmtree(output_dir, ignore_errors=True)
        except Exception as exc:
            logger.exception("Video generation failed for job %s", job_id)
            store.fail(job_id, owner_id, f"Video generation failed: {exc}")
        finally:
            if app.state.worker_tasks.get(job_id) is worker_task:
                app.state.worker_tasks.pop(job_id, None)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "video_engine_configured": not isinstance(video_engine, UnconfiguredEngine),
        }

    @app.get("/v1/system/resources")
    async def resources(user_id: str = Depends(authenticated_user)) -> dict[str, Any]:
        del user_id
        return gpu_resources()

    @app.get("/v1/models")
    async def models(user_id: str = Depends(authenticated_user)) -> list[dict[str, Any]]:
        del user_id
        return json.loads((PACKAGE_DIR / "models.json").read_text(encoding="utf-8"))

    @app.post("/v1/jobs", status_code=202)
    async def create_job(
        background_tasks: BackgroundTasks,
        scene: str = Form(...),
        image: UploadFile = File(...),
        audio: UploadFile = File(...),
        product_image: UploadFile | None = File(default=None),
        seed: int | None = Form(default=None),
        user_id: str = Depends(authenticated_user),
    ) -> dict[str, Any]:
        scene = scene.strip()
        if not scene:
            raise HTTPException(status_code=422, detail="Scene description is required")
        if len(scene) > settings.max_scene_chars:
            raise HTTPException(status_code=422, detail="Scene description is too long")
        job_id = uuid4().hex
        owner_dir = user_directory(settings.data_dir, user_id)
        upload_dir = owner_dir / "uploads"
        saved_files: list[Path] = []
        try:
            saved_files.append(
                await save_upload(image, upload_dir, "image", settings.max_image_bytes)
            )
            saved_files.append(
                await save_upload(audio, upload_dir, "audio", settings.max_audio_bytes)
            )
            if product_image is not None and product_image.filename:
                saved_files.append(
                    await save_upload(
                        product_image,
                        upload_dir,
                        "image",
                        settings.max_image_bytes,
                    )
                )
            config = {
                "model": "infinitetalk",
                "scene": scene,
                "seed": seed,
                "engine_version": None,
            }
            relative_files = [
                path.relative_to(settings.data_dir).as_posix() for path in saved_files
            ]
            if not store.create(
                job_id,
                user_id,
                config,
                relative_files,
                settings.max_active_jobs,
            ):
                raise HTTPException(
                    status_code=429, detail="Active-job quota exceeded"
                )
        except Exception:
            for path in saved_files:
                path.unlink(missing_ok=True)
            raise
        job = store.get(job_id, user_id)
        if job is None:
            raise RuntimeError("Newly created job could not be read")
        background_tasks.add_task(process_job, job_id, user_id)
        return public_job(job)

    @app.get("/v1/jobs")
    async def list_jobs(
        user_id: str = Depends(authenticated_user),
    ) -> list[dict[str, Any]]:
        return [public_job(job) for job in store.list(user_id)]

    @app.get("/v1/jobs/{job_id}")
    async def get_job(
        job_id: str,
        user_id: str = Depends(authenticated_user),
    ) -> dict[str, Any]:
        job = store.get(job_id, user_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return public_job(job)

    @app.post("/v1/jobs/{job_id}/cancel")
    async def cancel_job(
        job_id: str,
        user_id: str = Depends(authenticated_user),
    ) -> dict[str, str]:
        if not store.cancel(job_id, user_id):
            raise HTTPException(
                status_code=409, detail="Job is missing or already finished"
            )
        worker_task = app.state.worker_tasks.get(job_id)
        if worker_task is not None:
            worker_task.cancel()
        return {"id": job_id, "status": "cancelled"}

    @app.get("/v1/jobs/{job_id}/output")
    async def download_output(
        job_id: str,
        user_id: str = Depends(authenticated_user),
    ) -> FileResponse:
        job = store.get(job_id, user_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job["status"] != "succeeded" or not job["output_path"]:
            raise HTTPException(status_code=409, detail="Output is not available")
        output = (settings.data_dir / job["output_path"]).resolve()
        if (
            not output.is_relative_to(settings.data_dir.resolve())
            or not output.is_file()
            or output.suffix.lower() != ".mp4"
        ):
            raise HTTPException(status_code=404, detail="Output not found")
        return FileResponse(output, media_type="video/mp4", filename="advertisement.mp4")

    app.mount(
        "/",
        StaticFiles(directory=PACKAGE_DIR / "static", html=True),
        name="studio-ui",
    )
    return app


app = create_app()
