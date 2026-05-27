import time
import uuid
from pathlib import Path

import requests

from workflow import build_workflow


class ComfyClient:
    def __init__(self, base_url: str, output_dir: str = "/workspace/ComfyUI/output"):
        self.base_url = base_url.rstrip("/")
        self.output_dir = Path(output_dir)

    def wait_ready(self, timeout_seconds: int = 120) -> None:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                response = requests.get(f"{self.base_url}/system_stats", timeout=5)
                if response.status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(2)
        raise RuntimeError("ComfyUI did not become ready")

    def generate(self, payload: dict) -> Path:
        workflow = build_workflow(payload)
        prompt_id = str(uuid.uuid4())
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": prompt_id},
            timeout=30,
        )
        response.raise_for_status()
        before = set(self.output_dir.glob("*.webm"))
        deadline = time.time() + int(payload.get("timeoutSeconds", 900))
        while time.time() < deadline:
            after = set(self.output_dir.glob("*.webm"))
            created = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
            if created:
                return created[0]
            time.sleep(2)
        raise RuntimeError("ComfyUI generation timed out")
