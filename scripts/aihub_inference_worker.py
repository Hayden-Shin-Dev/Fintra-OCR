"""Execute the official AI-Hub logistics detector and ViTSTR recognizer.

This worker is intentionally dependency-isolated.  It must be launched with a
Python environment containing the AI-Hub-compatible torch/MMCV/MMOCR stack.
"""

from __future__ import annotations

import argparse
import json
import math
import string
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _install_import_shims() -> None:
    """Avoid importing optional augmentation/detector extensions not in this path."""
    if "lanms" not in sys.modules:
        lanms = ModuleType("lanms")
        lanms.merge_quadrangle_n9 = lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("LANMS is not used by OCRMaskRCNN")
        )
        sys.modules["lanms"] = lanms
    if "wand" not in sys.modules:
        wand = ModuleType("wand")
        image = ModuleType("wand.image")
        api = ModuleType("wand.api")

        class Image:
            pass

        class DisabledLibrary:
            def __getattr__(self, name):
                raise RuntimeError("Wand/ImageMagick augmentation is disabled")

        image.Image = Image
        api.library = DisabledLibrary()
        wand.image = image
        wand.api = api
        sys.modules.update({"wand": wand, "wand.image": image, "wand.api": api})


def _domain_characters(dictionary: Path) -> str:
    lines = dictionary.read_text(encoding="utf-8").splitlines()
    metadata = next((line.split(":", 1)[1].lstrip() for line in lines if line.startswith("character:")), None)
    if metadata is not None:
        suffix = string.printable[:-6]
        if metadata.endswith(suffix):
            metadata = metadata[: -len(suffix)]
        return metadata
    return "".join(lines)


def _options(dictionary: Path, checkpoint: Path, batch_size: int) -> SimpleNamespace:
    option = SimpleNamespace(
        Transformation="None",
        FeatureExtraction="ResNet",
        SequenceModeling="None",
        Prediction="None",
        Transformer=True,
        TransformerModel="vitstr_small_patch16_224",
        imgH=224,
        imgW=224,
        input_channel=1,
        output_channel=512,
        hidden_size=256,
        num_fiducial=20,
        batch_max_length=25,
        PAD=False,
        rgb=False,
        sensitive=True,
        batch_size=batch_size,
        workers=0,
        eval=True,
        isrand_aug=False,
        issel_aug=False,
        issemantic_aug=False,
        islearning_aug=False,
        isrotation_aug=False,
        isscatter_aug=False,
        data_filtering_off=True,
        dict_path=str(dictionary),
        saved_model=str(checkpoint),
    )
    import eval_utils

    option.character = _domain_characters(dictionary) + string.printable[:-6]
    option.num_class = len(eval_utils.TokenLabelConverter(option).character)
    return option


def _axis_box(points):
    xs = [int(round(float(point[0]))) for point in points]
    ys = [int(round(float(point[1]))) for point in points]
    return (min(xs), max(xs), max(xs), min(xs)), (min(ys), min(ys), max(ys), max(ys))


