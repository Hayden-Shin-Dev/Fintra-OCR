import os
import shutil
import torch
import string
import numpy as np
import os.path as osp
import mmcv
import cv2
import ujson
import tqdm
from collections import defaultdict
import tempfile
import uuid
from shapely import geometry
from model_inference import prediction
from eval_utils import TokenLabelConverter, get_args
from model import Model
import pyclipper
import psutil


def crop_img(bbox_4_point, img, scale_factor = 1.25):
    polygon = np.array(bbox_4_point)
    polygon = geometry.Polygon(polygon.reshape(4, 2))
    try:
        x_min, y_min, x_max, y_max = list(map(int, polygon.bounds))
    except:
        print(x_min, y_min, x_max, y_max)
    # print(x_min, y_min, x_max, y_max)
    return img[y_min:int(y_max+scale_factor), x_min:int(x_max+scale_factor), :]


def model_load(opt, device):    
    # initialization charecter encode
    # file_name = "/workspace/unidocs_dict_latest.txt"
    # file_name = "/workspace/dict/unidocs_dict_transit.txt"
    with open(opt.dict_path, encoding="utf-8") as fd:
        character = [char.strip("\n") for char in fd.readlines()]
    opt.character = "".join(sorted(character)) + string.printable[:-6]
    converter = TokenLabelConverter(opt)
    opt.num_class = len(converter.character)
    # opt.num_class = 1144
    # initialization model
    model = Model(opt)
    model = torch.nn.DataParallel(model).to(device)
    # loaded pre-trained model
    model.load_state_dict(torch.load(opt.saved_model, map_location=device))

    return model


# CPU execution-only change from the original @ray.remote(num_gpus=1) worker.
def inference_multi_fn(opt, json_dump, annotation_result, output_path):
    device = torch.device('cpu')
    score_thr = 0.2
    print('DEVICE: cpu')

    model = model_load(opt, device)
    for idx in tqdm.tqdm(json_dump, total=len(json_dump)):
        with tempfile.TemporaryDirectory() as temp_file_name:
            annotation_bucket = defaultdict(list)
            image_id, image_name = idx.get('id'), idx.get('file_name')
            image_path = osp.join(opt.image_root_path, image_name)
            annotations = annotation_result[int(image_id)].get('boundary_result')
            image_seq = 1
            img = cv2.imread(image_path)
            # per images annotation
            for annotation in annotations:
                if annotation[-1] > score_thr:
                    # NOTE: key: image unique key, value annotation information
                    polygon = list(map(int, annotation[:8]))
                    new_img= crop_img(polygon, img)
                    crop_h, crop_w, _ = new_img.shape
                    if crop_h * crop_w != 0:
                        image_unique_key = f"{image_seq:09d}.png"
                        img_save_name = osp.join(temp_file_name, image_unique_key)
                        # print(temp_file_name)
                        cv2.imwrite(img_save_name, new_img)
                        annotation_bucket[image_name].append(list(map(int, polygon)))
                    
                        image_seq += 1
            # if annotation_bucket == {}:
                # print(annotation_bucket)
            # model, opt, dict_recognition=None, image_folder="temp", device=None
            if annotation_bucket == {}:
                pass
            else:
                prediction_result = prediction(model, opt, annotation_bucket, image_folder=temp_file_name, output_path=output_path, device=device)
    
    
def main():
    # One-document CPU reference execution-only change: no Ray initialization,
    # no GPU resource request, and direct sequential invocation.
    opt = get_args(is_train=False)
    # print(opt)
    # opt.FeatureExtraction = "ResNet"
    
    json_path = opt.json_path
    output_path = osp.splitext(osp.basename(json_path))[0]
    with open(json_path, mode='r', encoding='utf8') as fr:
        json_dump = ujson.load(fr)
        
    if osp.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path, exist_ok=True)
    
    annotation_result = mmcv.load(opt.result_pkl)
    print(f'final prediction path: {output_path}')
    inference_multi_fn(opt, json_dump['images'], annotation_result, output_path)
    
    
if __name__ == '__main__':
    main()
