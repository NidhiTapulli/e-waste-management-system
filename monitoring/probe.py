from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen
from urllib.error import URLError
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            healthy = 0
            try:
                with urlopen("http://host.docker.internal:8001/", timeout=3) as response:
                    data = json.loads(response.read().decode())
                    if response.status == 200 and data.get("message") == "EWaste API is running!":
                        healthy = 1
            except Exception:
                healthy = 0

            body = (
                "# HELP ewaste_api_up Whether the EWaste API is responding correctly\n"
                "# TYPE ewaste_api_up gauge\n"
                f"ewaste_api_up {healthy}\n"
            ).encode()

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"EWaste monitoring exporter is running")
    def log_message(self, format, *args):
        pass

HTTPServer(("0.0.0.0", 9100), Handler).serve_forever()
