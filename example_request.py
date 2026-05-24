#!/usr/bin/env python3
"""
Minimal example: Wan 2.2 TI2V-5B image-to-video via Vast.ai Serverless.

Usage:
    pip install vastai-sdk
    export VAST_API_KEY="your-api-key"
    python example_request.py

Set IMAGE_URL below to the URL of your input image.
The Vast API wrapper automatically downloads URLs found in workflow
string fields and replaces them with local paths before sending to ComfyUI.
"""

import json
import uuid

from vastai import Serverless

ENDPOINT_NAME = "comfyui-json"

IMAGE_URL = "https://example.com/your-input-image.png"  # <-- CHANGE THIS

PROMPT = "a person walking through a beautiful garden, cinematic lighting"
NEGATIVE_PROMPT = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，"
    "静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，"
    "多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，"
    "形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，"
    "背景人很多，倒着走"
)

workflow = {
    "37": {
        "class_type": "UNETLoader",
        "inputs": {
            "unet_name": "wan2.2_ti2v_5B_fp16.safetensors",
            "weight_dtype": "default",
        },
    },
    "38": {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "type": "wan",
            "device": "default",
        },
    },
    "39": {
        "class_type": "VAELoader",
        "inputs": {"vae_name": "wan2.2_vae.safetensors"},
    },
    "48": {
        "class_type": "ModelSamplingSD3",
        "inputs": {"shift": 8.0, "model": ["37", 0]},
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": PROMPT, "clip": ["38", 0]},
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": NEGATIVE_PROMPT, "clip": ["38", 0]},
    },
    "57": {
        "class_type": "LoadImage",
        "inputs": {"image": IMAGE_URL},
    },
    "55": {
        "class_type": "Wan22ImageToVideoLatent",
        "inputs": {
            "width": 1280,
            "height": 704,
            "length": 121,
            "batch_size": 1,
            "start_image": ["57", 0],
        },
    },
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "seed": "__RANDOM_INT__",
            "steps": 30,
            "cfg": 5.0,
            "sampler_name": "uni_pc",
            "scheduler": "simple",
            "denoise": 1.0,
            "model": ["48", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["55", 0],
        },
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["39", 0]},
    },
    "47": {
        "class_type": "SaveWEBM",
        "inputs": {
            "filename_prefix": "wan_ti2v",
            "codec": "vp9",
            "fps": 24,
            "crf": 16,
            "images": ["8", 0],
        },
    },
}

payload = {
    "input": {
        "request_id": str(uuid.uuid4()),
        "workflow_json": workflow,
    }
}

# ── Optional: per-request S3 upload override ──────────────────────────
# Uncomment to override the instance-level S3 config for this request.
#
# payload["input"]["s3"] = {
#     "access_key_id": "YOUR_ACCESS_KEY",
#     "secret_access_key": "YOUR_SECRET_KEY",
#     "bucket_name": "your-bucket",
#     "endpoint_url": "https://s3.us-east-1.amazonaws.com",
# }
# ──────────────────────────────────────────────────────────────────────


def main():
    client = Serverless(endpoint=ENDPOINT_NAME)
    print(f"Sending request to endpoint '{ENDPOINT_NAME}'...")
    print(f"  Image URL : {IMAGE_URL}")
    print(f"  Resolution: 1280x704, 121 frames @ 24 fps")
    print(f"  Request ID: {payload['input']['request_id']}")
    print()

    result = client.request(payload, timeout=600)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
