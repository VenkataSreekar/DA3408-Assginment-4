"""All Prometheus metrics live here (a separate module is imported once per process,
so Streamlit's script re-runs never re-register collectors).

Metric families (namespace = caption):
  Counters   : images_processed_total{mode,status}, client_images_processed_total{mode,client_ip,session_id},
               requests_total{mode}, errors_total{mode,error_type}, zip_skipped_files_total{reason}
  Gauges     : active_requests{mode}, bulk_images_remaining, model_process_memory_bytes,
               process_cpu_percent, model_loaded, model_load_seconds, last_inference_seconds{mode}
  Histograms : inference_seconds{mode}, request_seconds{mode}, bulk_batch_size
  Summaries  : inference_summary_seconds{mode}, image_size_bytes{mode}, caption_words{mode}  (-> _sum / _count)
  Info       : app_info{model,version}
"""
import os
import threading

import psutil
from prometheus_client import Counter, Gauge, Histogram, Info, Summary, start_http_server

NS = "caption"
MODES = ("single", "bulk")
_proc = psutil.Process()
_proc.cpu_percent(None)  # prime; later calls report CPU% since previous call

# ---- Counters ---------------------------------------------------------------
IMAGES = Counter("images_processed", "Images processed by mode and outcome", ["mode", "status"], namespace=NS)
CLIENT_IMAGES = Counter("client_images_processed", "Successfully captioned images per client/session",
                        ["mode", "client_ip", "session_id"], namespace=NS)
REQUESTS = Counter("requests", "User submissions (a ZIP is ONE request)", ["mode"], namespace=NS)
ERRORS = Counter("errors", "Errors by type", ["mode", "error_type"], namespace=NS)
ZIP_SKIPPED = Counter("zip_skipped_files", "Files in ZIPs that were skipped", ["reason"], namespace=NS)

# ---- Gauges -----------------------------------------------------------------
ACTIVE = Gauge("active_requests", "Requests currently being processed", ["mode"], namespace=NS)
BULK_REMAINING = Gauge("bulk_images_remaining", "Images still queued in the running bulk job", namespace=NS)
MODEL_MEMORY = Gauge("model_process_memory_bytes", "RSS of the app process (dominated by the model)", namespace=NS)
PROC_CPU = Gauge("process_cpu_percent", "App process CPU %, since previous scrape (100 = 1 core)", namespace=NS)
MODEL_LOADED = Gauge("model_loaded", "1 once the model is in memory", namespace=NS)
MODEL_LOAD_SECONDS = Gauge("model_load_seconds", "Seconds taken to load the model", namespace=NS)
LAST_INFERENCE = Gauge("last_inference_seconds", "Most recent inference time", ["mode"], namespace=NS)
MODEL_MEMORY.set_function(lambda: _proc.memory_info().rss)   # evaluated at scrape time
PROC_CPU.set_function(lambda: _proc.cpu_percent(None))

# ---- Histograms (Fibonacci-ish buckets suit CPU inference: 0.1s .. 34s) ------
_B = (0.1, 0.25, 0.5, 1, 1.5, 2, 3, 5, 8, 13, 21, 34)
INFER_HIST = Histogram("inference_seconds", "Model inference time per image", ["mode"], namespace=NS, buckets=_B)
REQUEST_HIST = Histogram("request_seconds", "End-to-end time per submission", ["mode"], namespace=NS,
                         buckets=_B + (55, 89, 144, 233))
BATCH_HIST = Histogram("bulk_batch_size", "Valid images per ZIP", namespace=NS, buckets=(1, 5, 10, 20, 30, 40, 50))

# ---- Summaries --------------------------------------------------------------
INFER_SUMMARY = Summary("inference_summary_seconds", "Inference time (use _sum/_count for mean)", ["mode"], namespace=NS)
IMAGE_BYTES = Summary("image_size_bytes", "Uploaded image size", ["mode"], namespace=NS)
CAPTION_WORDS = Summary("caption_words", "Words per generated caption", ["mode"], namespace=NS)

APP_INFO = Info("app", "Static application metadata", namespace=NS)

_started, _lock = False, threading.Lock()


def start_metrics_server(model_name: str) -> int:
    """Idempotent: expose /metrics on METRICS_PORT (default 8000), separate from Streamlit's 8501."""
    global _started
    port = int(os.getenv("METRICS_PORT", "8000"))
    with _lock:
        if _started:
            return port
        start_http_server(port)
        APP_INFO.info({"model": model_name, "version": "1.0"})
        for m in MODES:  # pre-create series so dashboards show 0 instead of "no data"
            for s in ("success", "error"):
                IMAGES.labels(m, s)
            REQUESTS.labels(m); ACTIVE.labels(m).set(0)
            INFER_HIST.labels(m); REQUEST_HIST.labels(m); INFER_SUMMARY.labels(m)
            IMAGE_BYTES.labels(m); CAPTION_WORDS.labels(m); LAST_INFERENCE.labels(m).set(0)
        BULK_REMAINING.set(0); MODEL_LOADED.set(0)
        _started = True
    return port
