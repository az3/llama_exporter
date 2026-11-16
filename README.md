# llama_exporter

Prometheus exporter for [llama.cpp](https://github.com/ggerganov/llama.cpp) metrics.

Scrapes a running `llama-server` instance, tags every metric with a `model` label, and exposes a clean 
Prometheus-compatible endpoint. No dependencies — pure Python standard library.

## Why

`llama-server` exposes raw Prometheus metrics on `/metrics`, but they carry no model label. 
When multiple models are loaded, their metrics collide. This exporter fetches metrics per model, 
injects a `model="<id>"` label, and serves the combined output so Prometheus can distinguish them.

It also re-discovers loaded models on every scrape to avoid triggering unwanted model loads 
when an unloaded model is queried.

## Installation

No pip, no build step. Just copy the single file:

```sh
sudo cp llama_exporter.py /usr/local/bin/llama_exporter.py
sudo chmod +x /usr/local/bin/llama_exporter.py
```

Requires **Python 3.9+**.

## Usage

```sh
llama_exporter.py \
  --url http://127.0.0.1:9931 \
  --api-key YOUR_KEY \
  --port 9186
```

Then point Prometheus at `http://<host>:9186/metrics`.

### Options

| Flag | Default | Description |
|---|---|---|
| `--url` | `http://127.0.0.1:9931` | llama-server base URL |
| `--api-key` | `NONE` | Bearer token for llama-server auth |
| `--host` | `127.0.0.1` | Interface to listen on |
| `--port` | `9186` | Port to listen on |
| `--model` | *(auto)* | Restrict to a specific model ID (repeatable) |
| `--only-loaded` | `true` | Only scrape currently loaded models |
| `--no-only-loaded` | — | Scrape all models from `/v1/models` |
| `--timeout` | `0.1` | Upstream request timeout in seconds |

## Systemd deployment

A sample unit file is included. Edit the `ExecStart` line to match your setup:

```ini
[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/llama_exporter.py \
  --host 127.0.0.1 --port 9186 \
  --url http://127.0.0.1:9931 --api-key "YOUR_KEY"
```

Then:

```sh
sudo cp llama_exporter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now llama_exporter
```

Finally in prometheus.yml
```yml
scrape_configs:
  - job_name: "llama_exporter"
    static_configs:
      - targets: ["127.0.0.1:9186"]
    scrape_interval: 5s
```

Sample output:
```
$ curl -s http://localhost:9186/metrics
# HELP llama_exporter_online exporter application online flag.
# TYPE llama_exporter_online gauge
llama_exporter_online 1
# HELP llamacpp:prompt_tokens_total Number of prompt tokens processed, excluding cached tokens
# TYPE llamacpp:prompt_tokens_total counter
llamacpp:prompt_tokens_total{model="Qwen3.6-35B-A3B-Code"} 33775
# HELP llamacpp:prompt_tokens_cached_total Number of prompt tokens reused from the cache
# TYPE llamacpp:prompt_tokens_cached_total counter
llamacpp:prompt_tokens_cached_total{model="Qwen3.6-35B-A3B-Code"} 1.31297e+06
# HELP llamacpp:prompt_seconds_total Total time spent processing prompts
# TYPE llamacpp:prompt_seconds_total counter
llamacpp:prompt_seconds_total{model="Qwen3.6-35B-A3B-Code"} 155.648
# HELP llamacpp:tokens_predicted_total Number of generation tokens processed
# TYPE llamacpp:tokens_predicted_total counter
llamacpp:tokens_predicted_total{model="Qwen3.6-35B-A3B-Code"} 14387
# HELP llamacpp:tokens_predicted_seconds_total Total time spent generating tokens
# TYPE llamacpp:tokens_predicted_seconds_total counter
llamacpp:tokens_predicted_seconds_total{model="Qwen3.6-35B-A3B-Code"} 472.432
# HELP llamacpp:n_decode_total Total number of llama_decode() calls, excluding speculative decoding and multimodal decoding
# TYPE llamacpp:n_decode_total counter
llamacpp:n_decode_total{model="Qwen3.6-35B-A3B-Code"} 14472
# HELP llamacpp:n_tokens_max Largest observed sequence length (prompt + generation)
# TYPE llamacpp:n_tokens_max counter
llamacpp:n_tokens_max{model="Qwen3.6-35B-A3B-Code"} 47817
# HELP llamacpp:spec_decode_num_draft_tokens_total Speculative: Total draft tokens generated
# TYPE llamacpp:spec_decode_num_draft_tokens_total counter
llamacpp:spec_decode_num_draft_tokens_total{model="Qwen3.6-35B-A3B-Code"} 0
# HELP llamacpp:spec_decode_num_accepted_tokens_total Speculative: Total draft tokens accepted by the target model
# TYPE llamacpp:spec_decode_num_accepted_tokens_total counter
llamacpp:spec_decode_num_accepted_tokens_total{model="Qwen3.6-35B-A3B-Code"} 0
# HELP llamacpp:spec_decode_num_drafts_total Speculative: Total speculative decoding verification steps
# TYPE llamacpp:spec_decode_num_drafts_total counter
llamacpp:spec_decode_num_drafts_total{model="Qwen3.6-35B-A3B-Code"} 0
# HELP llamacpp:prompt_tokens_seconds Average prompt throughput in tokens/s
# TYPE llamacpp:prompt_tokens_seconds gauge
llamacpp:prompt_tokens_seconds{model="Qwen3.6-35B-A3B-Code"} 0
# HELP llamacpp:predicted_tokens_seconds Average generation throughput in tokens/s
# TYPE llamacpp:predicted_tokens_seconds gauge
llamacpp:predicted_tokens_seconds{model="Qwen3.6-35B-A3B-Code"} 0
# HELP llamacpp:requests_processing Number of requests processing
# TYPE llamacpp:requests_processing gauge
llamacpp:requests_processing{model="Qwen3.6-35B-A3B-Code"} 0
# HELP llamacpp:requests_deferred Number of requests deferred
# TYPE llamacpp:requests_deferred gauge
llamacpp:requests_deferred{model="Qwen3.6-35B-A3B-Code"} 0
# HELP llamacpp:n_busy_slots_per_decode Average number of busy slots per llama_decode() call
# TYPE llamacpp:n_busy_slots_per_decode gauge
llamacpp:n_busy_slots_per_decode{model="Qwen3.6-35B-A3B-Code"} 1
```

## License

MIT.
