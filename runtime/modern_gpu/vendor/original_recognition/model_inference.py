import cv2
import re
import torch
import torch.utils.data
import torch.nn.functional as F
import os.path as osp

from eval_utils import TokenLabelConverter
from dataset import AlignCollate, RawDataset


def prediction(model, opt, dict_recognition=None, image_folder="temp", output_path=None, device=None):

    opt.image_folder = image_folder
    # print(dict_recognition)
    img_unique_key = list(dict_recognition.keys())[0]
    converter = TokenLabelConverter(opt)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    opt.eval = True
    AlignCollate_demo = AlignCollate(
        imgH=opt.imgH, imgW=opt.imgW, keep_ratio_with_pad=opt.PAD, opt=opt
    )
    demo_data = RawDataset(root=opt.image_folder, opt=opt)
    demo_loader = torch.utils.data.DataLoader(
        demo_data,
        batch_size=opt.batch_size,
        shuffle=False,
        num_workers=int(opt.workers),
        collate_fn=AlignCollate_demo,
        pin_memory=True,
    )
    # prediction
    model.eval()
    output_annotation_path = osp.join(output_path, f"{img_unique_key.split('.')[0]}.txt")
    annotaion_file = open(output_annotation_path, mode='w', encoding='utf8')
    with torch.no_grad():
        for image_tensors, image_path_list in demo_loader:
            batch_size = image_tensors.size(0)
            image = image_tensors.to(device)
            # For max length prediction
            length_for_pred = torch.IntTensor([opt.batch_max_length] * batch_size).to(
                device
            )
            text_for_pred = (
                torch.LongTensor(batch_size, opt.batch_max_length + 1)
                .fill_(0)
                .to(device)
            )
            preds = model(image, text_for_pred, is_train=False)
            # select max probabilty (greddy decoding) then decode index to character
            _, preds_index = preds.max(2)
            # preds_str = converter.decode(preds_index, length_for_pred)
            
            preds_str = converter.decode(preds_index[:, 1:], length_for_pred)
            preds_prob = F.softmax(preds, dim=2)
            preds_max_prob, _ = preds_prob.max(dim=2)
            
            for pred, pred_max_prob, polygon, image_name in zip(preds_str, preds_max_prob, dict_recognition.get(img_unique_key), image_path_list):
                pred_EOS = pred.find("[s]")
                pred = re.sub(r',', '쉼표', pred[:pred_EOS].strip('\n').strip('\t'))
                pred_max_prob = pred_max_prob[:pred_EOS]
                result_text_line = ','.join(list(map(str, polygon))) + f',{pred}\n'
                annotaion_file.write(result_text_line)

            if len(dict_recognition.get(img_unique_key)) != len(preds_str):
                print(len(dict_recognition.get(img_unique_key)), len(preds_str))
    # prediction file input io
    if dict_recognition is not None:
        return dict_recognition