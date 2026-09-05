# Original Detection Reference — Static Import and Dependency Audit

This audit is static: Python files were parsed with `ast`; no project import, Docker build, model inference, or Detection execution was performed.

- config start: `artifacts/aihub/reference/original_detection/transit_detection/transit_config.py`
- recursively visited local Python files: `231`
- recorded import edges: `1097`
- unresolved/external import names: `105`

## Config dependency literals

- `ann_file=/workspace/images/transit_train/convert_json/2023-01-22_latest_test.json`
- `ann_file=/workspace/images/transit_train/convert_json/2023-01-22_latest_train.json`
- `ann_file=/workspace/images/transit_train/convert_json/2023-01-22_latest_validation.json`
- `checkpoint=torchvision://resnet50`
- `img_prefix=/workspace/images/transit_train/imgs_resize`
- `type=AnchorGenerator`
- `type=BN`
- `type=Collect`
- `type=CrossEntropyLoss`
- `type=DefaultFormatBundle`
- `type=DeltaXYWHBBoxCoder`
- `type=FCNMaskHead`
- `type=IcdarDataset`
- `type=ImageToTensor`
- `type=L1Loss`
- `type=LoadAnnotations`
- `type=LoadImageFromFile`
- `type=MaxIoUAssigner`
- `type=MultiScaleFlipAug`
- `type=Normalize`
- `type=OCRMaskRCNN`
- `type=OHEMSampler`
- `type=Pad`
- `type=Pretrained`
- `type=RPNHead`
- `type=RandomCropInstances`
- `type=RandomFlip`
- `type=RandomSampler`
- `type=Resize`
- `type=RoIAlign`
- `type=SGD`
- `type=ScaleAspectJitter`
- `type=Shared2FCBBoxHead`
- `type=SingleRoIExtractor`
- `type=StandardRoIHead`
- `type=TextLoggerHook`
- `type=UniformConcatDataset`
- `type=mmdet.FPN`
- `type=mmdet.ResNet`
- `type=nms`

## Required reference checks

