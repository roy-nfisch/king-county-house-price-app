"""Load only the reviewed model bytes, never an uploaded or self-approved file."""

import hashlib
from pathlib import Path

import skops.io as sio
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from king_county.features import HouseFeatureEngineer

MODEL_VERSION = "king-county-20261028T153712021211Z"
EXPECTED_MODEL_SHA256 = (
    "607d24aa27c464e5dda0aae260f050e9104f5377623e22ae7cdce98793383025"
)
DEFAULT_MODEL_PATH = Path("model/refactored") / MODEL_VERSION / "pipeline.skops"
TRUSTED_MODEL_TYPES = (
    "king_county.cleaning.HouseCleaner",
    "king_county.features.HouseFeatureEngineer",
)


class ModelLoadError(RuntimeError):
    """Fail startup when an approved, compatible model is unavailable."""


class ModelArtifact:
    """Read, verify, and load the configured artifact without reading metadata.

    The expected digest and model version are code-reviewed constants, not
    environment overrides. A path can relocate the same approved artifact.
    """

    def __init__(self, path: Path) -> None:
        """Store the local artifact path; do not read or load it yet."""
        self.path = path

    def load(self) -> Pipeline:
        """Return the verified fitted pipeline, or raise ModelLoadError.

        Read once and load the same bytes, avoiding a path change between the
        checksum check and deserialization. Never infer trust from a sidecar.
        """
        try:
            data = self.path.read_bytes()
        except OSError as exc:
            raise ModelLoadError(
                "Approved model file is missing or unreadable."
            ) from exc
        if hashlib.sha256(data).hexdigest() != EXPECTED_MODEL_SHA256:
            raise ModelLoadError("Model checksum mismatch; loading was blocked.")
        try:
            unexpected = set(sio.get_untrusted_types(data=data)) - set(
                TRUSTED_MODEL_TYPES
            )
            if unexpected:
                raise ModelLoadError("Model contains unapproved custom types.")
            pipeline = sio.loads(data, trusted=list(TRUSTED_MODEL_TYPES))
            self._validate_pipeline(pipeline)
        except ModelLoadError:
            raise
        except Exception as exc:
            raise ModelLoadError(
                "Approved model is incompatible or cannot be loaded."
            ) from exc
        return pipeline

    @staticmethod
    def _validate_pipeline(pipeline: Pipeline) -> None:
        """Require the fitted complete pipeline and canonical feature contract."""
        expected = ["cleaning", "features", "polynomial", "scaler", "model"]
        if not isinstance(pipeline, Pipeline) or list(pipeline.named_steps) != expected:
            raise ModelLoadError("Model must contain the complete prediction pipeline.")
        check_is_fitted(pipeline.named_steps["model"])
        features = pipeline.named_steps["features"]
        if list(features.get_feature_names_out()) != list(
            HouseFeatureEngineer.FEATURE_NAMES
        ):
            raise ModelLoadError(
                "Model feature order does not match the input contract."
            )
