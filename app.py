"""CPU-only image captioning (BLIP base) with Prometheus instrumentation."""
import hashlib
import io
import os
import time
import zipfile

import pandas as pd
import streamlit as st
from PIL import Image, UnidentifiedImageError
from streamlit.runtime.scriptrunner import get_script_run_ctx

import metrics as M

MODEL_NAME = os.getenv("MODEL_NAME", "Salesforce/blip-image-captioning-base")
ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_ZIP_IMAGES = int(os.getenv("MAX_ZIP_IMAGES", "40"))
MAX_FILE_BYTES = 10 * 1024 * 1024        # per image
MAX_TOTAL_BYTES = 150 * 1024 * 1024      # declared uncompressed ZIP size (zip-bomb guard)
MAX_SIDE = 640                           # downscale big images -> predictable CPU time

st.set_page_config(page_title="CPU Image Captioner", page_icon="🖼️", layout="wide")
METRICS_PORT = M.start_metrics_server(MODEL_NAME)


@st.cache_resource(show_spinner="Loading model on CPU (first run downloads ~1 GB)…")
def load_model():
    import torch
    from transformers import BlipForConditionalGeneration, BlipProcessor
    torch.set_num_threads(int(os.getenv("TORCH_THREADS", os.cpu_count() or 2)))
    t0 = time.perf_counter()
    proc = BlipProcessor.from_pretrained(MODEL_NAME)
    model = BlipForConditionalGeneration.from_pretrained(MODEL_NAME).eval()
    M.MODEL_LOAD_SECONDS.set(time.perf_counter() - t0)
    M.MODEL_LOADED.set(1)
    return proc, model


def client_identity():
    """(client_ip, short session id) used as metric labels."""
    ip = "127.0.0.1"
    try:
        ip = (st.context.headers.get("X-Forwarded-For", "").split(",")[0].strip()
              or getattr(st.context, "ip_address", None) or ip)
    except Exception:
        pass
    ctx = get_script_run_ctx()
    sid = hashlib.sha1(ctx.session_id.encode()).hexdigest()[:8] if ctx else "none"
    return ip, sid


def caption_image(img: Image.Image, mode: str):
    import torch
    proc, model = load_model()
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    t0 = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**proc(images=img, return_tensors="pt"), max_new_tokens=30, num_beams=3)
    dt = time.perf_counter() - t0
    M.INFER_HIST.labels(mode).observe(dt)
    M.INFER_SUMMARY.labels(mode).observe(dt)
    M.LAST_INFERENCE.labels(mode).set(dt)
    return proc.decode(out[0], skip_special_tokens=True), dt


def process_one(raw: bytes, mode: str, client):
    """Returns (caption, seconds, error_type). Never raises -> app never crashes on a bad file."""
    try:
        M.IMAGE_BYTES.labels(mode).observe(len(raw))
        text, dt = caption_image(Image.open(io.BytesIO(raw)), mode)
        M.IMAGES.labels(mode, "success").inc()
        M.CLIENT_IMAGES.labels(mode, *client).inc()
        M.CAPTION_WORDS.labels(mode).observe(len(text.split()))
        return text, dt, None
    except (UnidentifiedImageError, OSError, ValueError):
        err = "invalid_image"
    except Exception:
        err = "inference_error"
    M.IMAGES.labels(mode, "error").inc()
    M.ERRORS.labels(mode, err).inc()
    return None, 0.0, err


load_model()
client = client_identity()

with st.sidebar:
    st.header("Observability")
    st.write(f"Metrics: `http://localhost:{METRICS_PORT}/metrics`")
    st.write(f"Model: `{MODEL_NAME}`")
    st.write(f"Session: `{client[1]}`  ·  IP: `{client[0]}`")
    st.caption(f"ZIP limits: {MAX_ZIP_IMAGES} images, {MAX_FILE_BYTES // 2**20} MB each")

st.title("🖼️ Image Captioning (CPU)")
tab_single, tab_bulk = st.tabs(["Single image", "Bulk (ZIP)"])

# ------------------------------------------------------------------ single
with tab_single:
    f = st.file_uploader("Upload an image", type=[e.strip(".") for e in ALLOWED], key="single")
    if f and st.button("Generate caption", type="primary"):
        M.REQUESTS.labels("single").inc()
        with M.ACTIVE.labels("single").track_inprogress(), M.REQUEST_HIST.labels("single").time():
            raw = f.getvalue()
            with st.spinner("Captioning…"):
                text, dt, err = process_one(raw, "single", client)
        if err:
            st.error(f"Could not process this file ({err}).")
        else:
            st.image(raw, width=420)
            st.success(text)
            st.caption(f"Inference: {dt:.2f}s")

# ------------------------------------------------------------------- bulk
with tab_bulk:
    z = st.file_uploader("Upload a ZIP of images", type=["zip"], key="bulk")
    if z and st.button("Process ZIP", type="primary"):
        M.REQUESTS.labels("bulk").inc()
        with M.ACTIVE.labels("bulk").track_inprogress(), M.REQUEST_HIST.labels("bulk").time():
            try:
                zf = zipfile.ZipFile(z)
                infos = [i for i in zf.infolist() if not i.is_dir()]
            except zipfile.BadZipFile:
                M.ERRORS.labels("bulk", "bad_zip").inc()
                st.error("That is not a valid ZIP file.")
                st.stop()
            if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
                M.ERRORS.labels("bulk", "zip_rejected").inc()
                st.error("ZIP is too large when uncompressed.")
                st.stop()

            valid = []
            for i in infos:
                base = os.path.basename(i.filename)
                if base.startswith(".") or i.filename.startswith("__MACOSX"):
                    M.ZIP_SKIPPED.labels("hidden").inc()
                elif os.path.splitext(base)[1].lower() not in ALLOWED:
                    M.ZIP_SKIPPED.labels("unsupported_type").inc()
                elif i.file_size > MAX_FILE_BYTES:
                    M.ZIP_SKIPPED.labels("too_large").inc()
                elif len(valid) >= MAX_ZIP_IMAGES:
                    M.ZIP_SKIPPED.labels("over_limit").inc()
                else:
                    valid.append(i)
            M.BATCH_HIST.observe(len(valid))

            rows, bar = [], st.progress(0.0)
            M.BULK_REMAINING.set(len(valid))
            try:
                for n, info in enumerate(valid, 1):
                    with zf.open(info) as fh:
                        raw = fh.read(MAX_FILE_BYTES + 1)
                    text, dt, err = process_one(raw, "bulk", client)
                    M.BULK_REMAINING.dec()
                    rows.append({"file": info.filename, "caption": text or f"[{err}]", "seconds": round(dt, 2)})
                    bar.progress(n / len(valid), text=f"{n}/{len(valid)}")
            finally:
                M.BULK_REMAINING.set(0)
            st.session_state["bulk_df"] = pd.DataFrame(rows)

    df = st.session_state.get("bulk_df")
    if df is not None and not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button("Download CSV", df.to_csv(index=False), "captions.csv", "text/csv")
