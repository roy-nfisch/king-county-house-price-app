"""Exercise the workflow's smoke-check shell with offline Docker/curl stand-ins."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def smoke_shell(tmp_path):
    """Return the workflow shell and an environment with fake Docker/curl commands.

    Fake Docker reports a healthy container. Fake curl records requests and can
    return exit code 28 (timeout), even after printing valid prediction JSON.
    This checks shell error handling without real containers or HTTP requests.
    """
    workflow = (ROOT / ".github/workflows/publish-image.yml").read_text()
    step = workflow.split("- name: Check published image with the approved model", 1)[1]
    step = step.split("- name: Update latest", 1)[0]
    assert "shell: bash" in step  # GitHub's explicit bash shell enables pipefail.
    script = textwrap.dedent(step.split("run: |\n", 1)[1])
    commands = {
        "docker": 'case "$1" in\n'
        'run) if [ "$2" = --rm ]; then echo model.skops; fi ;;\n'
        "inspect) echo healthy ;;\nport) echo 127.0.0.1:1234 ;;\nesac\n",
        "curl": 'echo "$*" >> "$CURL_LOG"\n'
        "echo '{\"predicted_price\": 123}'\n"
        'case "$*" in *"/$FAIL_ENDPOINT"*) exit 28 ;; esac\n',
    }
    for name, content in commands.items():
        path = tmp_path / name
        path.write_text("#!/bin/sh\n" + content)
        path.chmod(0o755)
    (tmp_path / "python3").symlink_to(sys.executable)
    (tmp_path / "model.skops").touch()
    environment = dict(
        os.environ,
        PATH=f"{tmp_path}:{os.environ['PATH']}",
        GITHUB_WORKSPACE=str(tmp_path),
        REFERENCE="offline-image",
        CURL_LOG=str(tmp_path / "curl.log"),
    )
    return script, environment


@pytest.mark.parametrize("endpoint", ["health", "predict", "no-failure"])
def test_smoke_step_stops_on_curl_timeout(smoke_shell, endpoint):
    """Run the real smoke-check shell against successful or timed-out requests.

    A health timeout must prevent prediction; a prediction timeout must fail
    even with valid JSON in the pipe. With neither timeout, the step succeeds.
    """
    script, environment = smoke_shell
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        env=environment | {"FAIL_ENDPOINT": endpoint},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (result.returncode == 0) == (endpoint == "no-failure"), result.stderr
    calls = Path(environment["CURL_LOG"]).read_text().splitlines()
    assert len(calls) == (1 if endpoint == "health" else 2)
