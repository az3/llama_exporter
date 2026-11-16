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

## License

MIT.
