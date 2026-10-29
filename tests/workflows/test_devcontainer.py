"""Guard the private Codespaces development setup against accidental changes."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.unit


def test_devcontainer_forwards_only_api_and_installs_locked_dependencies():
    config = json.loads((ROOT / ".devcontainer/devcontainer.json").read_text())
    assert config["forwardPorts"] == [8000]
    assert config["portsAttributes"]["8000"]["onAutoForward"] == "silent"
    assert config["postCreateCommand"] == "uv sync --locked"
    assert "postStartCommand" not in config
    assert "postAttachCommand" not in config
    assert config["build"]["dockerfile"] == "Dockerfile"


def test_devcontainer_pins_uv_without_copying_project_model_into_image():
    dockerfile = (ROOT / ".devcontainer/Dockerfile").read_text().splitlines()
    assert dockerfile == [
        "FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm",
        "COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv",
    ]
