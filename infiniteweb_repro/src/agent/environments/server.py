import http.server
import socketserver
import threading
import os
import socket
from typing import Optional

class LocalWebServer:
    """A lightweight HTTP server to serve generated static website files."""
    
    def __init__(self, directory: str, port: int = 0):
        self.directory = os.path.abspath(directory)
        self.requested_port = port
        self.port: Optional[int] = None
        self.server: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None
        self._is_running = False

    def start(self):
        """Starts the server in a separate thread."""
        if self._is_running:
            return

        # Simple handler to serve files from the specified directory
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=kwargs.pop('directory'), **kwargs)
            
            def log_message(self, format, *args):
                # Suppress standard logging to keep console clean, or redirect to debug
                pass

        # Find an available port if requested_port is 0
        handler_factory = lambda *args, **kwargs: Handler(*args, directory=self.directory, **kwargs)
        
        try:
            self.server = socketserver.TCPServer(("", self.requested_port), handler_factory)
            self.port = self.server.server_address[1]
            self.url = f"http://localhost:{self.port}"
            
            self._is_running = True
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            print(f"🌍 Web server started at {self.url} (serving {self.directory})")
        except Exception as e:
            print(f"❌ Failed to start web server: {e}")
            self._is_running = False

    def stop(self):
        """Shuts down the server."""
        if not self._is_running:
            return
            
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        self._is_running = False
        print("🛑 Web server stopped.")

    @property
    def is_running(self) -> bool:
        return self._is_running
