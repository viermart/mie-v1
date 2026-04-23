"""
Simple HTTP server to serve mie_status.html
Runs on port 8000 so you can access it at http://localhost:8000 (local)
or http://your-railway-url:8000 (Railway)
"""

import http.server
import socketserver
from pathlib import Path
import logging

class StatusHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that serves mie_status.html"""

    def do_GET(self):
        # If root path, serve mie_status.html
        if self.path == "/" or self.path == "/status":
            self.path = "/mie_status.html"

        # Default file server behavior
        return super().do_GET()

    def log_message(self, format, *args):
        """Custom logging"""
        logger = logging.getLogger("HTTPServer")
        logger.info(format % args)


def start_server(port=8000, logger=None):
    """Start HTTP server in background"""
    import threading

    if logger:
        logger.info(f"🌐 Starting HTTP server on port {port}...")

    # Change to app directory so SimpleHTTPRequestHandler can serve files
    import os
    os.chdir(Path(__file__).parent.parent)

    Handler = StatusHandler
    httpd = socketserver.TCPServer(("0.0.0.0", port), Handler)

    def run_server():
        if logger:
            logger.info(f"✅ HTTP server ready at http://0.0.0.0:{port}")
        httpd.serve_forever()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    return httpd
