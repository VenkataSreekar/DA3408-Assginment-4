# DA3408 A4 — Image Captioning Observability

Streamlit + BLIP-base (CPU) → `prometheus_client` (:8000) → Prometheus (:9090) ← node_exporter (:9100) → Grafana (:3000).

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
streamlit run app.py                      # UI :8501, metrics http://localhost:8000/metrics

./node_exporter                           # :9100  (Linux; macOS/Windows metric names differ, see below)
prometheus --config.file=prometheus.yml   # :9090  -> Status > Targets: all 3 UP
alertmanager --config.file=alertmanager.yml   # :9093 (optional pipeline)
# Grafana :3000 -> add Prometheus data source (http://localhost:9090) -> Dashboards > Import > grafana_dashboard.json
python make_test_zip.py 30 demo.zip       # upload in Bulk tab to create a visible spike
```
Edit `metrics.py`/`app.py` → restart Streamlit (Ctrl+C), otherwise collectors register twice.
macOS/Windows: memory/disk node_* names differ (use `node_memory_free_bytes` etc. / windows_exporter); adjust the 3 host panels.

## Metric inventory
| Type | Names | Labels |
|---|---|---|
| Counter | images_processed_total, client_images_processed_total, requests_total, errors_total, zip_skipped_files_total | mode, status, client_ip, session_id, error_type, reason |
| Gauge | active_requests, bulk_images_remaining, model_process_memory_bytes, process_cpu_percent, model_loaded, model_load_seconds, last_inference_seconds | mode |
| Histogram | inference_seconds, request_seconds, bulk_batch_size | mode |
| Summary | inference_summary_seconds, image_size_bytes, caption_words (`_sum`,`_count`) | mode |
| Info | app_info | model, version |

## PromQL you must be able to explain (Black-Box rule)
- `rate(x_total[1m]) * 60` — per-second average increase over 1 min, ×60 = per minute. Counters only grow; rate() handles resets.
- `histogram_quantile(0.95, sum by (le)(rate(..._bucket[1m])))` — sum bucket rates across labels (keep `le`), then interpolate linearly inside the bucket where 95 % of observations fall. Accuracy depends on bucket layout.
- `rate(_sum)/rate(_count)` — mean of a Summary/Histogram over the window.
- `100 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m]))*100` — idle seconds/sec per core averaged → busy %.
- `1 - MemAvailable/MemTotal` — fraction of RAM not reclaimable.
- `errors / clamp_min(total, 1e-9)` — ratio without divide-by-zero when idle.

## Deliverable checklist
- [ ] Push this folder to GitHub (app.py, metrics.py, prometheus.yml, alert_rules.yml…)
- [ ] Replace the "Prompt used" comments in `prometheus.yml`/`alert_rules.yml`/`gen_dashboard.py` with your real prompts
- [ ] Export dashboard JSON (provided: `grafana_dashboard.json`, or re-export after tweaks)
- [ ] ~1 min screen recording at 5 s refresh while uploading `demo.zip` (health → throughput → latency → CPU correlation)
