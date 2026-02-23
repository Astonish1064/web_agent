"""
Integration validation using Playwright.
=========================================
Tests pages in a real browser environment using an embedded HTTP server
to enable Fetch API and other network-dependent features.
"""
import asyncio
import os
import threading
import socket
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from typing import Tuple, List, Optional
from contextlib import contextmanager


class QuietHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP handler that suppresses log output."""
    
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory
        super().__init__(*args, **kwargs)
    
    def translate_path(self, path):
        """Translate URL path to filesystem path using the specified directory."""
        # Remove leading slash and query string
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        path = path.lstrip('/')
        
        # If path is empty, use index.html
        if not path:
            path = 'index.html'
        
        return os.path.join(self.directory, path)
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


class HTTPServerContext:
    """
    Context manager for temporary HTTP server.
    
    Starts a simple HTTP server serving files from the specified directory,
    automatically finds an available port, and shuts down on exit.
    """
    
    def __init__(self, directory: str):
        self.directory = os.path.abspath(directory)
        self.server = None
        self.thread = None
        self.port = None
    
    def _find_free_port(self) -> int:
        """Find an available port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def __enter__(self):
        """Start the HTTP server."""
        self.port = self._find_free_port()
        
        # Create handler class with directory bound
        directory = self.directory
        class Handler(QuietHTTPHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)
        
        self.server = TCPServer(('127.0.0.1', self.port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        return False
    
    @property
    def base_url(self) -> str:
        """Get the base URL for the server."""
        return f"http://127.0.0.1:{self.port}"


class IntegrationValidator:
    """
    Validates frontend pages using Playwright.
    
    Uses an embedded HTTP server to serve pages, enabling Fetch API
    and other network-dependent JavaScript features.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 10000):
        self.headless = headless
        self.timeout = timeout
    
    async def validate_page(
        self, 
        output_dir: str, 
        page_file: str
    ) -> Tuple[bool, List[str]]:
        """
        Validates a single page for JS errors and console issues.
        
        Uses an HTTP server to serve the page, enabling Fetch API.
        
        Args:
            output_dir: Directory containing HTML files
            page_file: Name of the HTML file to test
            
        Returns:
            Tuple of (success: bool, errors: List[str])
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return False, ["Playwright not installed"]
        
        page_path = os.path.join(output_dir, page_file)
        if not os.path.exists(page_path):
            return False, [f"Page not found: {page_file}"]
        
        errors = []
        
        # Use HTTP server instead of file:// protocol
        with HTTPServerContext(output_dir) as server:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                
                # Capture console errors (but ignore non-critical resource failures)
                def on_console(msg):
                    # Only capture actual errors, not warnings
                    if msg.type == "error":
                        text = msg.text
                        # Ignore common non-critical 404 errors (images, CSS, fonts, etc.)
                        non_critical_patterns = [
                            "favicon.ico",
                            "404",  # Generic 404 errors for resources
                            ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",  # Images
                            ".css",  # Stylesheets
                            ".woff", ".woff2", ".ttf", ".eot",  # Fonts
                            ".mp3", ".mp4", ".wav", ".ogg",  # Media
                        ]
                        text_lower = text.lower()
                        is_non_critical = any(pattern in text_lower for pattern in non_critical_patterns)
                        if not is_non_critical:
                            errors.append(f"Console error: {text}")
                
                page.on("console", on_console)
                
                # Capture page errors (uncaught exceptions)
                page.on("pageerror", lambda err: errors.append(f"Page error: {err}"))
                
                try:
                    url = f"{server.base_url}/{page_file}"
                    await page.goto(url, timeout=self.timeout)
                    await page.wait_for_load_state("networkidle", timeout=self.timeout)
                except Exception as e:
                    errors.append(f"Navigation error: {str(e)}")
                
                await browser.close()
        
        return len(errors) == 0, errors
    
    async def validate_all_pages(
        self, 
        output_dir: str, 
        page_files: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Validates multiple pages using a shared HTTP server.
        
        Args:
            output_dir: Directory containing HTML files
            page_files: List of HTML file names to test
            
        Returns:
            Tuple of (all_success: bool, all_errors: List[str])
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return False, ["Playwright not installed"]
        
        all_errors = []
        
        # Use single HTTP server for all pages
        with HTTPServerContext(output_dir) as server:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                
                for page_file in page_files:
                    page_path = os.path.join(output_dir, page_file)
                    if not os.path.exists(page_path):
                        all_errors.append(f"[{page_file}] Page not found")
                        continue
                    
                    page = await browser.new_page()
                    page_errors = []
                    
                    def on_console(msg):
                        if msg.type == "error":
                            text = msg.text
                            # Ignore common non-critical 404 errors (images, CSS, fonts, etc.)
                            non_critical_patterns = [
                                "favicon.ico",
                                "404",  # Generic 404 errors for resources
                                ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",  # Images
                                ".css",  # Stylesheets
                                ".woff", ".woff2", ".ttf", ".eot",  # Fonts
                                ".mp3", ".mp4", ".wav", ".ogg",  # Media
                            ]
                            text_lower = text.lower()
                            is_non_critical = any(pattern in text_lower for pattern in non_critical_patterns)
                            if not is_non_critical:
                                page_errors.append(f"Console error: {text}")
                    
                    page.on("console", on_console)
                    page.on("pageerror", lambda err: page_errors.append(f"Page error: {err}"))
                    
                    try:
                        url = f"{server.base_url}/{page_file}"
                        await page.goto(url, timeout=self.timeout)
                        await page.wait_for_load_state("networkidle", timeout=self.timeout)
                    except Exception as e:
                        page_errors.append(f"Navigation error: {str(e)}")
                    
                    await page.close()
                    
                    if page_errors:
                        all_errors.extend([f"[{page_file}] {e}" for e in page_errors])
                
                await browser.close()
        
        return len(all_errors) == 0, all_errors
    
    async def check_element_exists(
        self, 
        output_dir: str, 
        page_file: str, 
        selector: str
    ) -> bool:
        """
        Checks if an element exists on the page.
        
        Args:
            output_dir: Directory containing HTML files
            page_file: Name of the HTML file
            selector: CSS selector to find
            
        Returns:
            True if element exists
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return False
        
        page_path = os.path.join(output_dir, page_file)
        if not os.path.exists(page_path):
            return False
        
        with HTTPServerContext(output_dir) as server:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    url = f"{server.base_url}/{page_file}"
                    await page.goto(url, timeout=self.timeout)
                    element = await page.query_selector(selector)
                    exists = element is not None
                except Exception:
                    exists = False
                
                await browser.close()
        
        return exists

