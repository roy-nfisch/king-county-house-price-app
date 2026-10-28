"""Artifact integrity and fail-closed loading, without a production model."""

import hashlib
import json
from unittest.mock import patch

import pytest
import skops.io as sio
from sklearn.dummy import DummyRegressor

from king_county.artifacts import ModelArtifact, ModelLoadError


def test_approved_model_loads_as_a_complete_pipeline(approved_artifact):
    """The verified model includes preprocessing and its fitted reference state."""
    assert list(approved_artifact.load().named_steps) == [
        "cleaning",
        "features",
        "polynomial",
        "scaler",
        "model",
    ]


def test_missing_artifact_fails_clearly(tmp_path):
    """No model must mean failed startup, not invented predictions."""
    with pytest.raises(ModelLoadError, match="missing or unreadable"):
        ModelArtifact(tmp_path / "missing.skops").load()


@pytest.mark.parametrize(
    "damage", ["empty", "changed", "junk", "truncated", "altered", "other-model"]
)
def test_changed_bytes_are_rejected_before_deserialization(approved_artifact, damage):
    """Neither type inspection nor the loader sees unapproved model bytes."""
    data = approved_artifact.path.read_bytes()
    replacements = {
        "empty": b"",
        "changed": b"changed",
        "junk": b"not a model",
        "truncated": data[: len(data) // 2],
        "altered": bytes([data[0] ^ 1]) + data[1:],
        "other-model": sio.dumps(DummyRegressor().fit([[0]], [100.0])),
    }
    approved_artifact.path.write_bytes(replacements[damage])
    with (
        patch("king_county.artifacts.sio.get_untrusted_types") as inspect_types,
        patch("king_county.artifacts.sio.loads") as loads,
        pytest.raises(ModelLoadError, match="checksum mismatch"),
    ):
        approved_artifact.load()
    inspect_types.assert_not_called()
    loads.assert_not_called()


def test_loader_uses_the_same_verified_bytes(approved_artifact):
    """The path is read only once; deserialization gets exactly those bytes."""
    data = approved_artifact.path.read_bytes()
    with (
        patch("king_county.artifacts.Path.read_bytes", return_value=data) as read,
        patch("king_county.artifacts.sio.loads", wraps=sio.loads) as load,
    ):
        approved_artifact.load()
    read.assert_called_once_with()
    assert load.call_args.args[0] == data


def test_unapproved_custom_type_is_never_automatically_trusted(approved_artifact):
    """The loader's discovered types cannot expand the code-defined allowlist."""
    with (
        patch(
            "king_county.artifacts.sio.get_untrusted_types", return_value=["other.Type"]
        ),
        patch("king_county.artifacts.sio.loads") as loads,
        pytest.raises(ModelLoadError, match="unapproved custom types"),
    ):
        approved_artifact.load()
    loads.assert_not_called()


def test_incompatible_model_fails_clearly(approved_artifact):
    """An environment/serialization failure cannot leave an apparently ready API."""
    with (
        patch(
            "king_county.artifacts.sio.loads", side_effect=ValueError("incompatible")
        ),
        pytest.raises(ModelLoadError, match="incompatible"),
    ):
        approved_artifact.load()


def test_sidecar_cannot_approve_changed_model_bytes(approved_artifact):
    """A colocated checksum is not allowed to replace the trusted code pin."""
    approved_artifact.path.write_bytes(b"changed")
    approved_artifact.path.with_name("metadata.json").write_text(
        json.dumps({"model_sha256": hashlib.sha256(b"changed").hexdigest()})
    )
    with pytest.raises(ModelLoadError, match="checksum mismatch"):
        approved_artifact.load()


def test_wrong_pipeline_shape_fails_clearly(approved_artifact):
    """A verified load still needs the expected complete pipeline contract."""
    with (
        patch("king_county.artifacts.sio.loads", return_value=object()),
        pytest.raises(ModelLoadError, match="complete prediction pipeline"),
    ):
        approved_artifact.load()
