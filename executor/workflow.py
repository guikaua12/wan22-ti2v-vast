import json
from pathlib import Path


WORKFLOW_PATH = Path("workflows/ti2v_i2v_1280x704_121f_url.json")


def build_workflow(payload: dict) -> dict:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    workflow["6"]["inputs"]["text"] = payload["prompt"]
    workflow["7"]["inputs"]["text"] = payload.get("negativePrompt", "")
    workflow["57"]["inputs"]["image"] = payload["inputImageUrl"]
    workflow["55"]["inputs"]["width"] = int(payload.get("width", 704))
    workflow["55"]["inputs"]["height"] = int(payload.get("height", 1280))
    workflow["55"]["inputs"]["length"] = int(payload.get("frameCount", 121))
    workflow["47"]["inputs"]["fps"] = int(payload.get("fps", 24))
    workflow["47"]["inputs"]["filename_prefix"] = payload["pipelineSceneId"]

    workflow_config = payload.get("workflow") or {}
    workflow["3"]["inputs"]["steps"] = int(workflow_config.get("steps", 30))
    workflow["3"]["inputs"]["cfg"] = float(workflow_config.get("cfg", 5.0))
    workflow["3"]["inputs"]["sampler_name"] = workflow_config.get("sampler", "uni_pc")
    workflow["3"]["inputs"]["scheduler"] = workflow_config.get("scheduler", "simple")
    return workflow
