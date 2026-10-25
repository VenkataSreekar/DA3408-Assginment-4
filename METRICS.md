# Metrics and PromQL: explained and calculated by hand

This file lists every metric the app exposes, why it exists, and shows the logic of the PromQL used in `alert_rules.yml` and the Grafana dashboard.

> **How to use this file.** Run the app, upload one image and one ZIP, then save a snapshot:
> `curl -s localhost:8000/metrics > metrics_snapshot.txt`
> The worked examples in section 3 use **illustrative numbers** (marked *example*). Replace them with values from **your** snapshot and re-do the arithmetic. The formulas stay the same. Delete the "(example)" tags once replaced.

---

## 1. Custom application metrics

Defined in [`metrics.py`](metrics.py), exposed on `http://localhost:8000/metrics` (all names are prefixed `caption_`).

### Counters (only go up, reset to 0 when the app restarts)
| Metric | Labels | Incremented when | Why monitored |
|---|---|---|---|
| `caption_images_processed_total` | `mode`, `status` | Each image finishes (success or error) | Throughput and error ratio |
| `caption_client_images_processed_total` | `mode`, `client_ip`, `session_id` | Each successfully captioned image | Who is driving load (client tracking) |
| `caption_requests_total` | `mode` | Each submission (a ZIP counts once) | Usage; compare with images to see batch size |
| `caption_errors_total` | `mode`, `error_type` | `invalid_image`, `inference_error`, `bad_zip`, `zip_rejected` | Error rate by cause |
| `caption_zip_skipped_files_total` | `reason` | A ZIP member is skipped (`hidden`, `unsupported_type`, `too_large`, `over_limit`) | Shows bulk mode survives bad input |

### Gauges (current value, go up and down)
| Metric | Labels | Meaning | Why monitored |
|---|---|---|---|
| `caption_active_requests` | `mode` | Submissions in flight | Concurrency |
| `caption_bulk_images_remaining` | none | Images still queued in the running ZIP | Job progress |
| `caption_model_process_memory_bytes` | none | Resident memory of the app (read at scrape time) | Memory cost of the model |
| `caption_process_cpu_percent` | none | App CPU % since previous scrape (100 = 1 core) | App-side CPU for correlation |
| `caption_model_loaded` | none | 1 once BLIP is in memory | Readiness |
| `caption_model_load_seconds` | none | Time to load the model | Cold-start cost |
| `caption_last_inference_seconds` | `mode` | Most recent inference time | Quick latency glance |

### Histograms (`_bucket{le=...}`, `_sum`, `_count`)
| Metric | Labels | Buckets | Why monitored |
|---|---|---|---|
| `caption_inference_seconds` | `mode` | 0.1, 0.25, 0.5, 1, 1.5, 2, 3, 5, 8, 13, 21, 34 s | Latency per image, percentiles |
| `caption_request_seconds` | `mode` | the same plus 55, 89, 144, 233 s | Whole-submission wait (a ZIP is long) |
| `caption_bulk_batch_size` | none | 1, 5, 10, 20, 30, 40, 50 | Size of ZIP jobs |

### Summaries (`_sum` and `_count`)
| Metric | Labels | Observed | Why monitored |
|---|---|---|---|
| `caption_inference_summary_seconds` | `mode` | Inference time per image | Exact mean via `_sum / _count` |
| `caption_image_size_bytes` | `mode` | Uploaded file size | Payload profile |
| `caption_caption_words` | `mode` | Words per caption | Output sanity (runaway or empty captions) |

*(The doubled name is correct: namespace `caption` plus metric `caption_words`.)*

### Info
`caption_app_info{model, version}`: static labels recording which model is served.

**Label cardinality note:** each distinct `(client_ip, session_id)` pair creates new time series. Fine for a lab, not for production.

---

## 2. Automatic metrics used
| Metric | Source | Used for |
|---|---|---|
| `up` | Prometheus (per target) | App/host status panels, `CaptionAppDown` |
| `node_cpu_seconds_total` | node_exporter | Host CPU %, `HostHighCPU` |
| `node_memory_MemAvailable_bytes`, `node_memory_MemTotal_bytes` | node_exporter | Host RAM %, `HostHighMemory` |
| `node_filesystem_avail_bytes`, `node_filesystem_size_bytes` | node_exporter | Disk used % |
| `node_load1` | node_exporter | Load average |
| `process_start_time_seconds` | prometheus_client | Uptime |

---

## 3. PromQL building blocks, worked by hand

