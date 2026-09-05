$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$baseTag = "fintra-modern-gpu:torch260-cu124"
$detectionTag = "fintra-modern-detection:torch260-cu124-mmdet330"
$checkpoint = "/project/artifacts/aihub/runtime/transit_detection_model.pth"
$config = "/opt/fintra/detection_config.py"
$drive = [System.IO.DriveInfo]::new(([System.IO.Path]::GetPathRoot($projectRoot)).TrimEnd('\'))
$freeGB = [math]::Round($drive.AvailableFreeSpace / 1GB, 2)
if ($freeGB -lt 30) {
    throw "Detection build blocked: only ${freeGB}GB is free. Use a separately provisioned build location with at least 30GB free. No Docker build was started."
}

function Invoke-DockerChecked {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE" }
}

if (-not (docker image inspect $baseTag 2>$null)) {
    throw "Missing $baseTag. Run RUN_GPU.ps1 once to build the Modern base image."
}

Write-Host "[1/5] Building isolated Modern Detection image..."
Invoke-DockerChecked @("build", "-t", $detectionTag, "-f", (Join-Path $PSScriptRoot "Dockerfile.detection"), $PSScriptRoot)

$ciCase = Join-Path $projectRoot "artifacts\aihub\validation\smoke\ci-01"
$ciImageName = (Get-Content (Join-Path $ciCase "case_manifest.json") -Raw | ConvertFrom-Json).image
$ciImage = "/project/artifacts/aihub/validation/smoke/ci-01/transit_train/imgs_resize/$ciImageName"
$ciModern = "/project/artifacts/aihub/modern_gpu/detection_parity/ci-01/detection.json"
$ciReference = "/project/artifacts/aihub/validation/smoke/ci-01/transit_train/transit_detection_result_latest.pkl"
$ciParity = "/project/artifacts/aihub/modern_gpu/detection_parity/ci-01/parity.json"

Write-Host "[2/5] Running CI-01 Modern Detection smoke and original-PKL parity..."
Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $detectionTag, "python", "/opt/fintra/modern_detection.py", "--image", $ciImage, "--checkpoint", $checkpoint, "--config", $config, "--output", $ciModern, "--device", "cuda")
Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $detectionTag, "python", "/opt/fintra/compare_detection.py", "--reference-pkl", $ciReference, "--modern-json", $ciModern, "--output", $ciParity)

$ciParityPayload = Get-Content $ciParity -Raw | ConvertFrom-Json
$requiredParityFields = @(
    "reference_score_gt_0_2_count", "modern_score_gt_0_2_count", "matched_count",
    "mean_bbox_iou", "median_bbox_iou", "iou_ge_0_5_match_rate",
    "iou_ge_0_8_match_rate", "mean_absolute_score_difference",
    "max_coordinate_difference"
)
foreach ($field in $requiredParityFields) {
    if ($null -eq $ciParityPayload.$field) { throw "CI-01 parity is missing field: $field" }
    $number = [double]$ciParityPayload.$field
    if ([double]::IsNaN($number) -or [double]::IsInfinity($number)) { throw "CI-01 parity has non-finite field: $field" }
}
Write-Host ("CI-01 parity evidence: reference_gt_0_2={0}, modern_gt_0_2={1}, matched={2}, mean_iou={3}, iou_ge_0_5={4}, mean_score_diff={5}" -f $ciParityPayload.reference_score_gt_0_2_count, $ciParityPayload.modern_score_gt_0_2_count, $ciParityPayload.matched_count, $ciParityPayload.mean_bbox_iou, $ciParityPayload.iou_ge_0_5_match_rate, $ciParityPayload.mean_absolute_score_difference)
Write-Host "[3/5] CI-01 evidence is structurally valid. Expanding Detection to 15 cases..."
$caseNames = @(
    "ci-01", "ci-02", "ci-03", "ci-04", "ci-05",
    "pl-01", "pl-02", "pl-03", "pl-04", "pl-05",
    "bl-01", "bl-02", "bl-03", "bl-04", "bl-05"
)
foreach ($caseName in $caseNames) {
    $caseRoot = Join-Path $projectRoot ("artifacts\aihub\validation\smoke\" + $caseName)
    $manifest = Get-Content (Join-Path $caseRoot "case_manifest.json") -Raw | ConvertFrom-Json
    $imageName = $manifest.image
    $image = "/project/artifacts/aihub/validation/smoke/$caseName/transit_train/imgs_resize/$imageName"
    $modern = "/project/artifacts/aihub/modern_gpu/detection_parity/$caseName/detection.json"
    $reference = "/project/artifacts/aihub/validation/smoke/$caseName/transit_train/transit_detection_result_latest.pkl"
    $parity = "/project/artifacts/aihub/modern_gpu/detection_parity/$caseName/parity.json"
    Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $detectionTag, "python", "/opt/fintra/modern_detection.py", "--image", $image, "--checkpoint", $checkpoint, "--config", $config, "--output", $modern, "--device", "cuda")
    Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $detectionTag, "python", "/opt/fintra/compare_detection.py", "--reference-pkl", $reference, "--modern-json", $modern, "--output", $parity)
}

