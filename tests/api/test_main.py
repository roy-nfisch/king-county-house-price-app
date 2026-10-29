"""Check how the application factory wires environment settings into the API."""

import pytest

from api.main import create_app

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("mode", ["local", "cloud"])
def test_app_factory_uses_environment_configuration(monkeypatch, mode):
    """The same factory reads either mode without needing a cloud host."""
    token = "a" * 32 if mode == "cloud" else None
    monkeypatch.setenv("API_MODE", mode)
    if token is None:
        monkeypatch.delenv("API_TOKEN", raising=False)
    else:
        monkeypatch.setenv("API_TOKEN", token)

    app = create_app()

    assert app.state.cloud_mode is (mode == "cloud")
    assert app.state.api_token == token
