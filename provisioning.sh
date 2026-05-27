#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────────
# Wan 2.2 TI2V-5B — Vast.ai Serverless Provisioning Script
#
# Modes:
#   FLOURN_EXECUTOR=true  — Flourn GPU executor (pulls jobs from Postgres queue)
#   FLOURN_EXECUTOR=false — Generic comfyui-json PyWorker (default, Vast /generate/sync)
# ──────────────────────────────────────────────────────────────────────────────

FLOURN_EXECUTOR="${FLOURN_EXECUTOR:-false}"
EXECUTOR_REPO="${EXECUTOR_REPO:-https://github.com/guikaua12/wan22-ti2v-vast.git}"
EXECUTOR_REF="${EXECUTOR_REF:-main}"
EXECUTOR_DIR="${EXECUTOR_DIR:-/workspace/flourn-gpu-executor}"
BENCHMARK_JSON_URL="${BENCHMARK_JSON_URL:-https://raw.githubusercontent.com/guikaua12/wan22-ti2v-vast/main/benchmark.json}"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

# ── Path detection ────────────────────────────────────────────────────────────

COMFYUI_DIR="${COMFYUI_DIR:-/workspace/ComfyUI}"
SERVER_DIR="${SERVER_DIR:-}"

if [[ -z "$SERVER_DIR" ]]; then
    for candidate in /workspace/vast-pyworker /workspace/pyworker; do
        if [[ -d "$candidate" ]]; then
            SERVER_DIR="$candidate"
            break
        fi
    done
    if [[ -z "$SERVER_DIR" && -d "./workers/comfyui-json" ]]; then
        SERVER_DIR="$(pwd)"
    fi
fi

if [[ -z "$SERVER_DIR" ]]; then
    log "ERROR: Could not locate the PyWorker server directory."
    log "  Checked: /workspace/vast-pyworker, /workspace/pyworker, \$(pwd)/workers/comfyui-json"
    log "  Set SERVER_DIR to the root of your PyWorker checkout and re-run."
    exit 1
fi

if [[ "$FLOURN_EXECUTOR" != "true" ]]; then
    BENCHMARK_DIR="${SERVER_DIR}/workers/comfyui-json/misc"

    if [[ ! -d "${SERVER_DIR}/workers/comfyui-json" ]]; then
        log "ERROR: ${SERVER_DIR}/workers/comfyui-json does not exist."
        log "  This provisioning script targets Vast's generic comfyui-json worker."
        log "  If you are using the dedicated 'wan' worker, the benchmark path differs."
        exit 1
    fi
fi

log "Mode        : $([[ "$FLOURN_EXECUTOR" == "true" ]] && echo "flourn-executor" || echo "pyworker")"
log "ComfyUI dir : ${COMFYUI_DIR}"
log "Server dir  : ${SERVER_DIR}"

# ── Directory setup ───────────────────────────────────────────────────────────

dirs=(
    "${COMFYUI_DIR}/models/diffusion_models"
    "${COMFYUI_DIR}/models/vae"
    "${COMFYUI_DIR}/models/text_encoders"
    "${COMFYUI_DIR}/custom_nodes"
    "${COMFYUI_DIR}/output"
)
[[ "$FLOURN_EXECUTOR" != "true" ]] && dirs+=("${BENCHMARK_DIR}")

for d in "${dirs[@]}"; do
    mkdir -p "$d"
done
log "Directories OK"

# ── Model downloads ──────────────────────────────────────────────────────────
# Uses wget -c for resumable downloads. Skips files that already look complete.

HF_BASE="https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files"

declare -A MODELS=(
    ["diffusion_models/wan2.2_ti2v_5B_fp16.safetensors"]="${HF_BASE}/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors"
    ["vae/wan2.2_vae.safetensors"]="${HF_BASE}/vae/wan2.2_vae.safetensors"
    ["text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"]="${HF_BASE}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
)

MIN_SIZE_BYTES=1048576  # 1 MB — sanity floor; real files are GBs

download_model() {
    local rel_path="$1"
    local url="$2"
    local dest="${COMFYUI_DIR}/models/${rel_path}"

    if [[ -f "$dest" ]]; then
        local size
        size=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest" 2>/dev/null || echo 0)
        if (( size > MIN_SIZE_BYTES )); then
            log "SKIP (exists, ${size} bytes): ${rel_path}"
            return 0
        fi
        log "File too small (${size} bytes), re-downloading: ${rel_path}"
    fi

    log "Downloading: ${rel_path}"
    wget -c -q --show-progress -O "$dest" "$url" || {
        log "ERROR: Download failed for ${rel_path}"
        return 1
    }
    log "Done: ${rel_path}"
}

