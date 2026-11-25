"""Serve the commerce workspace and keep the search token on localhost."""

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

if __package__:
    from .discovery import DiscoveryError, MARKETS, discover
else:
    from discovery import DiscoveryError, MARKETS, discover


ROOT = Path(__file__).resolve().parent
FILES = {
    "/": ("index.html", "text/html"),
    "/index.html": ("index.html", "text/html"),
    "/desk-cable-case.html": ("desk-cable-case.html", "text/html"),
    "/desk-cable-concept.webp": ("desk-cable-concept.webp", "image/webp"),
    "/styles.css": ("styles.css", "text/css"),
    **{f"/{name}.js": (f"{name}.js", "text/javascript") for name in ("evidence", "analysis", "zh", "app")},
}
MAX_BODY = 4096
ERROR_CODES = {"auth": 502, "quota": 429, "timeout": 504, "provider": 502}


def token():
    return os.getenv("BRAVE_SEARCH_API_KEY", "").strip()


def validate_request(payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_input")
    scene, market, keywords = (payload.get("scene"), payload.get("market"), payload.get("keywords", ""))
    if not isinstance(scene, str) or not 2 <= len(scene.strip()) <= 400:
        raise ValueError("invalid_scene")
    if not isinstance(market, str) or market not in MARKETS:
        raise ValueError("invalid_market")
    if not isinstance(keywords, str) or len(keywords.strip()) > 120:
        raise ValueError("invalid_keywords")
    return scene.strip(), market, keywords.strip()


class WorkspaceHandler(BaseHTTPRequestHandler):
    def respond(self, status, content, content_type):
        self.send_response(status)
        if content_type.startswith("text/") or content_type == "application/json":
            content_type += "; charset=utf-8"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def json_response(self, status, payload):
        self.respond(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json")

    def local_request(self):
        port = self.server.server_port
        host = self.headers.get("Host")
        origin = self.headers.get("Origin")
        return host in {f"127.0.0.1:{port}", f"localhost:{port}"} and (not origin or origin == f"http://{host}")

    def do_GET(self):
        if not self.local_request():
            return self.json_response(HTTPStatus.FORBIDDEN, {"error": "local_only"})
        path = urlsplit(self.path).path
        if path == "/api/status":
            return self.json_response(HTTPStatus.OK, {"configured": bool(token())})
        if path in FILES:
            filename, content_type = FILES[path]
            return self.respond(HTTPStatus.OK, (ROOT / filename).read_bytes(), content_type)
        return self.json_response(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):
        if not self.local_request():
            return self.json_response(HTTPStatus.FORBIDDEN, {"error": "local_only"})
        if urlsplit(self.path).path != "/api/discover":
            return self.json_response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        if self.headers.get_content_type() != "application/json":
            return self.json_response(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "invalid_input"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                raise ValueError("invalid_input")
            scene, market, keywords = validate_request(json.loads(self.rfile.read(length)))
        except (ValueError, UnicodeError) as exc:
            code = str(exc) if str(exc).startswith("invalid_") else "invalid_input"
            return self.json_response(HTTPStatus.BAD_REQUEST, {"error": code})
        secret = token()
        if not secret:
            return self.json_response(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "unconfigured"})
        try:
            result = discover(scene, market, secret, keywords)
        except DiscoveryError as exc:
            return self.json_response(ERROR_CODES.get(exc.code, HTTPStatus.BAD_GATEWAY), {"error": exc.code})
        return self.json_response(HTTPStatus.OK, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), WorkspaceHandler) as server:
        print(f"Commerce workspace: http://127.0.0.1:{server.server_port}", flush=True)
        print(f"Live search: {'configured' if token() else 'key required'}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
