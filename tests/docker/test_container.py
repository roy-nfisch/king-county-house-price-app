"""Opt-in smoke checks for the built runtime image, without a production model.

Set DOCKER_TEST_IMAGE to a locally built image. Only the healthy test process
overrides the digest of our own temporary fixture, in memory; the normal image
command and production approval constants stay unchanged.
"""

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

import pytest


def docker(*arguments, timeout=90):
    """Return both Docker streams; bound execution and surface failures."""
    return subprocess.run(
        ["docker", *arguments],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )


class DockerContainer:
    """Own one named test container and remove it on success or failure."""

    def __init__(self, image, model_path, command=()):
        """Store image, read-only model mount, and optional test-only command."""
        self.name = "king-county-test-" + uuid4().hex
        self.image = image
        self.model_path = model_path
        self.command = command

    def __enter__(self):
        """Create a stopped container before executing any bounded startup."""
        docker(
            "create",
            "--name",
            self.name,
            "--publish",
            "127.0.0.1::8000",
            "--mount",
            f"type=bind,source={self.model_path},target=/models/pipeline.skops,readonly",
            self.image,
            *self.command,
        )
        return self

    def __exit__(self, *exception):
        """Remove the owned container even when an attached Docker call times out."""
        docker("rm", "--force", self.name)

    def start(self, *, attach=False):
        """Start normally, or attach and wait for the normal entrypoint to exit."""
        options = ["--attach"] if attach else []
        return docker("start", *options, self.name)

    @property
    def url(self):
        """Return the randomly assigned localhost URL of this container."""
        port = docker("port", self.name, "8000/tcp").stdout.strip().rsplit(":", 1)[1]
        return f"http://127.0.0.1:{port}"

    def logs(self):
        """Preserve stdout and stderr, including Uvicorn startup tracebacks."""
        result = docker("logs", self.name)
        return result.stdout + result.stderr

    def wait_healthy(self, timeout=45):
        """Require Docker health, not just HTTP readiness; report useful failures."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = json.loads(
                docker("inspect", "--format", "{{json .State}}", self.name).stdout
            )
            health = state.get("Health", {}).get("Status")
            if not state["Running"] or health in (None, "unhealthy"):
                raise RuntimeError("Container failed readiness:\n" + self.logs())
            if health == "healthy":
                return
            time.sleep(0.25)
        raise RuntimeError("Container health timed out:\n" + self.logs())


@pytest.fixture
def image():
    """Skip only real Docker checks when no locally built image was selected."""
    value = os.getenv("DOCKER_TEST_IMAGE")
    if not value:
        pytest.skip("Build and set DOCKER_TEST_IMAGE first")
    return value


def request_json(url, payload=None):
    """Return status and decoded JSON for a health or prediction request."""
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        response = urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


@pytest.fixture
def container_url(approved_artifact, image):
    """Start the real image/app with the shared tiny artifact; always remove it."""
    digest = hashlib.sha256(approved_artifact.path.read_bytes()).hexdigest()
    startup = (
        "from king_county import artifacts; "
        f"artifacts.EXPECTED_MODEL_SHA256 = {digest!r}; "
        "import uvicorn; "
        "uvicorn.run('api.main:create_app', factory=True, host='0.0.0.0', port=8000)"
    )
    with DockerContainer(
        image, approved_artifact.path, ("python", "-c", startup)
    ) as app:
        app.start()
        app.wait_healthy()
        yield app.url


@pytest.mark.integration
@pytest.mark.docker
def test_container_includes_project_license(image):
    """The shipped runtime must retain the project's complete MIT notice."""
    script = (
        "from importlib.metadata import distribution; "
        "print(distribution('mle-refactoring-project').read_text('licenses/LICENSE'), end='')"
    )
    result = docker("run", "--rm", "--entrypoint", "python", image, "-c", script)
    expected = (Path(__file__).resolve().parents[2] / "LICENSE").read_text()
    assert result.stdout == expected


@pytest.mark.integration
@pytest.mark.docker
def test_container_serves_prediction(container_url, house_payload):
    """Check packaging, server startup, model loading and real network I/O."""
    status, body = request_json(container_url + "/predict", house_payload)
    assert status == 200, body
    assert body["predicted_price"] > 0


@pytest.mark.integration
@pytest.mark.docker
def test_normal_container_rejects_unapproved_model(approved_artifact, image):
    """The normal entrypoint must not trust our test model or its own digest."""
    with DockerContainer(image, approved_artifact.path) as app:
        with pytest.raises(subprocess.CalledProcessError) as failure:
            app.start(attach=True)
    assert "Model checksum mismatch" in failure.value.stderr


@pytest.mark.parametrize(
    "error",
    [subprocess.TimeoutExpired("start", 90), subprocess.CalledProcessError(3, "start")],
    ids=["timeout", "startup-failure"],
)
@pytest.mark.unit
def test_start_failure_still_removes_owned_container(monkeypatch, error):
    """Failures and timeouts must not leave the server-side container alive."""
    calls = []

    def run(*arguments, **kwargs):
        calls.append(arguments)
        if arguments[0] == "start":
            raise error
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setitem(globals(), "docker", run)
    app = DockerContainer("unused", Path("unused.skops"))
    with pytest.raises(type(error)), app:
        app.start(attach=True)
    assert calls[-1] == ("rm", "--force", app.name)