### 3.1 `rate()` on a counter: per-second speed
`rate(counter[w])` = (last value minus first value in the window) / window length. Multiplying by 60 converts it to per minute.

Throughput panel: `sum by (mode) (rate(caption_images_processed_total{status="success"}[1m])) * 60`

*Example:* a 25-image ZIP raises the bulk counter by 25 inside one 60 s window.
`rate = 25 / 60 = 0.417 images/s`, then `x 60 = 25 images/min`.
Your numbers: counter before = ____, after = ____, window = ____ s, result = ____.

### 3.2 `increase()`: how many in a window
`increase(counter[1h])` = rate x 3600 (with extrapolation at the edges). It drives the "Images last hour" and "Top clients" panels.

### 3.3 `_sum / _count`: average
`rate(x_sum[w]) / rate(x_count[w])` = mean over the window (all-time mean if you use the raw values).

*Example:* `caption_inference_summary_seconds_sum{mode="bulk"} = 40.0`, `_count = 25`, so mean = 40.0 / 25 = **1.6 s per image**.
Your numbers: sum = ____, count = ____, mean = ____.

### 3.4 Reading cumulative histogram buckets
Buckets are cumulative: `le="2"` counts every observation <= 2 s. Per-bucket counts are differences.

*Example (25 bulk images):*
| `le` | cumulative | images in this bucket |
|---|---|---|
| 1 | 2 | 2 |
| 1.5 | 6 | 4 |
| 2 | 24 | 18 |
| 3 | 25 | 1 |
| +Inf | 25 | 0 |

### 3.5 `histogram_quantile()`: percentiles
Method: find the bucket holding the target rank, then interpolate linearly inside it.

*Example p95 (25 observations):*
1. Target rank = 0.95 x 25 = **23.75**
2. Cumulative: `le=1.5` has 6, `le=2` has 24, so rank 23.75 is in the **1.5 to 2 s** bucket
3. p95 = 1.5 + (23.75 - 6) / (24 - 6) x (2 - 1.5) = 1.5 + 17.75/18 x 0.5 = **1.99 s**

*Example p50:* rank 12.5 is in the same bucket: 1.5 + (12.5 - 6)/18 x 0.5 = **1.68 s**.

Your numbers: rank = ____, bucket = ____ to ____, result = ____. Compare with Grafana's p95 panel; a small gap is expected because the panel uses a 1 minute window, not all-time.

Limitation: it assumes values are evenly spread inside a bucket, so accuracy depends on bucket boundaries.

### 3.6 Host CPU busy %
`100 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100`
`node_cpu_seconds_total{mode="idle"}` counts idle seconds per core. Its rate is the idle fraction per core (0 to 1). Averaging across cores and subtracting from 100 gives busy %.
*Example:* idle rate 0.25 on average, so busy = 100 - 25 = **75 %**.

### 3.7 Host RAM used %
`100 * (1 - MemAvailable / MemTotal)`
*Example:* 16 GB total, 4 GB available, so 100 x (1 - 0.25) = **75 %**.

### 3.8 Error ratio with `clamp_min`
`errors_rate / clamp_min(total_rate, 1e-9)` avoids division by zero when idle (otherwise the result is NaN).
*Example:* 1 error in 25 images gives **4 %**.

---

## 4. Alert rules: logic and observed behaviour

| Alert | Expression | Logic | Observed (fill in from your run) |
|---|---|---|---|
| `CaptionAppDown` (critical) | `up{job="caption-app"} == 0`, 30 s | Prometheus sets `up = 0` when `:8000` cannot be scraped | ____ |
| `HighInferenceP95` (warning) | p95 over 2 m > 8 s, 1 m | Normal p95 is about 2 s, so 8 s is well above normal | ____ |
| `HighErrorRatio` (warning) | error ratio over 5 m > 0.1, 2 m | More than 10 % of images failing | ____ |
| `HostHighCPU` (warning) | host CPU busy > 90 %, 2 m | Sustained saturation | ____ |
| `HostHighMemory` (warning) | host RAM used > 90 %, 2 m | Memory pressure | ____ |

Evidence to capture: Prometheus Alerts page (Firing), the Alertmanager UI, and the webhook.site payload.

---

## 5. Findings from the metrics
> Write 3 to 4 findings from **your own** runs, for example:
> 1. Does host CPU rise when bulk throughput rises? By how much (read from the correlation panel)?
> 2. Is p95 for bulk higher than for single? What does that say about sustained load?
> 3. Does app memory stay flat during a ZIP (images are processed one at a time)?
> 4. How does ZIP-level time (`caption_request_seconds`) compare with the sum of per-image inference times?
