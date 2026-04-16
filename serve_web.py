"""
Simple HTTP server to serve the web interface.
Serves files from the web/ directory on port 3000.

Run: python serve_web.py
Open: http://localhost:3000
"""

import http.server
import socketserver
import os
from pathlib import Path

# Change to web directory
web_dir = Path(__file__).parent / "web"
os.chdir(web_dir)

PORT = 3000

Handler = http.server.SimpleHTTPRequestHandler
Handler.extensions_map.update({
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
})

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"🌐 ChefMate Web Interface")
    print(f"=" * 60)
    print(f"📍 Serving at: http://localhost:{PORT}")
    print(f"📂 Directory: {web_dir}")
    print(f"\n✨ Open your browser and go to: http://localhost:{PORT}")
    print(f"\n⚠️  Make sure the following are running:")
    print(f"   • MCP Server (port 8002): python mcp_server.py")
    print(f"   • Langchain Agent (port 8000): python langchain_agent.py")
    print(f"\nPress Ctrl+C to stop\n")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Stopping server...")
        httpd.shutdown()