Write-Host "[4/5] Running existing Modern Recognition on Modern Detection regions..."
$modernRecognitionTag = $baseTag
$modernRecognitionCheckpoint = "/project/artifacts/aihub/runtime/transit_recog_model.pth"
$modernDictionary = "/project/artifacts/aihub/runtime/unidocs_dict_transit_runtime.txt"
foreach ($caseName in $caseNames) {
    $caseRoot = Join-Path $projectRoot ("artifacts\aihub\validation\smoke\" + $caseName)
    $manifest = Get-Content (Join-Path $caseRoot "case_manifest.json") -Raw | ConvertFrom-Json
    $imageName = $manifest.image
    $image = "/project/artifacts/aihub/validation/smoke/$caseName/transit_train/imgs_resize/$imageName"
    $modernDetection = "/project/artifacts/aihub/modern_gpu/detection_parity/$caseName/detection.json"
    $recognitionOutput = "/project/artifacts/aihub/modern_gpu/end_to_end/$caseName/recognition"
    Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $modernRecognitionTag, "python", "/opt/fintra/modern_recognition.py", "--image", $image, "--regions-json", $modernDetection, "--checkpoint", $modernRecognitionCheckpoint, "--dict", $modernDictionary, "--output-dir", $recognitionOutput, "--device", "cuda")
}

Write-Host "[5/5] Running the bundled AI-Hub official evaluator and aggregating metrics..."
$officialRoot = Join-Path $projectRoot "artifacts\aihub\modern_gpu\official_evaluation"
python (Join-Path $projectRoot "scripts\build_modern_official_inputs.py") --smoke-root (Join-Path $projectRoot "artifacts\aihub\validation\smoke") --modern-root (Join-Path $projectRoot "artifacts\aihub\modern_gpu\end_to_end") --output-dir $officialRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to build Modern official evaluator inputs" }

$officialOutput = Join-Path $officialRoot "official_output"
if (Test-Path -LiteralPath $officialOutput) {
    Remove-Item -LiteralPath $officialOutput -Recurse -Force
}
New-Item -ItemType Directory -Path $officialOutput | Out-Null
$officialScript = "/project/artifacts/aihub/reference/original_detection/text_recognition_baseline/evaluation_method/script.py"
$officialGt = "/project/artifacts/aihub/modern_gpu/official_evaluation/gt.zip"
$officialSubmission = "/project/artifacts/aihub/modern_gpu/official_evaluation/submission.zip"
$officialOutputContainer = "/project/artifacts/aihub/modern_gpu/official_evaluation/official_output"
Invoke-DockerChecked @("run", "--rm", "-v", "${projectRoot}:/project", "-w", "/project", $detectionTag, "python", $officialScript, "-g", $officialGt, "-s", $officialSubmission, "-o", $officialOutputContainer, "--E2E", "--TRANSCRIPTION")

$resultsZip = Join-Path $officialOutput "results.zip"
if (-not (Test-Path -LiteralPath $resultsZip)) { throw "Official evaluator did not produce $resultsZip" }
$extracted = Join-Path $officialOutput "extracted"
New-Item -ItemType Directory -Path $extracted | Out-Null
Expand-Archive -LiteralPath $resultsZip -DestinationPath $extracted -Force
python (Join-Path $projectRoot "scripts\aggregate_official_metrics.py") --smoke-root (Join-Path $projectRoot "artifacts\aihub\validation\smoke") --official-output $officialOutput --output-dir $officialRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to aggregate Modern official metrics" }

Write-Host "STATUS=MODERN_DETECTION_15_AND_FULL_E2E_EXECUTED"
Write-Host "ARTIFACT_ROOT=$officialRoot"
