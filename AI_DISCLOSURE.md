
This file documents how AI was used, as required by the assignment's Code of Conduct
(*Fair Use of AI*: the "Black Box" Metric Rule and Attribution).

## 1. Tool used
- **Claude (Anthropic)**, via the claude.ai chat interface.

## 2. What the AI generated
| Artifact | AI involvement | Where attributed |
|---|---|---|
| `app.py` (Streamlit UI, Single/Bulk logic, ZIP safeguards) | Drafted by AI, run and tested by me | This file |
| `metrics.py` (Counters, Gauges, Histograms, Summaries, Info, labels) | Drafted by AI, run and tested by me | This file |
| `prometheus.yml`, `alertmanager.yml` | Drafted by AI | Comments in file |
| `alert_rules.yml` (PromQL alert expressions) | PromQL drafted by AI | "Prompt used" comment in file |
| Grafana dashboard PromQL queries | Queries suggested by AI; panels built by me in the Grafana UI (Builder) | Section 3 below |
| `make_test_zip.py`, `README.md` | Drafted by AI | This file |
| `gen_dashboard.py` (optional reference generator, not used for my submitted dashboard) | Drafted by AI | Prompt comment in file |

## 3. Prompts used for PromQL / regex
> **Edit this section so it matches the exact prompts you actually used.**

**Prompt 1 (app, metrics, configs):**
```
<paste your original prompt here>
```

**Prompt 2 (dashboard queries):**
```
<paste your prompt here>
```

**Regex used (Grafana overrides / label matchers):**
| Pattern | Used for | Prompt / source |
|---|---|---|
| `caption-app\|node` (label `job`, `=~`) | Combined up/down status of both scrape targets | <prompt> |
| `single`, `bulk` (override: field name matching regex) | Consistent colour per mode | <prompt> |
| `invalid.*\|inference.*\|bad_zip\|zip_rejected` (label `error_type`, `=~`) | Errors-per-minute panel | <prompt> |
| `tmpfs\|rootfs` (label `fstype`, `!~`) | Exclude virtual filesystems from disk-used % | <prompt> |

## 4. What I did myself
Tick only what is true for you:
- [ ] Installed and configured Prometheus, node_exporter, (Alertmanager) and Grafana on my machine
- [ ] Ran the app and verified `/metrics` on port 8000
- [ ] Confirmed all scrape targets show UP in Prometheus
- [ ] Built the Grafana dashboard panels in the UI and applied the Seven Commandments
- [ ] Exported the dashboard JSON from Grafana
- [ ] Recorded the dashboard video at 5 s refresh
- [ ] Modified AI output where needed (describe: ______________________)

## 5. Manual verification of metric logic (Black Box Rule)
I can explain the following by hand:
- `rate(counter[1m]) * 60`: rate gives the per-second average increase; ×60 gives per minute; rate handles counter resets.
- `histogram_quantile(q, sum by (le)(rate(..._bucket[1m])))`: sums bucket rates while keeping `le`, then linearly interpolates inside the bucket that contains the q-th quantile; accuracy depends on bucket boundaries.
- `rate(_sum) / rate(_count)`: mean value of the observed quantity over the window.
- `100 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100`: idle seconds per second per core, averaged, converted to busy %.
- `100 * (1 - MemAvailable / MemTotal)`: fraction of RAM that is not reclaimable.
- `errors / clamp_min(total, 1e-9)`: error ratio without division by zero when idle.

## 6. Limitations I am aware of
- `client_ip` and `session_id` are high-cardinality labels: acceptable for this lab, not for production.
- Host panels use Linux node_exporter metric names.
- Quantiles from histograms are estimates bounded by bucket layout.

*Declaration: the above is an accurate account of AI use in this submission.*

Name: ____________________   Roll no.: ____________   Date: ____________
