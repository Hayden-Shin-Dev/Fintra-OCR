"""Modern Detection runner using the original model graph/config values.

The output conversion follows the inspected AI-Hub OCRMaskRCNN path:
instance mask -> foreground points -> cv2.minAreaRect -> boxPoints, with the
original score threshold applied by the OCR wrapper at 0.2.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from mmengine.config import Config
from mmdet.apis import inference_detector
from mmdet.registry import MODELS
from mmdet.utils import register_all_modules


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--score-threshold", type=float, default=0.2)
    return parser.parse_args()


def mask_to_boundary(mask, score):
    points_y, points_x = np.where(mask)
    if len(points_x) == 0:
        return None
    points = np.column_stack((points_x, points_y)).astype(np.float32)
    rectangle = cv2.minAreaRect(points)
    vertices = cv2.boxPoints(rectangle)
    if min(rectangle[1]) <= -1:
        return None
    return {"boundary": vertices.flatten().tolist(), "score": float(score)}


def load_model(config_path, checkpoint_path, device):
    cfg = Config.fromfile(str(config_path))
    model = MODELS.build(cfg.model)
    state = torch.load(str(checkpoint_path), map_location="cpu", weights_only=False)
    state = state["state_dict"] if isinstance(state, dict) and "state_dict" in state else state
    model.load_state_dict(state, strict=True)
    model.cfg = cfg
    model.to(device)
    model.eval()
    return model, cfg


def main():
    parsed = args()
    register_all_modules(init_default_scope=True)
    device = torch.device(parsed.device)
    if parsed.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available")
        capability = torch.cuda.get_device_capability(0)
        print("CUDA_DEVICE=" + torch.cuda.get_device_name(0))
        print("CUDA_CAPABILITY={}.{}".format(*capability))
        if capability != (8, 9):
            raise RuntimeError("Expected RTX4050 sm_89")

    model, _ = load_model(parsed.config, parsed.checkpoint, device)
    result = inference_detector(model, str(parsed.image))
    instances = result.pred_instances
    boxes = instances.bboxes.detach().cpu().numpy()
    scores = instances.scores.detach().cpu().numpy()
    masks = instances.masks.detach().cpu().numpy() if hasattr(instances, "masks") else None
    all_candidates = []
    candidates = []
    for index, score in enumerate(scores):
        boundary = mask_to_boundary(masks[index], score) if masks is not None else None
        if boundary is None:
            continue
        boundary["bbox"] = boxes[index].tolist()
        all_candidates.append(boundary)
        if float(score) > parsed.score_threshold:
            candidates.append(boundary)

    payload = {
        "image_id": parsed.image.name,
        "score_threshold": parsed.score_threshold,
        "raw_candidate_count": len(all_candidates),
        "score_threshold_candidate_count": len(candidates),
        "candidates": candidates,
        "metadata": {
            "runtime": "modern_gpu",
            "model_source": "AI-Hub original detection checkpoint",
            "checkpoint_load": "PASS",
            "device": str(device),
            "bbox_output_count": int(len(boxes)),
        },
    }
    parsed.output.parent.mkdir(parents=True, exist_ok=True)
    parsed.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CHECKPOINT_LOAD=PASS")
    print("RAW_CANDIDATES={}".format(len(all_candidates)))
    print("SCORE_GT_0_2={}".format(len(candidates)))
    print("OUTPUT={}".format(parsed.output))


if __name__ == "__main__":
    main()
