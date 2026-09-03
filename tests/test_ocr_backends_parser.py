import numpy as np

from fintra_ocr.ocr_backends import parse_paddle_output


def test_parse_paddle_mapping_with_boxes():
    result = {
        "rec_texts": ["ABC", "123"],
        "rec_scores": [0.9, 0.8],
        "rec_boxes": [[1, 2, 20, 10], [30, 2, 50, 10]],
    }
    predictions = parse_paddle_output(result)
    assert [p.text for p in predictions] == ["ABC", "123"]
    assert predictions[0].x == (1, 20, 20, 1)


def test_parse_paddle_mapping_with_polygons():
    result = {
        "rec_texts": ["ABC"],
        "rec_scores": [0.9],
        "rec_polys": [[[1, 2], [20, 2], [20, 10], [1, 10]]],
    }
    predictions = parse_paddle_output(result)
    assert predictions[0].y == (2, 2, 10, 10)


def test_parse_paddle_37_numpy_arrays():
    """PaddleOCR/PaddleX 3.7 returns ndarray scores and boxes."""
    result = {
        "rec_texts": ["Invoice No.", "311992"],
        "rec_scores": np.array([0.987, 0.976], dtype=np.float32),
        "rec_boxes": np.array([[10, 20, 90, 40], [100, 20, 170, 40]], dtype=np.int16),
    }
    predictions = parse_paddle_output(result)
    assert [p.text for p in predictions] == ["Invoice No.", "311992"]
    assert predictions[1].x == (100, 170, 170, 100)
    assert abs(predictions[0].score - 0.987) < 1e-5


def test_parse_paddle_json_res_wrapper_with_numpy_arrays():
    result = {
        "res": {
            "input_path": None,
            "rec_texts": ["TOTAL", "$1,216.98"],
            "rec_scores": np.array([0.99, 0.95]),
            "rec_boxes": np.array([[1, 2, 20, 10], [30, 2, 80, 10]], dtype=np.int16),
        }
    }
    predictions = parse_paddle_output(result)
    assert [p.text for p in predictions] == ["TOTAL", "$1,216.98"]


def test_parse_paddle_object_json_property():
    class FakePaddleResult:
        @property
        def json(self):
            return {
                "res": {
                    "rec_texts": ["B/L No.", "HG290309"],
                    "rec_scores": np.array([0.98, 0.97]),
                    "rec_boxes": np.array([[1, 2, 20, 10], [30, 2, 80, 10]], dtype=np.int16),
                }
            }

    predictions = parse_paddle_output(FakePaddleResult())
    assert [p.text for p in predictions] == ["B/L No.", "HG290309"]
