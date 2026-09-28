import os
import sys
import time
import socket
import threading
import pytest
from werkzeug.serving import make_server

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app as flask_application, client as global_client
from stratz_client import StratzClient


@pytest.fixture(scope="session")
def app():
    """Provides Flask application configured for testing."""
    flask_application.config["TESTING"] = True
    return flask_application


@pytest.fixture(scope="session")
def client(app):
    """Provides Flask test client for API requests."""
    return app.test_client()


@pytest.fixture(scope="session")
def stratz_client():
    """Provides initialized StratzClient using cached Dota 2 data."""
    return global_client


def get_free_port():
    """Finds an unused port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServerThread(threading.Thread):
    """Background thread running Flask server via Werkzeug make_server."""
    def __init__(self, app, host, port):
        super().__init__()
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


@pytest.fixture(scope="session")
def live_server_url(app):
    """Starts live HTTP server for Playwright browser E2E tests."""
    port = get_free_port()
    host = "127.0.0.1"
    server_thread = ServerThread(app, host, port)
    server_thread.daemon = True
    server_thread.start()

    url = f"http://{host}:{port}"

    import requests
    max_wait = 10
    start = time.time()
    ready = False
    while time.time() - start < max_wait:
        try:
            r = requests.get(f"{url}/api/status", timeout=1)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.1)

    if not ready:
        raise RuntimeError("Live test server failed to start within timeout.")

    yield url

    try:
        server_thread.shutdown()
    except Exception:
        pass
