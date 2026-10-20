"""
Shared test setup. Unit tests only: Kafka, Schema Registry, Elasticsearch, Kafka Connect
and Kibana are replaced by fakes, so no containers are needed.
"""
import importlib.util
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # makes the shared `common` package importable

from common.events import catalog  # noqa: E402


def load_app_module(app: str, module: str):
    """
    Import apps/<app>/src/<module>.py the way its container does (its src dir on sys.path),
    but under a unique name, because both apps have a main.py.
    """
    src = ROOT / "apps" / app / "src"
    sys.path.insert(0, str(src))
    try:
        spec = importlib.util.spec_from_file_location(f"{app}_{module}", src / f"{module}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(src))


@pytest.fixture(autouse=True)
def isolated_randomness_and_carts():
    """Deterministic randomness and no open carts leaking between tests."""
    random.seed(1234)
    catalog._open_carts.clear()
    yield
    catalog._open_carts.clear()


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text or str(self._payload)

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


class FakeHttp:
    """
    Stand-in for the `requests` module. Records every call; responses come from
    `routes`, a list of (method, url-substring, FakeResponse) checked in order.
    """

    def __init__(self, routes=()):
        self.routes = list(routes)
        self.calls = []

    def _respond(self, method, url, **kwargs):
        self.calls.append({"method": method.upper(), "url": url, **kwargs})
        for route_method, fragment, response in self.routes:
            if route_method == method.upper() and fragment in url:
                return response
        return FakeResponse(200, {})

    def request(self, method, url, **kwargs):
        return self._respond(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self._respond("GET", url, **kwargs)

    def put(self, url, **kwargs):
        return self._respond("PUT", url, **kwargs)

    def post(self, url, **kwargs):
        return self._respond("POST", url, **kwargs)

    def head(self, url, **kwargs):
        return self._respond("HEAD", url, **kwargs)

    def find(self, method, fragment):
        return [c for c in self.calls if c["method"] == method and fragment in c["url"]]


# Helpers exposed as fixtures (test modules can't import conftest directly).

@pytest.fixture
def app_module():
    return load_app_module


@pytest.fixture
def fake_http():
    return FakeHttp


@pytest.fixture
def fake_response():
    return FakeResponse
