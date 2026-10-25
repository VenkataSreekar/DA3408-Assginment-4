# AI Usage Disclosure

## AI Tool Used
- Claude (Anthropic), via the claude.ai chat.

## How It Was Used and Impact

1. **Code and configuration generation**
   - Claude drafted the Streamlit app (`app.py`), the instrumentation module (`metrics.py`), `prometheus.yml`, `alert_rules.yml`, `alertmanager.yml`, `make_test_zip.py`, an optional dashboard generator (`gen_dashboard.py`) and the README.
   - PromQL and regex are attributed with prompts in [`AI_prompt_usage.md`](AI_prompt_usage.md), as required.
   - **Impact:** Saved setup time, leaving more time for running the stack, testing and understanding the metrics.

2. **Conceptual clarification**
   - Claude explained Counters, Gauges, Histograms and Summaries, plus `rate()`, `increase()` and `histogram_quantile()`, and why each panel is on the dashboard.
   - **Impact:** Helped me understand how the pipeline fits together (app, Prometheus, node_exporter, Alertmanager, Grafana).

3. **Debugging and troubleshooting**
   - Claude helped with: the harmless Streamlit file-watcher / `torchvision` warnings, installing node_exporter, Prometheus and Alertmanager on Linux, why Alertmanager does not appear on the Targets page, and Grafana panel setup using the Builder.
   - **Impact:** Helped identify causes and get the stack running.

4. **Command and documentation assistance**
   - Claude supplied the terminal commands (including downloading 25 sample images) and structured the README and this disclosure.

## Responsibility
> Tick only what is true, and delete the rest. Do not submit this section unedited.

- [ ] I reviewed, executed and understood the code, configuration and commands in the final submission.
- [ ] The app, Prometheus, node_exporter, Alertmanager and Grafana were run on my own machine.
- [ ] I built the Grafana dashboard panels myself in the UI (Builder) and exported the JSON from Grafana.
- [ ] All screenshots, the metrics snapshot and the numbers in `METRICS.md` come from my real runs.
- [ ] I verified the hand calculations in `METRICS.md` against the values shown by Prometheus and Grafana.