@pytest.mark.parametrize("failure", ["exited", "unhealthy", "missing", "timeout"])
@pytest.mark.unit
def test_health_failure_reports_both_log_streams(monkeypatch, failure):
    """Missing/broken health checks and early exits must fail with diagnostics."""
    state = {"Running": failure != "exited"}
    if failure != "missing":
        state["Health"] = {
            "Status": "starting" if failure == "timeout" else "unhealthy"
        }

    def run(*arguments, **kwargs):
        if arguments[0] == "inspect":
            return subprocess.CompletedProcess(arguments, 0, json.dumps(state), "")
        return subprocess.CompletedProcess(
            arguments, 0, "stdout-message\n", "traceback"
        )

    monkeypatch.setitem(globals(), "docker", run)
    app = DockerContainer("unused", Path("unused.skops"))
    with pytest.raises(RuntimeError, match="stdout-message\\ntraceback"):
        app.wait_healthy(timeout=0 if failure == "timeout" else 1)


@pytest.mark.unit
def test_docker_health_is_required_before_ready(monkeypatch):
    """Wait through starting until Docker itself reports healthy."""
    states = iter(["starting", "healthy"])

    def run(*arguments, **kwargs):
        state = {"Running": True, "Health": {"Status": next(states)}}
        return subprocess.CompletedProcess(arguments, 0, json.dumps(state), "")

    monkeypatch.setitem(globals(), "docker", run)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    assert DockerContainer("unused", Path("unused.skops")).wait_healthy() is None


@pytest.mark.integration
@pytest.mark.docker
def test_real_timeout_does_not_leave_a_container(approved_artifact, image):
    """Reproduce a client timeout with real Docker and verify server cleanup."""
    app = DockerContainer(
        image, approved_artifact.path, ("python", "-c", "import time; time.sleep(30)")
    )
    with pytest.raises(subprocess.TimeoutExpired), app:
        docker("start", "--attach", app.name, timeout=2)
    remaining = docker("ps", "--all", "--format", "{{.Names}}").stdout.splitlines()
    assert app.name not in remaining


@pytest.fixture
def compose_api(image, monkeypatch):
    """Parse Compose defaults without reading a developer's local .env file."""
    for variable in ("API_PORT", "MODEL_FILE", "COMPOSE_FILE", "COMPOSE_PROJECT_NAME"):
        monkeypatch.delenv(variable, raising=False)
    root = Path(__file__).resolve().parents[2]
    result = docker(
        "compose",
        "--env-file",
        os.devnull,
        "-f",
        str(root / "compose.yaml"),
        "config",
        "--format",
        "json",
    )
    return json.loads(result.stdout)["services"]["api"]


@pytest.mark.integration
@pytest.mark.docker
def test_compose_publishes_only_localhost(compose_api):
    """A refactor must not accidentally expose this unauthenticated API publicly."""
    (port,) = compose_api["ports"]
    assert (port["host_ip"], str(port["published"]), port["target"]) == (
        "127.0.0.1",
        "7003",
        8000,
    )


@pytest.mark.integration
@pytest.mark.docker
def test_compose_model_mount_is_read_only(compose_api):
    """Keep the model at the configured container path and prevent writes."""
    mount = next(m for m in compose_api["volumes"] if m["type"] == "bind")
    assert mount["type"] == "bind"
    assert (
        mount["target"]
        == compose_api["environment"]["MODEL_PATH"]
        == "/models/pipeline.skops"
    )
    assert mount["read_only"] is True
    assert any(
        m["type"] == "volume" and m["target"] == "/var/lib/king-county"
        for m in compose_api["volumes"]
    )


@pytest.mark.integration
@pytest.mark.docker
def test_named_volume_persists_for_non_root(image):
    """A fresh Docker volume is writable and survives a container replacement."""
    volume = "king-county-test-" + uuid4().hex
    mount = f"type=volume,source={volume},target=/var/lib/king-county"
    create = (
        "from api.houses import HouseRepository, HouseCreate; "
        "from pathlib import Path; "
        "r=HouseRepository(Path('/var/lib/king-county/houses.sqlite3')); "
        "r.initialize(); "
        "r.create(HouseCreate(bedrooms=3,bathrooms=1,sqft_living=100,grade=7,zipcode='98101'))"
    )
    read = (
        "from api.houses import HouseRepository; from pathlib import Path; "
        "print(HouseRepository(Path('/var/lib/king-county/houses.sqlite3')).get(1).zipcode)"
    )
    docker("volume", "create", volume)
    try:
        docker("run", "--rm", "--mount", mount, image, "python", "-c", create)
        result = docker("run", "--rm", "--mount", mount, image, "python", "-c", read)
        assert result.stdout.strip() == "98101"
    finally:
        docker("volume", "rm", volume)


@pytest.mark.integration
@pytest.mark.docker
def test_compose_does_not_create_missing_model(image, tmp_path, monkeypatch):
    """Test missing-file behaviour, not version-specific config serialization."""
    missing = tmp_path / "missing-model.skops"
    monkeypatch.setenv("MODEL_FILE", str(missing))
    override = tmp_path / "image-override.json"
    override.write_text(json.dumps({"services": {"api": {"image": image}}}))
    root = Path(__file__).resolve().parents[2]
    command = (
        "compose",
        "--env-file",
        os.devnull,
        "--project-name",
        "missing-model-test-" + uuid4().hex,
        "-f",
        str(root / "compose.yaml"),
        "-f",
        str(override),
    )
    try:
        with pytest.raises(subprocess.CalledProcessError) as failure:
            docker(*command, "create", "--no-build", "--pull", "never", "api")
        assert missing.name in failure.value.stdout + failure.value.stderr
        assert not missing.exists()
    finally:
        docker(*command, "down", "--remove-orphans")
