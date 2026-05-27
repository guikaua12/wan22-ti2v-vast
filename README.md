# Wan 2.2 TI2V-5B — Vast.ai Serverless Template

Vast.ai Serverless ComfyUI JSON worker setup for **Wan 2.2 TI2V-5B** video generation.

Supports:

- **Text-to-video (T2V):** Generate video from a text prompt alone.
- **Image-to-video (I2V):** Animate a starting image with a text prompt.

Both modes use the same Wan 2.2 TI2V-5B diffusion model at 1280x704 resolution (native 720p).

## Important: Backend

This repo supports two Vast Serverless modes:

- Generic `comfyui-json` worker: accepts arbitrary ComfyUI API-format workflows via `/generate/sync`.
- Flourn GPU executor: exposes `/drain`, then pulls queued `wan_ti2v_scene` jobs from the Flourn Postgres queue.

The generic mode remains the default. Set `FLOURN_EXECUTOR=true` to install the custom `/drain` PyWorker route used by the Flourn API.

If your Vast template uses the **dedicated `wan` worker** (`workers/wan/`), the benchmark path and default behavior may differ. Ensure your template is configured for the generic ComfyUI JSON worker, or set `PYWORKER_REPO` / `PYWORKER_REF` to a fork that uses `comfyui-json` as the default backend.

## Vast Template Configuration

### Docker image

```
vastai/comfy:latest
```

### Environment variables

| Variable | Value | Required |
|---|---|---|
| `PROVISIONING_SCRIPT` | `https://raw.githubusercontent.com/guikaua12/wan22-ti2v-vast/main/provisioning.sh` | Yes |
| `PYWORKER_REPO` | `https://github.com/vast-ai/pyworker` | No (default) |
| `PYWORKER_REF` | `main` | No (default) |
| `WEBHOOK_URL` | Your webhook endpoint | No |

### Flourn executor mode

Set these when the endpoint is used by the Flourn backend queue.

| Variable | Value | Required |
|---|---|---|
| `FLOURN_EXECUTOR` | `true` | Yes |
| `DATABASE_URL` | Flourn Postgres URL reachable from the Vast worker | Yes |
| `R2_PUBLIC_BASE_URL` | Public base URL for input frame objects | Yes |
| `S3_ACCESS_KEY_ID` | R2 access key | Yes |
| `S3_SECRET_ACCESS_KEY` | R2 secret key | Yes |
| `S3_BUCKET_NAME` | R2 bucket name | Yes |
| `S3_ENDPOINT_URL` | R2 S3-compatible endpoint URL | Yes |
| `S3_REGION` | `auto` for Cloudflare R2 | No |
| `EXECUTOR_REF` | Git branch/tag for this repo, default `main` | No |

Configure the Flourn API to wake this route:

```properties
FLOURN_GPU_EXECUTOR_WORKER_ROUTE=/drain
FLOURN_GPU_EXECUTOR_WAKE_TIMEOUT=PT10M
```

### S3 upload (optional)

Set these to have generated videos uploaded to S3-compatible storage. The response will include an `s3_url` field.

| Variable | Value |
|---|---|
| `S3_ACCESS_KEY_ID` | Your access key |
| `S3_SECRET_ACCESS_KEY` | Your secret key |
| `S3_BUCKET_NAME` | Bucket name |
| `S3_ENDPOINT_URL` | Endpoint URL (e.g. `https://s3.us-east-1.amazonaws.com`) |
| `S3_REGION` | Region (optional) |

### Exposed ports

| Port | Service |
|---|---|
| `18188` | ComfyUI web UI |
| `18288` | API wrapper (health, docs) |

### GPU requirements

| Tier | VRAM | Notes |
|---|---|---|
| **Minimum** | 24 GB | Works but slower; may need reduced resolution for 121-frame generation |
| **Recommended** | 48 GB | Comfortable for 1280x704 @ 121 frames |
| **Best** | 80 GB | Fastest inference, headroom for longer sequences |

> **Do not** use GPUs with less than 24 GB VRAM. The TI2V-5B model with fp16 weights, fp8 text encoder, and VAE will not fit in 16 GB.

## Model Files Installed

The provisioning script downloads these to `/workspace/ComfyUI/models/`:

```
diffusion_models/wan2.2_ti2v_5B_fp16.safetensors   (~10 GB)
vae/wan2.2_vae.safetensors                          (~200 MB)
text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors (~5 GB)
```

Total download: approximately 15 GB.

## Expected Boot Time

- **First boot:** Downloads ~15 GB of model files. Duration depends on the instance's internet bandwidth — typically 3-10 minutes on fast instances.
- **Subsequent boots:** If `/workspace` persists between runs (same disk), models are already present and boot is much faster. The benchmark still runs to validate the setup.

## Usage

### Install the SDK

```bash
pip install vastai
```

`pip install vastai-sdk` also works as a compatibility wrapper.

### Set your API key

```bash
export VAST_API_KEY="your-api-key"
```

### Run the example

Edit `IMAGE_URL` in `example_request.py` to point to your input image, then:

```bash
python example_request.py
```

The script sends an I2V workflow to the `comfyui-json` endpoint and prints the JSON response.

### Customize the prompt

Edit the `PROMPT` variable in `example_request.py`, or modify the workflow JSON directly:

```python
workflow["6"]["inputs"]["text"] = "your custom prompt here"
```

### Text-to-video (no input image)

Use the T2V workflow from `workflows/ti2v_t2v_1280x704_121f.json`. This omits the `LoadImage` node and leaves `Wan22ImageToVideoLatent.start_image` unconnected.

### Image-to-video with URL input

The Vast API wrapper automatically detects HTTP/HTTPS URLs in workflow string fields, downloads them, and replaces them with local filenames before submitting to ComfyUI. This means you can put a URL directly in the `LoadImage` node's `image` field:

```json
{
    "57": {
        "class_type": "LoadImage",
        "inputs": {
            "image": "https://example.com/your-image.png"
        }
    }
}
```

No custom URL-loader node is required.

### Inspecting outputs

- If S3 is configured, the response includes an `s3_url` field pointing to the uploaded video.
- Without S3, outputs are saved locally under `/workspace/ComfyUI/output/` on the instance. You can access them via the ComfyUI web UI on port 18188.
- Output format is VP9 WebM (from the `SaveWEBM` node) and/or animated WebP (from `SaveAnimatedWEBP`).

## Workflow Files

| File | Mode | Resolution | Frames | Steps | Output |
|---|---|---|---|---|---|
| `benchmark.json` | T2V | 1280x704 | 41 | 20 | SaveWEBM |
| `workflows/ti2v_t2v_1280x704_121f.json` | T2V | 1280x704 | 121 | 30 | SaveWEBM + SaveAnimatedWEBP |
| `workflows/ti2v_i2v_1280x704_121f_url.json` | I2V | 1280x704 | 121 | 30 | SaveWEBM + SaveAnimatedWEBP |

All workflows use:
- Sampler: `uni_pc` / scheduler: `simple` (from the official ComfyUI Wan 2.2 5B example)
- CFG: 5.0
- ModelSamplingSD3 shift: 8.0
- Seed: `__RANDOM_INT__` (replaced at runtime by the Vast worker)

The benchmark uses 20 steps (reduced from the default 30) and 41 frames for faster startup scoring.

## Validation

Run these locally to check file correctness:

```bash
# Shell syntax check
bash -n provisioning.sh

# Shell lint (install: apt install shellcheck / brew install shellcheck)
shellcheck provisioning.sh

# JSON validity
python -m json.tool benchmark.json > /dev/null
python -m json.tool workflows/ti2v_t2v_1280x704_121f.json > /dev/null
python -m json.tool workflows/ti2v_i2v_1280x704_121f_url.json > /dev/null

# Workflow internal reference check
python scripts/validate_workflow_refs.py benchmark.json workflows/*.json

# Python syntax check
python -m py_compile example_request.py
```

On a running instance, use the environment checker:

```bash
bash scripts/validate_env.sh
```

## Troubleshooting

### `workers/comfyui-json` not found

The provisioning script expects the generic ComfyUI JSON worker. If `$SERVER_DIR/workers/comfyui-json/` does not exist, the template may be using a different backend (e.g., the dedicated `wan` worker). Either:

- Switch to a template that uses `comfyui-json`.
- Set `PYWORKER_REPO` / `PYWORKER_REF` to a PyWorker checkout that includes `workers/comfyui-json/`.

### Model file missing

Re-run the provisioning script. It resumes interrupted downloads and skips files that are already present and pass a size check:

```bash
bash /path/to/provisioning.sh
```

### ComfyUI node class not found

If ComfyUI reports an unknown `class_type` (e.g., `Wan22ImageToVideoLatent`, `SaveWEBM`, `ModelSamplingSD3`), the `vastai/comfy` image may be outdated. Check the installed ComfyUI version:

```bash
cd /workspace/ComfyUI && git log --oneline -5
```

Update if necessary, or use a newer `vastai/comfy` tag.

If `CLIPLoader` rejects the `device` parameter, your ComfyUI version predates the device-selection feature. Remove the `"device": "default"` line from the workflow JSON.

### OOM on 24 GB cards

For 24 GB GPUs generating 121-frame 1280x704 video:

- Reduce `length` to 81 or 41.
- Reduce resolution to 832x480 (not native 720p — update prompts accordingly).
- Ensure no other processes consume VRAM on the instance.

### No S3 URL in response

- Verify `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, and `S3_ENDPOINT_URL` are set in the Vast template environment.
- Check the API wrapper logs at `/var/log/portal/comfyui.log` for S3 upload errors.
- You can also pass S3 config per-request in the payload (see `example_request.py`).

### Output saved locally but not uploaded

Without S3 configured, outputs are only saved to `/workspace/ComfyUI/output/`. Access them via ComfyUI's web UI or SSH.

### Benchmark too slow

The benchmark generates a 41-frame video at 1280x704 with 20 steps. On 24 GB cards this can take several minutes. If the benchmark times out:

- Use a GPU with more VRAM (48 GB+).
- Check if `BENCHMARK_TEST_STEPS` env var is supported by your PyWorker version to adjust timeout.

### `SaveVideo` / `CreateVideo` nodes missing

The official ComfyUI Wan 2.2 5B example uses `SaveWEBM` and `SaveAnimatedWEBP` — not `CreateVideo` / `SaveVideo`. These workflows follow the official example. If you need MP4 output, install a custom node that provides MP4 encoding (e.g., `video-helper-suite`).

## License

MIT