for rel in "${!MODELS[@]}"; do
    download_model "$rel" "${MODELS[$rel]}"
done

log "Model file sizes:"
for rel in "${!MODELS[@]}"; do
    ls -lh "${COMFYUI_DIR}/models/${rel}"
done

# ── Benchmark JSON (PyWorker mode only) ─────────────────────────────────────

if [[ "$FLOURN_EXECUTOR" != "true" ]]; then
    BENCHMARK_DEST="${BENCHMARK_DIR}/benchmark.json"
    log "Installing benchmark workflow: ${BENCHMARK_DEST}"

    wget -q -O "$BENCHMARK_DEST" "$BENCHMARK_JSON_URL" || {
        log "ERROR: Failed to download benchmark.json from ${BENCHMARK_JSON_URL}"
        exit 1
    }

    python3 -m json.tool "$BENCHMARK_DEST" >/dev/null || {
        log "ERROR: benchmark.json is not valid JSON"
        exit 1
    }
    log "Benchmark JSON validated OK"
fi

# ── Flourn GPU executor setup ───────────────────────────────────────────────

if [[ "$FLOURN_EXECUTOR" == "true" ]]; then
    log "Cloning executor repo: ${EXECUTOR_REPO} (${EXECUTOR_REF})"
    if [[ -d "${EXECUTOR_DIR}/.git" ]]; then
        cd "$EXECUTOR_DIR"
        git fetch origin "$EXECUTOR_REF" && git checkout FETCH_HEAD
        cd -
        log "Executor repo updated"
    else
        git clone --depth 1 --branch "$EXECUTOR_REF" "$EXECUTOR_REPO" "$EXECUTOR_DIR"
        log "Executor repo cloned"
    fi

    log "Installing executor Python dependencies"
    python3 -m pip install --no-cache-dir -r "${EXECUTOR_DIR}/requirements.txt"

    log "Installing Flourn PyWorker route into ${SERVER_DIR}"
    cp "${EXECUTOR_DIR}/worker.py" "${SERVER_DIR}/worker.py"
    rm -rf "${SERVER_DIR}/executor"
    cp -R "${EXECUTOR_DIR}/executor" "${SERVER_DIR}/executor"

    chmod +x "${EXECUTOR_DIR}/executor/entrypoint.sh"
    log "Executor setup complete"
fi

# ── Output cleanup cron ──────────────────────────────────────────────────────
# Delete output files older than 24 h when available disk drops below 512 MB.

CRON_MARKER="# wan22-ti2v-output-cleanup"
CLEANUP_CMD="find ${COMFYUI_DIR}/output -type f -mmin +1440 -delete"
CRON_LINE="*/30 * * * * avail=\$(df --output=avail -B1M ${COMFYUI_DIR} | tail -1 | tr -d ' '); [ \"\$avail\" -lt 512 ] && ${CLEANUP_CMD} ${CRON_MARKER}"

CRON_INSTALLED="no"
if command -v crontab >/dev/null 2>&1; then
    existing=$(crontab -l 2>/dev/null || true)
    if echo "$existing" | grep -qF "$CRON_MARKER"; then
        log "Output cleanup cron already installed"
        CRON_INSTALLED="yes (already present)"
    else
        (echo "$existing"; echo "$CRON_LINE") | crontab -
        log "Output cleanup cron installed (every 30 min, threshold 512 MB)"
        CRON_INSTALLED="yes"
    fi
else
    log "WARNING: crontab not available. Output cleanup cron not installed."
    log "  You may want to periodically clear ${COMFYUI_DIR}/output/ manually."
    CRON_INSTALLED="no (crontab unavailable)"
fi

# ── Final diagnostics ────────────────────────────────────────────────────────

echo ""
log "=== DIAGNOSTICS ==="
log "Mode              : $([[ "$FLOURN_EXECUTOR" == "true" ]] && echo "flourn-executor" || echo "pyworker")"
log "ComfyUI dir       : ${COMFYUI_DIR}"
log "Server dir        : ${SERVER_DIR}"
if [[ "$FLOURN_EXECUTOR" == "true" ]]; then
    log "Executor dir      : ${EXECUTOR_DIR}"
else
    log "Benchmark path    : ${BENCHMARK_DEST}"
fi
log "Cleanup cron      : ${CRON_INSTALLED}"
echo ""
log "Model files:"
for rel in "${!MODELS[@]}"; do
    ls -lh "${COMFYUI_DIR}/models/${rel}" 2>/dev/null || log "  MISSING: ${rel}"
done
echo ""
log "PROVISIONING COMPLETE"
