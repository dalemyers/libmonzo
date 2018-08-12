#!/usr/bin/env python3

"""Utility methods for libmonzo."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import secrets
import threading
from typing import Any, Callable, Dict, Optional, Type
import urllib.parse

RequestCallback = Callable[[str], None]

_SECRETS_ALPHABET: str = "ABCDEFGHIJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def random_string(length: int) -> str:
    """Generate a secure random string of length specified."""
    return ''.join([secrets.choice(_SECRETS_ALPHABET) for _ in range(0, length)])


def create_request_handler(callback: RequestCallback) -> Type[BaseHTTPRequestHandler]:
    """Create a new request handler."""
    class _SimpleRequestHandler(BaseHTTPRequestHandler):

        callback_reference: RequestCallback

        def __init__(self, request, client_address, server) -> None:
            self.callback_reference = callback
            super().__init__(request, client_address, server)

        def base_handler(self) -> None:
            """Base handler for all kinds of calls."""
            self.send_response(200)
            self.end_headers()
            self.wfile.write("Done. Please go back to the app.".encode('utf-8'))
            self.callback_reference(self.path)

        do_GET = base_handler
        do_POST = base_handler
        do_PUT = base_handler
        do_DELETE = base_handler

    return _SimpleRequestHandler

class OAuthServer(HTTPServer):
    """Simple OAuth helper server."""

    _not_cancelled: bool
    _completed: bool
    _path: Optional[str]

    def __init__(self, port: int) -> None:
        self._cancelled = False
        self._completed = False
        self._path = None
        self.timeout = 0.2
        self.lock = threading.Lock()

        def _callback(path: str) -> None:
            self.handler_callback(path)

        handler = create_request_handler(_callback)
        super().__init__(('', port), handler)

    def handler_callback(self, path: str) -> None:
        """Callback for the handler to complete."""
        self.lock.acquire()
        self._completed = True
        self.path = path
        self.lock.release()

    def wait_for_call(self) -> Optional[Dict[str, Any]]:
        """Wait for the callback to occur."""
        while True:

            try:
                self.lock.acquire()

                if self._completed:
                    break

                if self._cancelled:
                    break

            finally:
                self.lock.release()

            self.handle_request()


        try:
            self.lock.acquire()

            if self._cancelled:
                return None

            if self._completed:
                query = urllib.parse.urlparse(self.path).query
                return urllib.parse.parse_qs(query)

            raise Exception("Call should be cancelled or completed by this point")

        finally:
            self.lock.release()


    def stop(self) -> None:
        """Stop running the server."""
        self.lock.acquire()
        self._cancelled = True
        self.lock.release()
