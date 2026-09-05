"""Modern-device Recognition runner for the AI-Hub reference model.

This file is intentionally separate from the source in the original Docker
image.  The model class, checkpoint, character construction, crop geometry,
image resize, tensor conversion, sequence length and greedy decoder are kept
equivalent to the original recognition path.  Only runtime/device ownership
is changed: one explicit device and a normal sequential DataLoader.
"""

from __future__ import annotations

import argparse
import json
import re
import string
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from shapely import geometry


VENDOR = Path(__file__).resolve().parent / "vendor" / "original_recognition"
sys.path.insert(0, str(VENDOR))

from eval_utils import TokenLabelConverter  # noqa: E402
from model import Model  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--baseline-txt", type=Path)
    source.add_argument("--regions-json", type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--dict", dest="dictionary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--batch-size", type=int, default=768)
    return parser.parse_args()


def read_regions(path):
    regions = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split(",", 8)
        if len(fields) != 9:
            raise ValueError("{}:{} is not official 8-coordinate TXT".format(path, line_number))
        polygon = [int(float(value)) for value in fields[:8]]
        regions.append(polygon)
    return regions


def read_detection_regions(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    regions = []
    for candidate in payload["candidates"]:
        # Original detection_model.py applies map(int) before cropping.
        regions.append([int(float(value)) for value in candidate["boundary"]])
    return regions


def crop_img(bbox_4_point, image, scale_factor=1.25):
    polygon = np.array(bbox_4_point)
    bounds = geometry.Polygon(polygon.reshape(4, 2)).bounds
    x_min, y_min, x_max, y_max = list(map(int, bounds))
    return image[y_min:int(y_max + scale_factor), x_min:int(x_max + scale_factor), :]


def make_opt(dictionary_path, batch_size):
    character = [line.rstrip("\n") for line in dictionary_path.read_text(encoding="utf-8").splitlines()]
    final_character = "".join(sorted(character)) + string.printable[:-6]
    opt = SimpleNamespace(
        dict_path=str(dictionary_path),
        character=final_character,
        batch_max_length=25,
        sensitive=True,
        PAD=False,
        imgH=224,
        imgW=224,
        rgb=False,
        workers=0,
        batch_size=batch_size,
        Transformer=True,
        TransformerModel="vitstr_small_patch16_224",
        # The original argparse value is the string "None".  The original
        # Model.forward checks this string before calling self.Transformation.
        Transformation="None",
        FeatureExtraction="ResNet",
        SequenceModeling=None,
        Prediction=None,
        num_fiducial=20,
        input_channel=1,
        output_channel=512,
        hidden_size=256,
        eval=True,
    )
    converter = TokenLabelConverter(opt)
    opt.num_class = len(converter.character)
    if opt.num_class != 370:
        raise RuntimeError("runtime character construction produced num_class={}".format(opt.num_class))
    return opt, converter


def load_model(checkpoint_path, opt, device):
    model = torch.nn.DataParallel(Model(opt)).to(device)
    try:
        state = torch.load(str(checkpoint_path), map_location=device, weights_only=False)
    except TypeError:  # compatibility with torch versions without weights_only
        state = torch.load(str(checkpoint_path), map_location=device)
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def tensor_from_crop(crop):
    # Exact evaluation branch of the original DataAugment: grayscale PIL,
    # BICUBIC resize to 224x224, ToTensor, with no [-1, 1] scaling for ViTSTR.
    image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)).convert("L")
    image = image.resize((224, 224), Image.Resampling.BICUBIC)
    array = np.asarray(image, dtype=np.float32) / 255.0
    return torch.from_numpy(array).unsqueeze(0)


def run(args):
    device = torch.device(args.device)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in the Modern runtime")
    if args.device == "cuda":
        print("CUDA_DEVICE={}".format(torch.cuda.get_device_name(0)))
        capability = torch.cuda.get_device_capability(0)
        print("CUDA_CAPABILITY={}.{}".format(*capability))
        if capability != (8, 9):
            raise RuntimeError("Expected RTX4050 sm_89, got sm_{}{}".format(*capability))

    region_source = args.baseline_txt or args.regions_json
    regions = read_regions(args.baseline_txt) if args.baseline_txt else read_detection_regions(args.regions_json)
    image = cv2.imread(str(args.image))
    if image is None:
        raise FileNotFoundError(str(args.image))
    opt, converter = make_opt(args.dictionary, args.batch_size)
    model = load_model(args.checkpoint, opt, device)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.output_dir / (args.image.stem + ".txt")
    structured_path = args.output_dir / (args.image.stem + ".json")
    records = []
    exceptions = []
    with tempfile.TemporaryDirectory(prefix="fintra-modern-recognition-"):
        tensors = []
        valid_regions = []
        for index, polygon in enumerate(regions, 1):
            try:
                crop = crop_img(polygon, image)
                if crop.size == 0:
                    continue
                tensors.append(tensor_from_crop(crop))
                valid_regions.append(polygon)
            except Exception as exc:  # keep per-region evidence in the artifact
                exceptions.append({"region_index": index, "error": repr(exc)})

        with raw_path.open("w", encoding="utf-8") as raw:
            with torch.no_grad():
                for start in range(0, len(tensors), args.batch_size):
                    batch = torch.stack(tensors[start:start + args.batch_size]).to(device)
                    batch_size = batch.size(0)
                    length_for_pred = torch.IntTensor([opt.batch_max_length] * batch_size).to(device)
                    text_for_pred = torch.LongTensor(batch_size, opt.batch_max_length + 1).fill_(0).to(device)
                    preds = model(batch, text_for_pred, is_train=False)
                    _, preds_index = preds.max(2)
                    preds_str = converter.decode(preds_index[:, 1:], length_for_pred)
                    # Keep the reference probability computation executed, but
                    # do not invent a confidence field absent from official TXT.
                    F.softmax(preds, dim=2).max(dim=2)
                    for polygon, prediction in zip(valid_regions[start:start + args.batch_size], preds_str):
                        eos = prediction.find("[s]")
                        text = re.sub(",", "쉼표", prediction[:eos].strip("\n").strip("\t"))
                        raw.write(",".join(map(str, polygon)) + "," + text + "\n")
                        records.append({"bbox": polygon, "text": text})

    structured = {
        "image_id": args.image.name,
        "regions": records,
        "metadata": {
            "runtime": "modern_gpu",
            "model_source": "AI-Hub original weights/code",
            "device": str(device),
            "checkpoint": str(args.checkpoint),
            "dictionary": str(args.dictionary),
            "region_source": str(region_source),
            "num_class": opt.num_class,
            "input_regions": len(regions),
            "output_regions": len(records),
            "exceptions": exceptions,
            "empty_text_count": sum(1 for record in records if not record["text"]),
        },
    }
    structured_path.write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CHECKPOINT_LOAD=PASS")
    print("DETECTION_REGIONS={}".format(len(regions)))
    print("RECOGNITION_REGIONS={}".format(len(records)))
    print("RAW_OUTPUT={}".format(raw_path))
    print("STRUCTURED_OUTPUT={}".format(structured_path))
    print("EXCEPTIONS={}".format(len(exceptions)))
    print("EMPTY_TEXT={}".format(structured["metadata"]["empty_text_count"]))


if __name__ == "__main__":
    run(parse_args())
