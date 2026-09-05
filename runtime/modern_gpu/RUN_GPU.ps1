$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$imageTag = "fintra-modern-gpu:torch260-cu124"
$smokeCase = Join-Path $projectRoot "artifacts\aihub\validation\smoke\ci-01"
$dictionary = "/project/artifacts/aihub/runtime/unidocs_dict_transit_runtime.txt"
$checkpoint = "/project/artifacts/aihub/runtime/transit_recog_model.pth"

function Invoke-DockerChecked {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed with exit code $LASTEXITCODE"
    }
}

Write-Host "[1/4] Building isolated Modern runtime image..."
Invoke-DockerChecked @("build", "-t", $imageTag, "-f", (Join-Path $PSScriptRoot "Dockerfile"), $PSScriptRoot)

Write-Host "[2/4] Running CUDA/RTX4050 and Recognition smoke validation..."
$smokeOutput = "/project/artifacts/aihub/validation/smoke/ci-01/modern_recognition"
$smokeImage = "/project/artifacts/aihub/validation/smoke/ci-01/transit_train/imgs_resize/IMG_OCR_6_T_NV_000012.png"
$smokeReference = "/project/artifacts/aihub/validation/smoke/ci-01/transit_train/2023-01-22_latest_test/IMG_OCR_6_T_NV_000012.txt"
Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $imageTag, "python", "/opt/fintra/modern_recognition.py", "--image", $smokeImage, "--baseline-txt", $smokeReference, "--checkpoint", $checkpoint, "--dict", $dictionary, "--output-dir", $smokeOutput, "--device", "cuda")
Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $imageTag, "python", "/opt/fintra/compare_recognition.py", "--reference", $smokeReference, "--modern", "$smokeOutput/IMG_OCR_6_T_NV_000012.txt", "--output", "$smokeOutput/parity.json")

Write-Host "[3/4] Running Recognition over the prepared 15-document smoke set..."
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
    $reference = "/project/artifacts/aihub/validation/smoke/$caseName/transit_train/2023-01-22_latest_test/$([System.IO.Path]::GetFileNameWithoutExtension($imageName)).txt"
    $output = "/project/artifacts/aihub/validation/smoke/$caseName/modern_recognition"
    Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $imageTag, "python", "/opt/fintra/modern_recognition.py", "--image", $image, "--baseline-txt", $reference, "--checkpoint", $checkpoint, "--dict", $dictionary, "--output-dir", $output, "--device", "cuda")
    Invoke-DockerChecked @("run", "--rm", "--gpus", "all", "--ipc=host", "-v", "${projectRoot}:/project", "-w", "/project", $imageTag, "python", "/opt/fintra/compare_recognition.py", "--reference", $reference, "--modern", "$output/$([System.IO.Path]::GetFileNameWithoutExtension($imageName)).txt", "--output", "$output/parity.json")
}

Write-Host "[4/4] Detection migration is intentionally not run by this script."
Write-Host "STATUS=RECOGNITION_GPU_EXECUTED; DETECTION=NOT_STARTED"
