import json
import sys

import pytest

from fintra_ocr.aihub_backend import (
    AIHubModelPaths,
    AIHubOCRBackend,
    AIHubRuntimeError,
    _classify_failure,
)


def _model_paths(tmp_path, worker):
    source = tmp_path / "source"
    (source / "configs").mkdir(parents=True)
    (source / "text_recognition_baseline" / "new_detection").mkdir(parents=True)
    for path in (
        source / "configs" / "transit_config.py",
        source / "transit_detection_model.pth",
        source / "transit_recog_model.pth",
        source / "transit_dict.txt",
    ):
        path.write_text("placeholder", encoding="utf-8")
    return AIHubModelPaths(
        source_root=source,
        dictionary=source / "transit_dict.txt",
        detector_config=source / "configs" / "transit_config.py",
        detector_checkpoint=source / "transit_detection_model.pth",
        recognizer_checkpoint=source / "transit_recog_model.pth",
        runtime_python=sys.executable,
        worker=worker,
    )


def test_aihub_worker_protocol_returns_common_predictions(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import argparse, json\n"
        "p=argparse.ArgumentParser(); p.add_argument('--output'); a,_=p.parse_known_args()\n"
        "json.dump({'predictions':[{'text':'INV-1','bbox':[[1,2],[9,2],[9,8],[1,8]],'score':0.91}]}, open(a.output, 'w'))\n",
        encoding="utf-8",
    )
    # The tiny fake worker is protocol-only test infrastructure; no model result
    # is used as an AI-Hub evaluation result.
    model = _model_paths(tmp_path, worker)
    predictions = AIHubOCRBackend(model).predict_bytes(b"image-bytes")
    assert predictions[0].text == "INV-1"
    assert predictions[0].x == (1, 9, 9, 1)
    assert predictions[0].score == pytest.approx(0.91)


def test_aihub_model_paths_report_missing_assets(tmp_path):
    model = AIHubModelPaths(source_root=tmp_path, dictionary=tmp_path / "missing.txt")
    with pytest.raises(AIHubRuntimeError) as error:
        model.validate()
    assert error.value.category == "missing_model_asset"


def test_aihub_failure_categories_are_explicit():
    assert _classify_failure("ModuleNotFoundError: No module named 'mmcv'") == "missing_dependency"
    assert _classify_failure("CUDA_HOME environment variable is not set") == "cuda_compatibility"
    assert _classify_failure("size mismatch for backbone.layer") == "checkpoint_incompatibility"
