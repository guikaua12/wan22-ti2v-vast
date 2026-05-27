import socket
import time
from pathlib import Path

try:
    from executor.comfy import ComfyClient
    from executor.config import load_config
    from executor.db import QueueDb
    from executor.probe import probe_video
    from executor.storage import R2Storage
except ModuleNotFoundError as exc:
    if exc.name != "executor":
        raise
    from comfy import ComfyClient
    from config import load_config
    from db import QueueDb
    from probe import probe_video
    from storage import R2Storage


def executor_id(prefix: str) -> str:
    return f"{prefix}_{socket.gethostname()}_{int(time.time())}"


def run() -> None:
    config = load_config()
    queue = QueueDb(config.database_url)
    storage = R2Storage(config)
    comfy = ComfyClient(config.comfyui_url)
    comfy.wait_ready()
    current_executor_id = executor_id(config.executor_id_prefix)
    idle_started_at = None

    with queue.connect() as conn:
        while True:
            job = queue.claim(conn, current_executor_id, {"provider": "vast", "model": "wan2.2-ti2v-5b"})
            if job is None:
                if idle_started_at is None:
                    idle_started_at = time.time()
                if time.time() - idle_started_at >= config.idle_exit_seconds:
                    return
                time.sleep(2)
                continue

            idle_started_at = None
            process_job(queue, conn, comfy, storage, current_executor_id, job)


def process_job(queue: QueueDb, conn, comfy: ComfyClient, storage: R2Storage, current_executor_id: str, job) -> None:
    try:
        payload = dict(job.request_payload)
        payload["inputImageUrl"] = r2_public_or_signed_url(payload["inputImageStorageKey"])
        queue.heartbeat(conn, job.job_id, current_executor_id, "running", 10, "Generating scene video")
        video_path = comfy.generate(payload)
        queue.heartbeat(conn, job.job_id, current_executor_id, "uploading", 90, "Uploading scene video to R2")
        result = storage.upload(Path(video_path), payload["outputStorageKey"], "video/webm")
        result.update(probe_video(Path(video_path)))
        ok = queue.complete(conn, job.job_id, current_executor_id, result)
        if not ok:
            raise RuntimeError("Completion function rejected job ownership")
    except Exception as exc:
        queue.fail(conn, job.job_id, current_executor_id, "executor_job_failed", str(exc), True, "generate")


def r2_public_or_signed_url(storage_key: str) -> str:
    import os
    public_base = os.getenv("R2_PUBLIC_BASE_URL", "").rstrip("/")
    if not public_base:
        raise RuntimeError("R2_PUBLIC_BASE_URL is required for ComfyUI URL input")
    return f"{public_base}/{storage_key}"


if __name__ == "__main__":
    run()
