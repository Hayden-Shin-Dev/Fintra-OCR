from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch


def shape(state: dict, key: str) -> list[int] | None:
    value = state.get(key)
    return list(value.shape) if value is not None else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    args = parser.parse_args()
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    state = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else {}
    checks = {
        "top_level_state_dict": isinstance(checkpoint, dict) and "state_dict" in checkpoint,
        "backbone_present": any(key.startswith("backbone.") for key in state),
        "neck_present": any(key.startswith("neck.") for key in state),
        "rpn_present": any(key.startswith("rpn_head.") for key in state),
        "roi_head_present": any(key.startswith("roi_head.") for key in state),
        "rpn_cls_shape": shape(state, "rpn_head.rpn_cls.weight") == [5, 256, 1, 1],
        "rpn_reg_shape": shape(state, "rpn_head.rpn_reg.weight") == [20, 256, 1, 1],
        "bbox_cls_shape": shape(state, "roi_head.bbox_head.fc_cls.weight") == [2, 1024],
        "bbox_reg_shape": shape(state, "roi_head.bbox_head.fc_reg.weight") == [4, 1024],
        "bbox_fc1_shape": shape(state, "roi_head.bbox_head.shared_fcs.0.weight") == [1024, 12544],
        "bbox_fc2_shape": shape(state, "roi_head.bbox_head.shared_fcs.1.weight") == [1024, 1024],
        "mask_logits_shape": shape(state, "roi_head.mask_head.conv_logits.weight") == [1, 256, 1, 1],
        "mask_upsample_shape": shape(state, "roi_head.mask_head.upsample.weight") == [256, 256, 2, 2],
    }
    details = {
        "checkpoint": str(args.checkpoint),
        "top_level_keys": sorted(checkpoint.keys()) if isinstance(checkpoint, dict) else [],
        "state_dict_keys": len(state),
        "selected_shapes": {
            key: shape(state, key)
            for key in (
                "rpn_head.rpn_cls.weight",
                "rpn_head.rpn_reg.weight",
                "roi_head.bbox_head.fc_cls.weight",
                "roi_head.bbox_head.fc_reg.weight",
                "roi_head.bbox_head.shared_fcs.0.weight",
                "roi_head.bbox_head.shared_fcs.1.weight",
                "roi_head.mask_head.conv_logits.weight",
                "roi_head.mask_head.upsample.weight",
            )
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }
    print(json.dumps(details, indent=2))
    if not details["all_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
