# Build and push the feature-extraction image (requires: docker login)
param(
    [Parameter(Mandatory = $true)]
    [string]$DockerUser,
    [string]$Tag = "cu124"
)

$ErrorActionPreference = "Stop"
$Image = "${DockerUser}/hybrid-ai-features:${Tag}"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Set-Location $Root
Write-Host "Building $Image ..."
docker build -t $Image .
Write-Host "Pushing $Image ..."
docker push $Image
Write-Host ""
Write-Host "On Vast.ai set Docker image to: $Image"
Write-Host "Expose port 8888 and mount /workspace/data for your CSV."