| Item | Exists | Preserved path | Role |
|---|---:|---|---|
| OCRMaskRCNN | YES | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/ocr_mask_rcnn.py` | custom detector |
| backbone/FPN/RPN/RoI/bbox/mask heads | YES | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models` | model registry and standard/custom model definitions |
| custom losses/mask utilities | YES | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core` | custom geometry/mask logic |
| custom dataset/pipeline | YES | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets` | dataset and transform implementations |
| image preprocessing/postprocessing | YES | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr` | inference, transforms, mask-to-quad and utilities |
| inference entrypoint | YES | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | official detection test entrypoint |
| checkpoint | YES | `artifacts/aihub/runtime/transit_detection_model.pth` | transit detection weights |
| checkpoint metadata | YES | `artifacts/aihub/reference/original_detection/model_store/transit_detection_model_info.log` | packaged training metadata |
| official evaluator | YES | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | AI-Hub evaluation code |
| 15-document Detection PKLs | YES | `artifacts/aihub/validation/smoke` | preserved original Detection outputs |
| Recognition golden reference | YES | `artifacts/aihub/validation/smoke` | preserved original OCR outputs |

## Recursively visited local Python files

- `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/arg_parser.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/file_utils.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/validation.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_ic13.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_iou.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/kie_metric.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ner_metric.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ocr_metric.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/utils.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/mask.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/builder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/icdar_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ner_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_seg_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/openset_kie_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/box_utils.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/crop.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/custom_format_bundle.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/dbnet_transforms.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/kie_transforms.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/loading.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ner_transforms.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_seg_targets.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/test_time_aug.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/panet_targets.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/psenet_targets.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/text_det_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/uniform_concat_dataset.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/loader.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/parser.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/single_stage.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/layers/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/layers/transformer_layers.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/dice_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/focal_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/transformer_module.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/sdmgr_head.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/sdmgr_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/classifiers/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/classifiers/ner_classifier.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/convertors/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/convertors/ner_convertor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/fc_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/encoders/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/encoders/bert_encoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_cross_entropy_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_focal_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/utils/bert.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/db_head.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pse_head.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/textsnake_head.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/dbnet.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/drrg.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/fcenet.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/ocr_mask_rcnn.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/panet.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/psenet.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/textsnake.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/db_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/drrg_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/fce_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pse_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/textsnake_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/gcn.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/local_graph.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/utils.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpem_ffm.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_cat.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_unet.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpnf.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/base_postprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/db_postprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/drrg_postprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/fce_postprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/nrtr_modality_transformer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet31_ocr.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet_abi.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/shallow_cnn.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/very_deep_vgg.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/abi.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/attn.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/base.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/ctc.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/seg.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_vision_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/crnn_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/position_attention_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/robust_scanner_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder_with_bs.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/abinet_vision_model.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/channel_reduction_encoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/nrtr_encoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/satrn_encoder.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/transformer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/abi_fuser.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/seg_head.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/conv_layer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/dot_product_attention_layer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/lstm_layer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/position_aware_layer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/robust_scanner_fusion_layer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/satrn_layers.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ce_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ctc_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/mix_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/seg_loss.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/fpn_ocr.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/base_preprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/tps_preprocessor.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/abinet.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/crnn.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/nrtr.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/robust_scanner.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/sar.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/satrn.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/seg_recognizer.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/box_util.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/check_argument.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/collect_env.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/data_convert_util.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/fileio.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/img_util.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/lmdb_util.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/logger.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/model.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/setup_env.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/string_util.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/version.py`
- `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py`
- `artifacts/aihub/reference/original_detection/transit_detection/transit_config.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/camera.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/geometry.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/noise.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/ops.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/pattern.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/process.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/warp.py`
- `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py`
- `runtime/modern_gpu/vendor/original_recognition/dataset.py`
- `runtime/modern_gpu/vendor/original_recognition/eval_utils.py`
- `runtime/modern_gpu/vendor/original_recognition/model.py`
- `runtime/modern_gpu/vendor/original_recognition/model_inference.py`
- `runtime/modern_gpu/vendor/original_recognition/modules/feature_extraction.py`
- `runtime/modern_gpu/vendor/original_recognition/modules/prediction.py`
- `runtime/modern_gpu/vendor/original_recognition/modules/sequence_modeling.py`
- `runtime/modern_gpu/vendor/original_recognition/modules/transformation.py`
- `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py`

## Unresolved or external imports

These names are expected to be supplied by the runtime (MMCV/MMDetection, PyTorch, or third-party packages), unless marked as a missing local module.

- `PIL`
- `PIL.ImageEnhance`
- `PIL.ImageOps`
- `Polygon`
- `__future__`
- `abc`
- `argparse`
- `codecs`
- `collections`
- `concurrent.futures`
- `copy`
- `cv2`
- `difflib`
- `functools`
- `imgaug`
- `imgaug.augmenters`
- `inspect`
- `io`
- `itertools`
- `json`
- `lanms`
- `lmdb`
- `logging`
- `math`
- `matplotlib`
- `mmcv`
- `mmcv.cnn`
- `mmcv.cnn.bricks.transformer`
- `mmcv.cnn.resnet`
- `mmcv.image`
- `mmcv.ops`
- `mmcv.parallel`
- `mmcv.runner`
- `mmcv.runner.dist_utils`
- `mmcv.utils`
- `mmcv.utils.parrots_wrapper`
- `mmdet`
- `mmdet.apis`
- `mmdet.core`
- `mmdet.core.mask`
- `mmdet.datasets`
- `mmdet.datasets.api_wrappers`
- `mmdet.datasets.builder`
- `mmdet.datasets.coco`
- `mmdet.datasets.pipelines`
- `mmdet.datasets.pipelines.compose`
- `mmdet.datasets.pipelines.formating`
- `mmdet.datasets.pipelines.loading`
- `mmdet.datasets.pipelines.transforms`
- `mmdet.models.builder`
- `mmdet.models.detectors`
- `mmdet.models.losses`
- `natsort`
- `numpy`
- `numpy.fft`
- `numpy.linalg`
- `operator`
- `os`
- `os.path`
- `packaging.version`
- `pathlib`
- `pkg_resources`
- `platform`
- `pprint`
- `psutil`
- `pyclipper`
- `queue`
- `random`
- `rapidfuzz`
- `ray`
- `re`
- `scipy.ndimage`
- `shapely`
- `shapely.geometry`
- `shutil`
- `six`
- `skimage`
- `skimage.filters`
- `skimage.morphology`
- `string`
- `sys`
- `tempfile`
- `time`
- `timm.models`
- `timm.models.registry`
- `timm.models.vision_transformer`
- `torch`
- `torch._utils`
- `torch.distributed`
- `torch.multiprocessing`
- `torch.nn`
- `torch.nn.functional`
- `torch.utils.checkpoint`
- `torch.utils.data`
- `torch.utils.model_zoo`
- `torchvision.transforms`
- `torchvision.transforms.functional`
- `tqdm`
- `ujson`
- `urllib`
- `uuid`
- `wand.api`
- `wand.image`
- `warnings`
- `zipfile`

## Local import edges

| From | Import | Resolved target |
|---|---|---|
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `collections` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `eval_utils` | `runtime/modern_gpu/vendor/original_recognition/eval_utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `model` | `runtime/modern_gpu/vendor/original_recognition/model.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `model_inference` | `runtime/modern_gpu/vendor/original_recognition/model_inference.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `os.path` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `psutil` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `pyclipper` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `ray` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `shapely` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `shutil` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `string` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `tempfile` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `tqdm` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `ujson` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/detection_model.py` | `uuid` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/arg_parser.py` | `argparse` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py` | `Polygon` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py` | `abc` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py` | `arg_parser` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/arg_parser.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/file_utils.py` | `codecs` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/file_utils.py` | `re` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/file_utils.py` | `zipfile` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `arg_parser` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/arg_parser.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `box_types` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/box_types.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `file_utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/file_utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `io` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `json` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `pprint` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `re` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `sys` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `sys` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `validation` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/validation.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` | `zipfile` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `Polygon` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `arg_parser` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/arg_parser.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `concurrent.futures` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `file_utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/file_utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `itertools` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `rrc_evaluation_funcs` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/rrc_evaluation_funcs.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `tqdm` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py` | `validation` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/validation.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/validation.py` | `arg_parser` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/arg_parser.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/validation.py` | `file_utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/file_utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/__init__.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/__init__.py` | `mmdet` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/__init__.py` | `packaging.version` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/__init__.py` | `version` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/version.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/__init__.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` | `mmcv.image` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` | `mmcv.parallel` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` | `os.path` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` | `utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` | `copy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` | `mmdet.datasets` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` | `evaluation` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` | `mask` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/mask.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` | `visualize` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` | `hmean` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` | `hmean_ic13` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_ic13.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` | `hmean_iou` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_iou.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` | `kie_metric` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/kie_metric.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` | `ner_metric` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ner_metric.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` | `ocr_metric` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ocr_metric.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` | `mmocr.core.evaluation` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` | `mmocr.core.evaluation.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` | `mmocr.core.mask` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/mask.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` | `operator` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_ic13.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_ic13.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_ic13.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_iou.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_iou.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean_iou.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/kie_metric.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ner_metric.py` | `collections` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ocr_metric.py` | `difflib` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ocr_metric.py` | `rapidfuzz` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ocr_metric.py` | `re` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/utils.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/utils.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/utils.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/mask.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/mask.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/mask.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `matplotlib` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `shutil` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `urllib` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `base_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `icdar_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/icdar_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `kie_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `ner_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ner_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `ocr_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `ocr_seg_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_seg_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `openset_kie_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/openset_kie_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `pipelines` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `text_det_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/text_det_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `uniform_concat_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/uniform_concat_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` | `utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` | `mmdet.datasets.pipelines` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` | `mmocr.datasets.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` | `torch.utils.data` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/builder.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/icdar_dataset.py` | `mmdet.datasets.api_wrappers` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/icdar_dataset.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/icdar_dataset.py` | `mmdet.datasets.coco` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/icdar_dataset.py` | `mmocr.core.evaluation.hmean` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/icdar_dataset.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/icdar_dataset.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `copy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `mmocr.core` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `mmocr.datasets.base_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `mmocr.datasets.pipelines` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/kie_dataset.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ner_dataset.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ner_dataset.py` | `mmocr.core.evaluation.ner_metric` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ner_metric.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ner_dataset.py` | `mmocr.datasets.base_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_dataset.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_dataset.py` | `mmocr.core.evaluation.ocr_metric` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/ocr_metric.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_dataset.py` | `mmocr.datasets.base_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_seg_dataset.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_seg_dataset.py` | `mmocr.datasets.ocr_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/ocr_seg_dataset.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/openset_kie_dataset.py` | `copy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/openset_kie_dataset.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/openset_kie_dataset.py` | `mmocr.datasets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/openset_kie_dataset.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/openset_kie_dataset.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `box_utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/box_utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `custom_format_bundle` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/custom_format_bundle.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `dbnet_transforms` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/dbnet_transforms.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `kie_transforms` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/kie_transforms.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `loading` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/loading.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `ner_transforms` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ner_transforms.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `ocr_seg_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_seg_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `ocr_transforms` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `test_time_aug` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/test_time_aug.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `textdet_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `transform_wrappers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/__init__.py` | `transforms` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/box_utils.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/box_utils.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/crop.py` | `box_utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/box_utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/crop.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/crop.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/crop.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/crop.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/custom_format_bundle.py` | `mmcv.parallel` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/custom_format_bundle.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/custom_format_bundle.py` | `mmdet.datasets.pipelines.formating` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/custom_format_bundle.py` | `mmocr.core.visualize` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/visualize.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/custom_format_bundle.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/dbnet_transforms.py` | `imgaug` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/dbnet_transforms.py` | `imgaug.augmenters` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/dbnet_transforms.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/dbnet_transforms.py` | `mmdet.core.mask` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/dbnet_transforms.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/dbnet_transforms.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/kie_transforms.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/kie_transforms.py` | `mmcv.parallel` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/kie_transforms.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/kie_transforms.py` | `mmdet.datasets.pipelines.formating` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/kie_transforms.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/loading.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/loading.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/loading.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/loading.py` | `mmdet.datasets.pipelines.loading` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/loading.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/loading.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ner_transforms.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ner_transforms.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ner_transforms.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_seg_targets.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_seg_targets.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_seg_targets.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_seg_targets.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_seg_targets.py` | `mmocr.utils.check_argument` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/check_argument.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_seg_targets.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `mmcv.runner.dist_utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `mmocr.datasets.pipelines.crop` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/crop.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/ocr_transforms.py` | `torchvision.transforms.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/test_time_aug.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/test_time_aug.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/test_time_aug.py` | `mmdet.datasets.pipelines.compose` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/test_time_aug.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` | `base_textdet_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` | `dbnet_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` | `drrg_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` | `fcenet_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` | `panet_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/panet_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` | `psenet_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/psenet_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` | `textsnake_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py` | `mmocr.utils.check_argument` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/check_argument.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py` | `pyclipper` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/base_textdet_targets.py` | `sys` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py` | `pyclipper` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/dbnet_targets.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` | `lanms` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` | `mmocr.utils.check_argument` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/check_argument.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` | `numpy.linalg` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/drrg_targets.py` | `textsnake_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py` | `mmocr.utils.check_argument` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/check_argument.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py` | `numpy.fft` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py` | `numpy.linalg` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/fcenet_targets.py` | `textsnake_targets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/panet_targets.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/panet_targets.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/panet_targets.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/psenet_targets.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/psenet_targets.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` | `mmocr.utils.check_argument` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/check_argument.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/textdet_targets/textsnake_targets.py` | `numpy.linalg` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `inspect` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `mmdet.datasets.pipelines` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `random` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transform_wrappers.py` | `torchvision.transforms` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `mmdet.datasets.pipelines.transforms` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `mmocr.core.evaluation.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/pipelines/transforms.py` | `torchvision.transforms` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/text_det_dataset.py` | `mmdet.datasets.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/text_det_dataset.py` | `mmocr.core.evaluation.hmean` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/hmean.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/text_det_dataset.py` | `mmocr.datasets.base_dataset` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/base_dataset.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/text_det_dataset.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/uniform_concat_dataset.py` | `copy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/uniform_concat_dataset.py` | `mmdet.datasets` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/uniform_concat_dataset.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/__init__.py` | `loader` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/loader.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/__init__.py` | `parser` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/parser.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/loader.py` | `lmdb` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/loader.py` | `mmocr.datasets.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/loader.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/loader.py` | `os.path` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/parser.py` | `json` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/parser.py` | `mmocr.datasets.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/utils/parser.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` | `builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` | `common` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` | `kie` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` | `ner` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` | `textdet` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` | `textrecog` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` | `mmdet.models.builder` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` | `backbones` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` | `layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/layers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` | `losses` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` | `modules` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/__init__.py` | `unet` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py` | `mmcv.utils.parrots_wrapper` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/backbones/unet.py` | `torch.utils.checkpoint` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/__init__.py` | `single_stage` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/single_stage.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/single_stage.py` | `mmdet.models.detectors` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/single_stage.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/single_stage.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/layers/__init__.py` | `transformer_layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/layers/transformer_layers.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/layers/transformer_layers.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/layers/transformer_layers.py` | `mmocr.models.common.modules` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/layers/transformer_layers.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/__init__.py` | `dice_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/dice_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/__init__.py` | `focal_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/focal_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/dice_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/dice_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/dice_loss.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/focal_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/focal_loss.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/focal_loss.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/__init__.py` | `transformer_module` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/transformer_module.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/transformer_module.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/transformer_module.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/transformer_module.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/transformer_module.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/transformer_module.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/__init__.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/__init__.py` | `extractors` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/__init__.py` | `heads` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/__init__.py` | `losses` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/__init__.py` | `sdmgr` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `mmocr.core` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `mmocr.models.common.detectors` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/extractors/sdmgr.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/__init__.py` | `sdmgr_head` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/sdmgr_head.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/sdmgr_head.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/sdmgr_head.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/sdmgr_head.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/sdmgr_head.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/heads/sdmgr_head.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/__init__.py` | `sdmgr_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/sdmgr_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/sdmgr_loss.py` | `mmdet.models.losses` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/sdmgr_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/sdmgr_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/kie/losses/sdmgr_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py` | `classifiers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/classifiers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py` | `convertors` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/convertors/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py` | `decoders` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py` | `encoders` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/encoders/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/__init__.py` | `losses` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/classifiers/__init__.py` | `ner_classifier` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/classifiers/ner_classifier.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/classifiers/ner_classifier.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/classifiers/ner_classifier.py` | `mmocr.models.textrecog.recognizer.base` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/convertors/__init__.py` | `ner_convertor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/convertors/ner_convertor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/convertors/ner_convertor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/convertors/ner_convertor.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/convertors/ner_convertor.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/__init__.py` | `fc_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/fc_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/fc_decoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/fc_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/fc_decoder.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/fc_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/decoders/fc_decoder.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/encoders/__init__.py` | `bert_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/encoders/bert_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/encoders/bert_encoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/encoders/bert_encoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/encoders/bert_encoder.py` | `mmocr.models.ner.utils.bert` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/utils/bert.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/__init__.py` | `masked_cross_entropy_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_cross_entropy_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/__init__.py` | `masked_focal_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_focal_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_cross_entropy_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_cross_entropy_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_cross_entropy_loss.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_focal_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_focal_loss.py` | `mmocr.models.common.losses.focal_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/focal_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/losses/masked_focal_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/utils/bert.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/utils/bert.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/utils/bert.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/ner/utils/bert.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py` | `dense_heads` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py` | `detectors` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py` | `losses` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py` | `necks` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/__init__.py` | `postprocess` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` | `db_head` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/db_head.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` | `drrg_head` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` | `fce_head` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` | `head_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` | `pan_head` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` | `pse_head` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pse_head.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` | `textsnake_head` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/textsnake_head.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/db_head.py` | `head_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/db_head.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/db_head.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/db_head.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/db_head.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/db_head.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `head_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `mmocr.models.textdet.modules` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/drrg_head.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py` | `head_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py` | `postprocess.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/fce_head.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` | `head_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pan_head.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pse_head.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/pse_head.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/textsnake_head.py` | `head_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/head_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/textsnake_head.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/textsnake_head.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/textsnake_head.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/dense_heads/textsnake_head.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `dbnet` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/dbnet.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `drrg` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/drrg.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `fcenet` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/fcenet.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `ocr_mask_rcnn` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/ocr_mask_rcnn.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `panet` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/panet.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `psenet` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/psenet.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `single_stage_text_detector` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `text_detector_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/__init__.py` | `textsnake` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/textsnake.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/dbnet.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/dbnet.py` | `single_stage_text_detector` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/dbnet.py` | `text_detector_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/drrg.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/drrg.py` | `single_stage_text_detector` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/drrg.py` | `text_detector_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/fcenet.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/fcenet.py` | `single_stage_text_detector` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/fcenet.py` | `text_detector_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/ocr_mask_rcnn.py` | `mmdet.models.detectors` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/ocr_mask_rcnn.py` | `mmocr.core` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/ocr_mask_rcnn.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/ocr_mask_rcnn.py` | `text_detector_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/panet.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/panet.py` | `single_stage_text_detector` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/panet.py` | `text_detector_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/psenet.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/psenet.py` | `single_stage_text_detector` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/psenet.py` | `text_detector_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` | `mmocr.models.common.detectors` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/detectors/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` | `mmocr.core` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/textsnake.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/textsnake.py` | `single_stage_text_detector` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/single_stage_text_detector.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/textsnake.py` | `text_detector_mixin` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/detectors/text_detector_mixin.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py` | `db_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/db_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py` | `drrg_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/drrg_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py` | `fce_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/fce_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py` | `pan_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py` | `pse_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pse_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py` | `textsnake_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/textsnake_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/db_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/db_loss.py` | `mmocr.models.common.losses.dice_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/losses/dice_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/db_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/db_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/db_loss.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/drrg_loss.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/drrg_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/drrg_loss.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/drrg_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/drrg_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/drrg_loss.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/fce_loss.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/fce_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/fce_loss.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/fce_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/fce_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/fce_loss.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `itertools` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pan_loss.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pse_loss.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pse_loss.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pse_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/pse_loss.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/textsnake_loss.py` | `mmdet.core` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/textsnake_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/textsnake_loss.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/textsnake_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/textsnake_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/losses/textsnake_loss.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/__init__.py` | `gcn` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/gcn.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/__init__.py` | `local_graph` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/local_graph.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/__init__.py` | `proposal_local_graph` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/gcn.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/gcn.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/gcn.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/gcn.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/local_graph.py` | `mmcv.ops` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/local_graph.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/local_graph.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/local_graph.py` | `utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py` | `lanms` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py` | `mmcv.ops` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py` | `mmocr.models.textdet.postprocess.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/proposal_local_graph.py` | `utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/modules/utils.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/__init__.py` | `fpem_ffm` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpem_ffm.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/__init__.py` | `fpn_cat` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_cat.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/__init__.py` | `fpn_unet` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_unet.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/__init__.py` | `fpnf` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpnf.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpem_ffm.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpem_ffm.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpem_ffm.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpem_ffm.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_cat.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_cat.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_cat.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_cat.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_cat.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_unet.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_unet.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_unet.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_unet.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpn_unet.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpnf.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpnf.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpnf.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpnf.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/necks/fpnf.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py` | `base_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/base_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py` | `db_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/db_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py` | `drrg_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/drrg_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py` | `fce_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/fce_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py` | `pan_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py` | `pse_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/__init__.py` | `textsnake_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/db_postprocessor.py` | `base_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/base_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/db_postprocessor.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/db_postprocessor.py` | `mmocr.core` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/db_postprocessor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/db_postprocessor.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/db_postprocessor.py` | `utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/drrg_postprocessor.py` | `base_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/base_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/drrg_postprocessor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/drrg_postprocessor.py` | `utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/fce_postprocessor.py` | `base_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/base_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/fce_postprocessor.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/fce_postprocessor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/fce_postprocessor.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/fce_postprocessor.py` | `utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py` | `base_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/base_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py` | `mmcv.ops` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py` | `mmocr.core` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pan_postprocessor.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py` | `base_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/base_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py` | `mmcv.ops` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py` | `mmocr.core` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/pse_postprocessor.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py` | `base_postprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/base_postprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py` | `skimage.morphology` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/textsnake_postprocessor.py` | `utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `functools` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `mmocr.core.evaluation.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/evaluation/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `numpy.fft` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `numpy.linalg` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `operator` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `pyclipper` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textdet/postprocess/utils.py` | `shapely.geometry` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `backbones` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `convertors` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `decoders` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `encoders` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `fusers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `heads` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `losses` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `necks` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `preprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/__init__.py` | `recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/__init__.py` | `nrtr_modality_transformer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/nrtr_modality_transformer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/__init__.py` | `resnet31_ocr` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet31_ocr.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/__init__.py` | `resnet_abi` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet_abi.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/__init__.py` | `shallow_cnn` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/shallow_cnn.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/__init__.py` | `very_deep_vgg` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/very_deep_vgg.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/nrtr_modality_transformer.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/nrtr_modality_transformer.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/nrtr_modality_transformer.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet31_ocr.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet31_ocr.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet31_ocr.py` | `mmocr.models.textrecog.layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet31_ocr.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet31_ocr.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet_abi.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet_abi.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet_abi.py` | `mmocr.models.textrecog.layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet_abi.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/resnet_abi.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/shallow_cnn.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/shallow_cnn.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/shallow_cnn.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/shallow_cnn.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/very_deep_vgg.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/very_deep_vgg.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/backbones/very_deep_vgg.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/__init__.py` | `abi` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/abi.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/__init__.py` | `attn` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/attn.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/__init__.py` | `base` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/base.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/__init__.py` | `ctc` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/ctc.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/__init__.py` | `seg` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/seg.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/abi.py` | `attn` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/attn.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/abi.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/abi.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/abi.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/attn.py` | `base` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/base.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/attn.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/attn.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/attn.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/base.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/base.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/ctc.py` | `base` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/base.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/ctc.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/ctc.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/ctc.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/ctc.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/ctc.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/seg.py` | `base` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/base.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/seg.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/seg.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/seg.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/seg.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/convertors/seg.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `abinet_language_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `abinet_vision_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_vision_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `crnn_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/crnn_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `nrtr_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `position_attention_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/position_attention_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `robust_scanner_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/robust_scanner_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `sar_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `sar_decoder_with_bs` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder_with_bs.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` | `sequence_attention_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` | `copy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` | `mmcv.cnn.bricks.transformer` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` | `mmocr.models.common.modules` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_language_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_vision_decoder.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_vision_decoder.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_vision_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_vision_decoder.py` | `mmocr.models.common.modules` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_vision_decoder.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/abinet_vision_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/crnn_decoder.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/crnn_decoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/crnn_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/crnn_decoder.py` | `mmocr.models.textrecog.layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/crnn_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` | `mmocr.models.common` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/nrtr_decoder.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/position_attention_decoder.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/position_attention_decoder.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/position_attention_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/position_attention_decoder.py` | `mmocr.models.textrecog.layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/position_attention_decoder.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/position_attention_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/robust_scanner_decoder.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/robust_scanner_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/robust_scanner_decoder.py` | `mmocr.models.textrecog.layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/robust_scanner_decoder.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/robust_scanner_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/robust_scanner_decoder.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder_with_bs.py` | `.` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder_with_bs.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder_with_bs.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder_with_bs.py` | `queue` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder_with_bs.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sar_decoder_with_bs.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py` | `base_decoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/base_decoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py` | `mmocr.models.textrecog.layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/decoders/sequence_attention_decoder.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py` | `abinet_vision_model` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/abinet_vision_model.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py` | `base_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py` | `channel_reduction_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/channel_reduction_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py` | `nrtr_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/nrtr_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py` | `sar_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py` | `satrn_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/satrn_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/__init__.py` | `transformer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/transformer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/abinet_vision_model.py` | `base_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/abinet_vision_model.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/channel_reduction_encoder.py` | `base_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/channel_reduction_encoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/channel_reduction_encoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/nrtr_encoder.py` | `base_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/nrtr_encoder.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/nrtr_encoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/nrtr_encoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/nrtr_encoder.py` | `mmocr.models.common` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/nrtr_encoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py` | `base_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/sar_encoder.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/satrn_encoder.py` | `base_encoder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/base_encoder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/satrn_encoder.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/satrn_encoder.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/satrn_encoder.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/satrn_encoder.py` | `mmocr.models.textrecog.layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/satrn_encoder.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/transformer.py` | `copy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/transformer.py` | `mmcv.cnn.bricks.transformer` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/transformer.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/transformer.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/encoders/transformer.py` | `mmocr.models.common.modules` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/modules/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/__init__.py` | `abi_fuser` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/abi_fuser.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/abi_fuser.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/abi_fuser.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/abi_fuser.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/fusers/abi_fuser.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/__init__.py` | `seg_head` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/seg_head.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/seg_head.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/seg_head.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/seg_head.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/seg_head.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/heads/seg_head.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` | `conv_layer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/conv_layer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` | `dot_product_attention_layer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/dot_product_attention_layer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` | `lstm_layer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/lstm_layer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` | `position_aware_layer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/position_aware_layer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` | `robust_scanner_fusion_layer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/robust_scanner_fusion_layer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/__init__.py` | `satrn_layers` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/satrn_layers.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/conv_layer.py` | `mmcv.cnn.resnet` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/conv_layer.py` | `mmcv.cnn.resnet` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/conv_layer.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/dot_product_attention_layer.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/dot_product_attention_layer.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/dot_product_attention_layer.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/lstm_layer.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/position_aware_layer.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/robust_scanner_fusion_layer.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/robust_scanner_fusion_layer.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/robust_scanner_fusion_layer.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/satrn_layers.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/satrn_layers.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/satrn_layers.py` | `mmocr.models.common` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/common/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/satrn_layers.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/satrn_layers.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/layers/satrn_layers.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/__init__.py` | `ce_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ce_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/__init__.py` | `ctc_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ctc_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/__init__.py` | `mix_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/mix_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/__init__.py` | `seg_loss` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/seg_loss.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ce_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ce_loss.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ctc_loss.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ctc_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ctc_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/ctc_loss.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/mix_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/mix_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/mix_loss.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/mix_loss.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/seg_loss.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/seg_loss.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/seg_loss.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/losses/seg_loss.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/__init__.py` | `fpn_ocr` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/fpn_ocr.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/fpn_ocr.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/fpn_ocr.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/fpn_ocr.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/fpn_ocr.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/necks/fpn_ocr.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/__init__.py` | `base_preprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/base_preprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/__init__.py` | `tps_preprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/tps_preprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/base_preprocessor.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/base_preprocessor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/tps_preprocessor.py` | `base_preprocessor` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/base_preprocessor.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/tps_preprocessor.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/tps_preprocessor.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/tps_preprocessor.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/tps_preprocessor.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/preprocessor/tps_preprocessor.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `abinet` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/abinet.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `base` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `crnn` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/crnn.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `encode_decode_recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `nrtr` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/nrtr.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `robust_scanner` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/robust_scanner.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `sar` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/sar.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `satrn` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/satrn.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/__init__.py` | `seg_recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/seg_recognizer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/abinet.py` | `encode_decode_recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/abinet.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/abinet.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/abinet.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` | `abc` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` | `collections` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` | `mmocr.core` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/core/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` | `torch.distributed` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/crnn.py` | `encode_decode_recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/crnn.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` | `base` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/nrtr.py` | `encode_decode_recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/nrtr.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/robust_scanner.py` | `encode_decode_recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/robust_scanner.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/sar.py` | `encode_decode_recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/sar.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/satrn.py` | `encode_decode_recognizer` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/encode_decode_recognizer.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/satrn.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/seg_recognizer.py` | `base` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/base.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/seg_recognizer.py` | `mmocr.models.builder` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/builder.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/textrecog/recognizer/seg_recognizer.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `box_util` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/box_util.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `check_argument` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/check_argument.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `collect_env` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/collect_env.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `data_convert_util` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/data_convert_util.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `fileio` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/fileio.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `img_util` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/img_util.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `lmdb_util` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/lmdb_util.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `logger` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/logger.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `model` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/model.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `setup_env` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/setup_env.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` | `string_util` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/string_util.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/box_util.py` | `functools` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/box_util.py` | `mmocr.utils.check_argument` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/check_argument.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/box_util.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/collect_env.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/collect_env.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/collect_env.py` | `mmocr` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/data_convert_util.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/fileio.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/fileio.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/img_util.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/img_util.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/lmdb_util.py` | `lmdb` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/lmdb_util.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/lmdb_util.py` | `pathlib` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/lmdb_util.py` | `shutil` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/lmdb_util.py` | `sys` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/lmdb_util.py` | `time` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/logger.py` | `logging` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/logger.py` | `mmcv.utils` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/model.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/setup_env.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/setup_env.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/setup_env.py` | `platform` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/setup_env.py` | `torch.multiprocessing` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/setup_env.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `argparse` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmcv` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmcv.cnn` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmcv.parallel` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmcv.runner` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmdet.apis` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmocr.apis.test` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/test.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmocr.apis.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/apis/utils.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmocr.datasets` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/datasets/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmocr.models` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/models/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `mmocr.utils` | `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/mmocr/utils/__init__.py` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `artifacts/aihub/reference/original_detection/text_recognition_baseline/new_detection/tools/test.py` | `warnings` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `io` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `ops` | `runtime/modern_gpu/vendor/original_recognition/augmentation/ops.py` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `scipy.ndimage` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `skimage.filters` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `torchvision.transforms` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `wand.api` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` | `wand.image` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/camera.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/camera.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/camera.py` | `io` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/camera.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/camera.py` | `skimage` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/camera.py` | `skimage` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/geometry.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/geometry.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/geometry.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/noise.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/noise.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/noise.py` | `skimage` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/ops.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/ops.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/ops.py` | `scipy.ndimage` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/ops.py` | `wand.api` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/ops.py` | `wand.image` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/pattern.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/pattern.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/pattern.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/process.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/process.py` | `PIL.ImageEnhance` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/process.py` | `PIL.ImageOps` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/process.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/warp.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/warp.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/warp.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` | `io` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` | `ops` | `runtime/modern_gpu/vendor/original_recognition/augmentation/ops.py` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` | `pkg_resources` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` | `skimage` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `PIL` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `PIL.ImageOps` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.blur` | `runtime/modern_gpu/vendor/original_recognition/augmentation/blur.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.camera` | `runtime/modern_gpu/vendor/original_recognition/augmentation/camera.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.geometry` | `runtime/modern_gpu/vendor/original_recognition/augmentation/geometry.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.noise` | `runtime/modern_gpu/vendor/original_recognition/augmentation/noise.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.pattern` | `runtime/modern_gpu/vendor/original_recognition/augmentation/pattern.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.process` | `runtime/modern_gpu/vendor/original_recognition/augmentation/process.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.warp` | `runtime/modern_gpu/vendor/original_recognition/augmentation/warp.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.weather` | `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `augmentation.weather` | `runtime/modern_gpu/vendor/original_recognition/augmentation/weather.py` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `lmdb` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `natsort` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `os` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `re` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `six` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `sys` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `torch._utils` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `torch.utils.data` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `torchvision.transforms` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/dataset.py` | `torchvision.transforms.functional` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/eval_utils.py` | `argparse` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/eval_utils.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/eval_utils.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model.py` | `math` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model.py` | `modules.feature_extraction` | `runtime/modern_gpu/vendor/original_recognition/modules/feature_extraction.py` |
| `runtime/modern_gpu/vendor/original_recognition/model.py` | `modules.prediction` | `runtime/modern_gpu/vendor/original_recognition/modules/prediction.py` |
| `runtime/modern_gpu/vendor/original_recognition/model.py` | `modules.sequence_modeling` | `runtime/modern_gpu/vendor/original_recognition/modules/sequence_modeling.py` |
| `runtime/modern_gpu/vendor/original_recognition/model.py` | `modules.transformation` | `runtime/modern_gpu/vendor/original_recognition/modules/transformation.py` |
| `runtime/modern_gpu/vendor/original_recognition/model.py` | `modules.vitstr` | `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` |
| `runtime/modern_gpu/vendor/original_recognition/model.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model_inference.py` | `cv2` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model_inference.py` | `dataset` | `runtime/modern_gpu/vendor/original_recognition/dataset.py` |
| `runtime/modern_gpu/vendor/original_recognition/model_inference.py` | `eval_utils` | `runtime/modern_gpu/vendor/original_recognition/eval_utils.py` |
| `runtime/modern_gpu/vendor/original_recognition/model_inference.py` | `os.path` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model_inference.py` | `re` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model_inference.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model_inference.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/model_inference.py` | `torch.utils.data` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/feature_extraction.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/feature_extraction.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/prediction.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/prediction.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/prediction.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/sequence_modeling.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/transformation.py` | `numpy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/transformation.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/transformation.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/transformation.py` | `torch.nn.functional` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `__future__` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `__future__` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `__future__` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `copy` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `functools` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `logging` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `timm.models` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `timm.models.registry` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `timm.models.vision_transformer` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `torch` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `torch.nn` | `EXTERNAL/UNRESOLVED` |
| `runtime/modern_gpu/vendor/original_recognition/modules/vitstr.py` | `torch.utils.model_zoo` | `EXTERNAL/UNRESOLVED` |
