#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import sys
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler



def list_models(base_url, api_key, only_loaded, timeout):
    """Return model ids from /v1/models.

    With ``only_loaded`` (default) only models whose ``status.value == "loaded"``
    are returned; otherwise every model is returned.
    """
    req = urllib.request.Request(base_url + '/v1/models')
    req.add_header('accept', 'application/json')
    req.add_header('Authorization', 'Bearer ' + api_key)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    if only_loaded:
        return [m['id'] for m in data.get('data', []) if m.get('status', {}).get('value') == 'loaded']
    return [m['id'] for m in data.get('data', [])]


def fetch_model_metrics(base_url, api_key, model, timeout):
    """Return the Prometheus text metrics for a single model."""
    params = urllib.parse.urlencode({'model': model})
    req = urllib.request.Request(base_url + '/metrics?' + params)
    req.add_header('accept', 'text/plain')
    req.add_header('Authorization', 'Bearer ' + api_key)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8')


def add_model_label(text, model_id):
    """Tag every metric line in ``text`` with ``model="<id>"``.

    The llama-server ``/metrics`` endpoint does not label its own lines, so
    metrics from different models would otherwise collide. HELP/TYPE/comment
    lines are passed through untouched.
    """
    label = 'model="%s"' % model_id
    out = []
    for line in text.splitlines():
        if not line or line.startswith('#'):
            out.append(line)
            continue
        brace = line.find('{')
        if brace == -1:
            parts = line.split(None, 1)
            if len(parts) == 2:
                out.append('%s{%s} %s' % (parts[0], label, parts[1]))
            else:
                out.append(line)
        else:
            close = line.rfind('}')
            if close != -1:
                out.append(line[:close] + ',' + label + '}' + line[close + 1:])
            else:
                out.append(line)
    return '\n'.join(out) + '\n'


def fetch_all_metrics(base_url, api_key, models, only_loaded, timeout):
    """Fetch metrics for every model and join them into one blob.

    With ``only_loaded`` (default) only models whose ``status.value == "loaded"``
    are scraped; otherwise every model from ``/v1/models`` is used. Each model's
    metrics are tagged with its own ``model="..."`` label, so the joined output
    keeps every metric separated by model name.
    """
    try:
        if models is None:
            if only_loaded:
                models = list_models(base_url, api_key, only_loaded=True, timeout=timeout)
            else:
                models = list_models(base_url, api_key, only_loaded=False, timeout=timeout)
    except Exception:
        models = []
    chunks = ["""# HELP llama_exporter_online exporter application online flag.
# TYPE llama_exporter_online gauge
llama_exporter_online 1"""]
    for model in models:
        try:
            raw = fetch_model_metrics(base_url, api_key, model, timeout=timeout)
            chunks.append(add_model_label(raw, model))
        except Exception:
            logging.exception('Failed to fetch metrics for model=%s', model)
    return ''.join(chunks)


class MyHttpRequestHandler(BaseHTTPRequestHandler):

    def fetch_metrics(self):
        return fetch_all_metrics(
            self.server.base_url,
            self.server.api_key,
            self.server.models,
            self.server.only_loaded,
            self.server.timeout,
        )

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()

    def do_GET(self):
        # https://gist.github.com/mdonkers/63e115cc0c79b4f6b8b3a6b797e485c7
        # logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        output = self.fetch_metrics()
        self._set_response()
        self.wfile.write(output.encode('utf-8'))


class MyHttpServer(HTTPServer):
    def __init__(self, server_address, base_url, api_key, models, only_loaded, timeout, handler_class=MyHttpRequestHandler):
        super().__init__(server_address, handler_class)
        self.base_url = base_url
        self.api_key = api_key
        self.models = models
        self.only_loaded = only_loaded
        self.timeout = timeout
        if not only_loaded:
            if not self.models:
                self.models = list_models(self.base_url, self.api_key, only_loaded=False, timeout=self.timeout)
                logging.info('Models: %s', self.models)
        else:
            logging.info('Only loaded models will be displayed at each metrics query.')


def run(base_url, api_key, port, host, models, only_loaded, timeout):
    logging.basicConfig(level=logging.INFO)
    server_class = MyHttpServer
    server_address = (host, port)
    httpd = server_class(server_address, base_url, api_key, models, only_loaded, timeout)
    logging.info('Starting httpd on %s:%s...\n', host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')


def build_arg_parser():
    ap = argparse.ArgumentParser(
        description="Expose llama-server metrics to Prometheus.",
    )
    ap.add_argument(
        "--url",
        default="http://127.0.0.1:9931",
        help="llama-server base URL (default: http://127.0.0.1:9931)",
    )
    ap.add_argument(
        "--api-key",
        default="NONE",
        help="llama-server API key (default: NONE)",
    )
    ap.add_argument(
        "--host",
        default="127.0.0.1",
        help="host/interface the exporter listens on (default: 127.0.0.1)",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=9186,
        help="port the exporter listens on (default: 9186)",
    )
    ap.add_argument(
        "--model",
        action="append",
        metavar="ID",
        help="restrict to a specific model id (repeatable); "
             "defaults to the loaded models discovered via /v1/models",
    )
    ap.add_argument(
        "--only-loaded",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="only scrape models whose status.value == \"loaded\" "
             "(default: True; pass --no-only-loaded to scrape all models)",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=0.1,
        help="upstream request timeout in seconds (default: 0.1)",
    )
    return ap


def main() -> int:
    args = build_arg_parser().parse_args()
    run(
        base_url=args.url,
        api_key=args.api_key,
        port=args.port,
        host=args.host,
        models=args.model,
        only_loaded=args.only_loaded,
        timeout=args.timeout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
