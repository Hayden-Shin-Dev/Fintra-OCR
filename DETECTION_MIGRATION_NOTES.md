# Modern Detection migration status

Status: `NOT_STARTED` (intentional, not a failed baseline).

The validated original Detection path depends on MMDetection 2.20.0,
MMCV 1.4.3, custom `OCRMaskRCNN` modules, old config semantics, and compiled
ops. The original checkpoint is a 351MB state dict. The RTX4050 cannot execute
the original PyTorch 1.7.1 binary because that binary has no `sm_89` support.

No current MMDetection/MMCV package was installed as a substitute. Doing that
would change registries, config semantics, compiled operators, tensor behavior,
and potentially checkpoint key/shape interpretation before parity could be
measured. The next detection phase must choose and document one of these
explicit paths:

1. Reconstruct the exact custom OCRMaskRCNN graph against a compatible modern
   framework and prove strict checkpoint compatibility; or
2. Port only the inference graph and postprocessing, with a state-dict/key
   audit and candidate-level comparison against the existing Detection PKL.

Until that work is complete, this project must not call Modern Detection or
Modern end-to-end OCR `PASS`.

