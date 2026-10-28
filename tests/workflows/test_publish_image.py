"""Offline release-safety regressions; never authenticate or publish images."""

import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.unit


@pytest.fixture
def registry(monkeypatch):
    """Load the release helper and replace all network requests with a mock."""
    spec = importlib.util.spec_from_file_location(
        "check_image_version", ROOT / ".github/scripts/check_image_version.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    network = MagicMock()
    token = MagicMock()
    token.__enter__.return_value = io.StringIO('{"token": "test-token"}')
    network.side_effect = [token, MagicMock()]
    monkeypatch.setattr(module, "urlopen", network)
    return module, network, token


def registry_error(status, codes):
    """Build a structured registry HTTP error without using a real service."""
    body = json.dumps({"errors": [{"code": code} for code in codes]}).encode()
    return HTTPError("https://ghcr.io/test", status, "test", {}, io.BytesIO(body))


@pytest.mark.parametrize("code", ["MANIFEST_UNKNOWN", "NAME_UNKNOWN"])
def test_only_explicit_missing_version_is_allowed(registry, code):
    """Allow a new tag only when GHCR explicitly reports it or its image missing.

    Fake both registry responses; check the requested tag, bearer token, and
    network timeouts without contacting GHCR or using real credentials.
    """
    module, network, token = registry
    network.side_effect = [token, registry_error(404, [code])]
    module.check_version("ghcr.io/owner/app", "2026.10.29", "actor", "secret")
    assert network.call_count == 2
    for call in network.call_args_list:
        assert call.kwargs["timeout"] == 10
    request = network.call_args.args[0]
    assert request.full_url.endswith("/owner/app/manifests/2026.10.29")
    assert request.get_header("Authorization") == "Bearer test-token"


def test_existing_version_is_rejected(registry):
    """A successful manifest lookup means the tag exists, so reject its reuse."""
    module, _, _ = registry
    with pytest.raises(RuntimeError, match="already exists"):
        module.check_version("ghcr.io/owner/app", "2026.10.29", "actor", "secret")


@pytest.mark.parametrize(
    "error",
    [
        registry_error(401, ["UNAUTHORIZED"]),
        registry_error(403, ["DENIED"]),
        registry_error(429, ["TOOMANYREQUESTS"]),
        registry_error(500, ["UNKNOWN"]),
        registry_error(404, ["DENIED"]),
        registry_error(404, []),
        URLError("offline"),
        TimeoutError("timed out"),
        HTTPError("https://ghcr.io/test", 404, "test", {}, io.BytesIO(b"bad")),
    ],
)
@pytest.mark.parametrize("phase", ["token", "manifest"])
def test_registry_failures_never_allow_publishing(registry, error, phase):
    """Errors must stop the check, not be mistaken for an unused version.

    Try each failure while obtaining a token and while looking up the tag.
    Cover access errors, rate limits, outages, timeouts, and invalid responses.
    """
    module, network, token = registry
    network.side_effect = [error] if phase == "token" else [token, error]
    with pytest.raises((HTTPError, URLError, TimeoutError, ValueError, RuntimeError)):
        module.check_version("ghcr.io/owner/app", "2026.10.29", "actor", "secret")


def test_workflow_checks_version_before_any_push():
    """Check step ordering: reject reused versions first; verify before latest.

    Inspect the workflow text only; this does not run GitHub Actions or push.
    """
    workflow = (ROOT / ".github/workflows/publish-image.yml").read_text()
    check = workflow.index("run: python3 .github/scripts/check_image_version.py")
    assert check < workflow.index('docker push "$IMAGE:$VERSION"')
    assert workflow.index("Update latest after verification") > workflow.index(
        "Check published image with the approved model"
    )


@pytest.mark.parametrize("endpoint", ["health", "predict"])
def test_post_publish_http_checks_have_bounded_timeouts(endpoint):
    """Require connection/total time limits and HTTP failure handling on both URLs."""
    workflow = (ROOT / ".github/workflows/publish-image.yml").read_text()
    command = next(
        line for line in workflow.splitlines() if f"$port/{endpoint}" in line
    )
    assert "--connect-timeout 5" in command
    assert "--max-time 15" in command
    assert "--fail" in command
