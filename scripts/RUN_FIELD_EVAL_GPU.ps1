$ErrorActionPreference = "Stop"

# User-run entrypoint for the 60-case field extraction evaluation.
# This script does not build images and does not alter the Modern OCR source.
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$casesRoot = Join-Path $projectRoot "artifacts\fintra\field_eval\cases"
$outputRoot = Join-Path $projectRoot "artifacts\fintra\field_eval"
$detectionTag = "fintra-modern-detection:torch260-cu124-mmdet330"
$recognitionTag = "fintra-modern-gpu:torch260-cu124"
$detectionCheckpoint = "/project/artifacts/aihub/runtime/transit_detection_model.pth"
$recognitionCheckpoint = "/project/artifacts/aihub/runtime/transit_recog_model.pth"
$dictionary = "/project/artifacts/aihub/runtime/unidocs_dict_transit_runtime.txt"

if (-not (Test-Path -LiteralPath $casesRoot)) {
    throw "Missing prepared cases: $casesRoot"
}
if (-not (docker image inspect $detectionTag 2>$null)) {
    throw "Missing detection image: $detectionTag"
}
if (-not (docker image inspect $recognitionTag 2>$null)) {
    throw "Missing recognition image: $recognitionTag"
}

function Invoke-DockerChecked {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed with exit code $LASTEXITCODE"
    }
}

$caseDirs = @(Get-ChildItem -LiteralPath $casesRoot -Directory | Sort-Object Name)
if ($caseDirs.Count -ne 60) {
    throw "Expected 60 prepared cases, found $($caseDirs.Count)"
}

foreach ($caseDir in $caseDirs) {
    $imageFile = @(Get-ChildItem -LiteralPath $caseDir.FullName -File | Where-Object { $_.Extension.ToLowerInvariant() -in @('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff') })
    if ($imageFile.Count -ne 1) {
        throw "Expected exactly one image in $($caseDir.FullName), found $($imageFile.Count)"
    }
    $relativeCase = $caseDir.FullName.Substring($projectRoot.Length).TrimStart('\').Replace('\', '/')
    $image = "/project/$relativeCase/$($imageFile[0].Name)"
    $detection = "/project/$relativeCase/outputs/detection.json"
    $recognitionOutput = "/project/$relativeCase/outputs/recognition"
    $detectionHost = Join-Path $caseDir.FullName "outputs\detection.json"
    New-Item -ItemType Directory -Force -Path (Join-Path $caseDir.FullName "outputs\recognition") | Out-Null

    if (Test-Path -LiteralPath $detectionHost) {
        Write-Host "[$($caseDir.Name)] Detection already present; reusing it"
    } else {
        Write-Host "[$($caseDir.Name)] Detection"
        Invoke-DockerChecked @(
            "run", "--rm", "--gpus", "all", "--ipc=host",
            "-v", "${projectRoot}:/project", "-w", "/project", $detectionTag,
            "python", "/opt/fintra/modern_detection.py",
            "--image", $image,
            "--checkpoint", $detectionCheckpoint,
            "--config", "/opt/fintra/detection_config.py",
            "--output", $detection,
            "--device", "cuda"
        )
    }

    $recognitionJson = @(Get-ChildItem -LiteralPath (Join-Path $caseDir.FullName "outputs\recognition") -Filter "*.json" -File -ErrorAction SilentlyContinue)
    if ($recognitionJson.Count -gt 0) {
        Write-Host "[$($caseDir.Name)] Recognition already present; reusing it"
    } else {
        Write-Host "[$($caseDir.Name)] Recognition"
        Invoke-DockerChecked @(
            "run", "--rm", "--gpus", "all", "--ipc=host",
            "-v", "${projectRoot}:/project", "-w", "/project", $recognitionTag,
            # Run the repository wrapper through the project mount.  The image may
            # contain an older wrapper that only accepts --baseline-txt.
            "python", "/project/runtime/modern_gpu/modern_recognition.py",
            "--image", $image,
            "--regions-json", $detection,
            "--checkpoint", $recognitionCheckpoint,
            "--dict", $dictionary,
            "--output-dir", $recognitionOutput,
            "--device", "cuda"
        )
    }
}

Write-Host "[60/60] Evaluating extracted fields"
& python (Join-Path $projectRoot "scripts\evaluate_field_extraction.py") --cases $casesRoot --output-dir $outputRoot
if ($LASTEXITCODE -ne 0) {
    throw "Field evaluation failed with exit code $LASTEXITCODE"
}
Write-Host "FIELD_EVALUATION_COMPLETE=$outputRoot"
