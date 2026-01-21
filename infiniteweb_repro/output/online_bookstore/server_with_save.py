import http.server
import socketserver
import json
import os

PORT = 8080

class TrajectoryHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save_trajectory':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # Validate JSON
                trajectory = json.loads(post_data.decode('utf-8'))
                
                # Save to disk
                with open('trajectory.json', 'w') as f:
                    json.dump(trajectory, f, indent=2)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Trajectory saved to trajectory.json"}).encode('utf-8'))
                print("Size of trajectory received:", len(trajectory))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_error(404, "File not found")


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

print(f"Starting server on port {PORT} with POST support...")
# Use ReusableTCPServer instead of TCPServer
with ReusableTCPServer(("", PORT), TrajectoryHandler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    httpd.serve_forever()