def _recognize(crop_paths, polygons, source_root, checkpoint, dictionary, device, batch_size):
    import torch
    import torch.nn.functional as functional
    from dataset import AlignCollate, RawDataset
    from eval_utils import TokenLabelConverter
    from model import Model

    option = _options(dictionary, checkpoint, batch_size)
    converter = TokenLabelConverter(option)
    recognizer = torch.nn.DataParallel(Model(option)).to(device)
    recognizer.load_state_dict(torch.load(str(checkpoint), map_location=device))
    recognizer.eval()
    crop_root = Path(crop_paths[0]).parent
    dataset = RawDataset(root=str(crop_root), opt=option)
    loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=AlignCollate(imgH=option.imgH, imgW=option.imgW, keep_ratio_with_pad=option.PAD, opt=option),
        pin_memory=False,
    )
    by_index = {}
    with torch.no_grad():
        for tensors, image_paths in loader:
            images = tensors.to(device)
            count = images.size(0)
            length = torch.IntTensor([option.batch_max_length] * count).to(device)
            text = torch.LongTensor(count, option.batch_max_length + 1).fill_(0).to(device)
            logits = recognizer(images, text, is_train=False)
            _, indices = logits.max(2)
            decoded = converter.decode(indices[:, 1:], length)
            probabilities = functional.softmax(logits, dim=2).max(dim=2).values[:, 1:]
            for raw_text, token_probabilities, path in zip(decoded, probabilities, image_paths):
                eos = raw_text.find("[s]")
                text_value = raw_text if eos < 0 else raw_text[:eos]
                # The official text-file writer replaces commas to protect its
                # comma-separated polygon format. JSON has no such collision;
                # preserve the recognizer text for Fintra number parsing.
                text_value = text_value.strip("\n\t")
                token_count = len(text_value)
                if token_count:
                    confidence = math.exp(
                        float(torch.log(token_probabilities[:token_count].clamp_min(1e-12)).mean())
                    )
                else:
                    confidence = 0.0
                by_index[int(Path(path).stem) - 1] = (text_value, confidence)
    return [
        {"text": by_index[index][0], "bbox": polygon, "score": by_index[index][1]}
        for index, polygon in enumerate(polygons)
        if index in by_index
    ]


def run(args) -> None:
    import cv2
    import numpy as np
    import torch
    source_root = Path(args.source_root)
    baseline_root = source_root / "text_recognition_baseline"
    detection_root = baseline_root / "new_detection"
    sys.path.insert(0, str(baseline_root))
    sys.path.insert(0, str(detection_root))
    import torch._utils
    from itertools import accumulate

    torch._utils._accumulate = accumulate
    from mmcv import imread
    from mmocr.apis import init_detector, model_inference
    requested_device = args.device
    if requested_device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested but torch.cuda.is_available() is false")
    device = torch.device(requested_device)
    detector = init_detector(args.detector_config, args.detector_checkpoint, device=requested_device)
    result = model_inference(detector, args.image)
    boundaries = result.get("boundary_result", [])
    page = imread(args.image, flag="color")
    if page is None:
        raise RuntimeError(f"Unable to read image: {args.image}")

    polygons = []
    crops = []
    with tempfile.TemporaryDirectory(prefix="fintra-aihub-crops-") as crop_dir:
        crop_root = Path(crop_dir)
        for boundary in boundaries:
            if float(boundary[-1]) < args.score_threshold:
                continue
            polygon = [int(round(value)) for value in boundary[:8]]
            points = np.asarray(polygon, dtype=np.float32).reshape(4, 2)
            x_min, y_min = points.min(axis=0).astype(int)
            x_max, y_max = points.max(axis=0).astype(int)
            crop = page[max(0, y_min) : min(page.shape[0], int(y_max + 1.25)), max(0, x_min) : min(page.shape[1], int(x_max + 1.25))]
            if crop.size == 0:
                continue
            crop_path = crop_root / f"{len(crops) + 1:09d}.png"
            if not cv2.imwrite(str(crop_path), crop):
                raise RuntimeError(f"Unable to write crop: {crop_path}")
            polygons.append(polygon)
            crops.append(str(crop_path))
        predictions = _recognize(
            crops,
            polygons,
            source_root,
            Path(args.recognizer_checkpoint),
            Path(args.dictionary),
            device,
            args.batch_size,
        ) if crops else []

    payload = {
        "backend": "aihub-logistics",
        "detector_boundary_count": len(boundaries),
        "predictions": predictions,
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--detector-config", required=True)
    parser.add_argument("--detector-checkpoint", required=True)
    parser.add_argument("--recognizer-checkpoint", required=True)
    parser.add_argument("--dictionary", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--score-threshold", type=float, default=0.2)
    parser.add_argument("--batch-size", type=int, default=32)
    run(parser.parse_args())


if __name__ == "__main__":
    _install_import_shims()
    main()
