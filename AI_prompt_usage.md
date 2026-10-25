# AI prompt usage (PromQL attribution)

This file answers the course's **"Black Box" Metric Rule**: AI may be used to generate PromQL, but every AI-generated query must be attributed with the prompt used.

- The PromQL in `alert_rules.yml` and in the Grafana dashboard (`grafana_dashboard.json`, built by me in the Grafana UI using the Builder) was generated with AI assistance (Claude, Anthropic).
- All queries below were suggested by Claude in one chat session. The root prompt was the assignment PDF pasted in, plus: **"help me complete this assignment"**. Follow-up prompts are quoted where I used one.
- The **logic of every query is calculated by hand** in [`METRICS.md`](METRICS.md).
- `gen_dashboard.py` is an optional script that was **not** used to build my submitted dashboard.

> TODO before submitting: if you wrote or changed any query yourself, change its "Origin" cell to "Written by me".

## 1. Prometheus rules (`alert_rules.yml`)

| Rule | PromQL | Origin / prompt |
|---|---|---|
| `CaptionAppDown` | `up{job="caption-app"} == 0` (for 30 s) | AI. Root prompt (assignment + "help me complete this assignment") |
| `HighInferenceP95` | `histogram_quantile(0.95, sum by (le) (rate(caption_inference_seconds_bucket[2m]))) > 8` (for 1 m) | AI. Root prompt |
| `HighErrorRatio` | `sum(rate(caption_images_processed_total{status="error"}[5m])) / clamp_min(sum(rate(caption_images_processed_total[5m])), 1e-9) > 0.1` (for 2 m) | AI. Root prompt |
| `HostHighCPU` | `100 - avg(rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100 > 90` (for 2 m) | AI. Root prompt |
| `HostHighMemory` | `100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 90` (for 2 m) | AI. Root prompt |

## 2. Grafana dashboard panels

Built in the UI with the query **Builder**, following Claude's reply to: *"do with builder only, in class, we did using builder"*.

| Row | Panel | Query (Builder: metric, filters, operations) | Origin / prompt |
|---|---|---|---|
| 1 · Health | App status | `up{job="caption-app"}` | AI, builder prompt above |
| 1 · Health | Host status | `up{job="node"}` | AI |
| 1 · Health | Both targets | `up{job=~"caption-app\|node"}` (regex match) | AI |
| 1 · Health | Active requests | `sum(caption_active_requests)` | AI |
| 1 · Health | Images / errors last hour | `sum(increase(caption_images_processed_total{status="success"}[1h]))` and the same with `status="error"` | AI |
| 2 · Throughput | Images per minute by mode | `sum by (mode) (rate(caption_images_processed_total{status="success"}[1m])) * 60` | AI |
| 2 · Throughput | Requests per minute | `sum by (mode) (rate(caption_requests_total[1m])) * 60` | AI |
| 2 · Throughput | Errors per minute by type | `sum by (error_type) (rate(caption_errors_total{error_type=~"invalid.*\|inference.*\|bad_zip\|zip_rejected"}[1m])) * 60` | AI |
| 3 · Latency | p50 / p95 / p99 (log axis) | `histogram_quantile(q, sum by (le) (rate(caption_inference_seconds_bucket[1m])))`, q = 0.50 / 0.95 / 0.99 | AI |
| 3 · Latency | p95 by mode | `histogram_quantile(0.95, sum by (le, mode) (rate(caption_inference_seconds_bucket[1m])))` | AI |
| 3 · Latency | Mean inference (Summary) | `sum by (mode) (rate(caption_inference_summary_seconds_sum[1m])) / sum by (mode) (rate(caption_inference_summary_seconds_count[1m]))` | AI |
| 3 · Latency | Heatmap | `sum by (le) (increase(caption_inference_seconds_bucket[1m]))` | AI |
| 4 · Correlation | Host CPU vs bulk images/min | `100 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100` and `sum(rate(caption_images_processed_total{mode="bulk",status="success"}[1m])) * 60` | AI |
| 4 · Correlation | Host RAM vs app RSS | `100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)` and `caption_model_process_memory_bytes` | AI |
| 5 · App resources | Memory / CPU / concurrency | `caption_model_process_memory_bytes`, `caption_process_cpu_percent`, `caption_active_requests`, `caption_bulk_images_remaining` | AI |
| 6 · System | Disk used % | `100 * (1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs\|rootfs"} / node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs\|rootfs"})` | AI |
| 7 · Clients | Top clients table | `topk(15, sum by (client_ip, session_id, mode) (increase(caption_client_images_processed_total[1h])))` | AI |

## 3. Regex used

| Pattern | Where | Origin |
|---|---|---|
| `caption-app\|node` (`job =~`) | Both-targets status panel | AI |
| `invalid.*\|inference.*\|bad_zip\|zip_rejected` (`error_type =~`) | Errors per minute panel | AI |
| `tmpfs\|rootfs` (`fstype !~`) | Disk used panel | AI |
| `single`, `bulk` (override "field name matching regex") | Colour per mode | AI |
