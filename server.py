import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import PORT

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bilig AI Bot is alive and running!")

    def log_message(self, format, *args):
        pass  # Konsolga ortiqcha log yozmaslik uchun

class ReusableTCPServer(HTTPServer):
    allow_reuse_address = True

def run_dummy_server():
    server = ReusableTCPServer(('0.0.0.0', PORT), HealthCheckHandler)
    server.serve_forever()
