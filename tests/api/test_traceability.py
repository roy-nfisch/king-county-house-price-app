"""Trace metadata, correlation, privacy, and HTTP failure paths."""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import ApiSettings
from api.traceability import PredictionTrace, PredictionTraceMiddleware
from king_county.artifacts import MODEL_VERSION
from king_county.prediction import PredictionError, PredictionService


@pytest.fixture
def traced_client(approved_artifact, caplog):
    """Capture trace INFO records while exercising the real app and tiny model."""
    caplog.set_level(logging.INFO, logger="api.traceability")
    with TestClient(
        create_app(ApiSettings(model_path=approved_artifact.path))
    ) as client:
        yield client


def traces(caplog):
    """Return parsed prediction records, excluding unrelated library logs."""
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "api.traceability"
    ]


def test_trace_uses_monotonic_elapsed_time(caplog):
    """Wall-clock changes cannot affect elapsed duration."""
    caplog.set_level(logging.INFO, logger="api.traceability")
    with patch("api.traceability.perf_counter", side_effect=[10.0, 10.125]):
        PredictionTrace("test-model").finish(200)
    assert traces(caplog)[0]["duration_ms"] == 125.0


@pytest.fixture
def successful_trace(traced_client, house_payload, caplog):
    """Return one success record and response for independent field checks."""
    response = traced_client.post(
        "/predict", json=house_payload, headers={"X-Request-ID": "untrusted-input"}
    )
    records = traces(caplog)
    assert len(records) == 1
    return records[0], response


def test_trace_contains_only_operational_metadata(successful_trace):
    """Do not include house fields or predicted prices."""
    record, _ = successful_trace
    assert set(record) == {
        "request_id",
        "timestamp",
        "model_version",
        "outcome",
        "status_code",
        "duration_ms",
    }


@pytest.mark.parametrize(
    "field,expected",
    [("model_version", MODEL_VERSION), ("outcome", "success"), ("status_code", 200)],
)
def test_success_trace_field(successful_trace, field, expected):
    """Report unrelated metadata failures as separate test cases."""
    record, _ = successful_trace
    assert record[field] == expected


def test_response_id_matches_generated_trace_id(successful_trace):
    """A server UUID replaces, rather than trusts, an incoming request ID."""
    record, response = successful_trace
    assert str(UUID(record["request_id"])) == response.headers["X-Request-ID"]
    assert record["request_id"] != "untrusted-input"


def test_trace_timestamp_is_explicitly_utc(successful_trace):
    """The structured timestamp must not depend on the host's timezone."""
    record, _ = successful_trace
    assert datetime.fromisoformat(record["timestamp"]).utcoffset() == timedelta(0)


def test_trace_duration_is_nonnegative(successful_trace):
    """A completed request has a nonnegative duration in milliseconds."""
    record, _ = successful_trace
    assert record["duration_ms"] >= 0


@pytest.mark.parametrize("body", ["{}", '{"bedrooms":1,"bedrooms":2}', "{"])
def test_rejected_requests_are_traced_before_prediction(traced_client, caplog, body):
    """Validation failures retain a correlation ID and do not call the model."""
    with patch.object(PredictionService, "predict") as predict:
        response = traced_client.post(
            "/predict", content=body, headers={"Content-Type": "application/json"}
        )
    predict.assert_not_called()
    assert response.status_code == 422
    assert traces(caplog)[0]["outcome"] == "rejected"
    assert traces(caplog)[0]["request_id"] == response.headers["X-Request-ID"]


def test_controlled_prediction_failure_is_traced(traced_client, house_payload, caplog):
    """A handled model failure gets one failed trace and an HTTP correlation ID."""
    with patch.object(
        PredictionService, "predict", side_effect=PredictionError("failed")
    ):
        response = traced_client.post("/predict", json=house_payload)
    assert response.status_code == 500
    assert len(traces(caplog)) == 1
    assert traces(caplog)[0]["outcome"] == "failed"
    assert traces(caplog)[0]["request_id"] == response.headers["X-Request-ID"]


def test_unexpected_failure_is_logged_and_not_hidden(
    traced_client, house_payload, caplog
):
    """Do not swallow programming errors or put exception details in trace logs."""
    with (
        patch.object(PredictionService, "predict", side_effect=RuntimeError("private")),
        pytest.raises(RuntimeError, match="private"),
    ):
        traced_client.post("/predict", json=house_payload)
    assert len(traces(caplog)) == 1
    assert traces(caplog)[0]["outcome"] == "failed"
    assert "private" not in json.dumps(traces(caplog))


@pytest.mark.parametrize("path", ["/health", "/docs", "/openapi.json"])
def test_non_prediction_requests_do_not_create_traces(traced_client, caplog, path):
    """Readiness checks and documentation must not flood prediction logs."""
    response = traced_client.get(path)
    assert traces(caplog) == []
    assert "X-Request-ID" not in response.headers


def test_concurrent_predictions_keep_separate_request_ids(
    traced_client, house_payload, caplog
):
    """Per-request objects prevent shared IDs or timings between concurrent calls."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: traced_client.post("/predict", json=house_payload), range(2)
            )
        )
    ids = {response.headers["X-Request-ID"] for response in responses}
    assert len(ids) == 2
    assert {record["request_id"] for record in traces(caplog)} == ids


@pytest.mark.parametrize("error", [asyncio.CancelledError, RuntimeError])
@pytest.mark.parametrize("headers_started", [False, True])
def test_interrupted_requests_never_log_success(caplog, error, headers_started):
    """Propagate interruptions and preserve the status actually started, if any."""
    caplog.set_level(logging.INFO, logger="api.traceability")

    async def interrupted_app(scope, receive, send):
        if headers_started:
            await send({"type": "http.response.start", "status": 200, "headers": []})
        raise error("interrupted")

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        pass

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/predict",
        "app": SimpleNamespace(
            state=SimpleNamespace(
                prediction_service=SimpleNamespace(model_version="test")
            )
        ),
    }
    with pytest.raises(error, match="interrupted"):
        asyncio.run(PredictionTraceMiddleware(interrupted_app)(scope, receive, send))
    records = traces(caplog)
    assert len(records) == 1
    assert records[0]["outcome"] == "failed"
    assert records[0]["status_code"] == (200 if headers_started else None)


@pytest.mark.parametrize(
    "root_path,path",
    [
        ("/houses", "/houses/predict"),
        ("/houses", "/predict"),
        ("/api/houses", "/api/houses/predict"),
    ],
)
def test_prefixed_predictions_are_traced(
    approved_artifact, house_payload, caplog, root_path, path
):
    """Trace the same route with proxy prefixes present or already stripped."""
    caplog.set_level(logging.INFO, logger="api.traceability")
    app = create_app(ApiSettings(model_path=approved_artifact.path))
    with TestClient(app, root_path=root_path) as client:
        response = client.post(path, json=house_payload)
    assert response.status_code == 200
    records = traces(caplog)
    assert len(records) == 1
    assert records[0]["request_id"] == response.headers["X-Request-ID"]
    assert records[0]["outcome"] == "success"
