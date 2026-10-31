"""Local provider fixture used only by integration tests (never by production)."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time
from threading import Thread
from urllib.parse import parse_qs


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', '0'))).decode()
        text = parse_qs(body).get('text', [''])[0]
        if text == 'slow-preview':
            time.sleep(.4)
        if text == 'provider-offline':
            self.send_response(503)
            self.end_headers()
            return
        payload = json.dumps({'bully_type': [2] if 'bully-test' in text else 0}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, *args):
        pass


def start_provider():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
