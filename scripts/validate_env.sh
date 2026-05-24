#!/usr/bin/env bash
set -euo pipefail

# Quick pre-flight check for the Wan 2.2 TI2V-5B serverless setup.

ok=0
fail=0

check() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        printf '  [OK]   %s\n' "$label"
        ((ok++))
    else
        printf '  [FAIL] %s\n' "$label"
        ((fail++))
    fi
}

COMFYUI_DIR="${COMFYUI_DIR:-/workspace/ComfyUI}"
SERVER_DIR="${SERVER_DIR:-/workspace/vast-pyworker}"

echo "=== Wan 2.2 TI2V-5B Environment Check ==="
echo ""
echo "Paths:"
echo "  COMFYUI_DIR = ${COMFYUI_DIR}"
echo "  SERVER_DIR  = ${SERVER_DIR}"
echo ""

echo "Directories:"
check "ComfyUI dir exists" test -d "$COMFYUI_DIR"
check "comfyui-json worker exists" test -d "${SERVER_DIR}/workers/comfyui-json"
check "output dir exists" test -d "${COMFYUI_DIR}/output"
echo ""

echo "Model files:"
check "diffusion model" test -f "${COMFYUI_DIR}/models/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors"
check "VAE" test -f "${COMFYUI_DIR}/models/vae/wan2.2_vae.safetensors"
check "text encoder" test -f "${COMFYUI_DIR}/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
echo ""

echo "Benchmark:"
check "benchmark.json exists" test -f "${SERVER_DIR}/workers/comfyui-json/misc/benchmark.json"
check "benchmark.json valid JSON" python3 -m json.tool "${SERVER_DIR}/workers/comfyui-json/misc/benchmark.json"
echo ""

echo "Services:"
check "ComfyUI HTTP (8188)" curl -sf http://127.0.0.1:8188/system_stats
check "API wrapper HTTP (18288)" curl -sf http://127.0.0.1:18288/health
echo ""

echo "=== Result: ${ok} passed, ${fail} failed ==="
exit "$fail"
