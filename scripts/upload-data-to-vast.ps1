# Upload combined_dataset.csv to a running Vast instance.
param(
    [Parameter(Mandatory = $true)]
    [string]$SshHost,
    [Parameter(Mandatory = $true)]
    [int]$Port,
    [string]$User = "root",
    [string]$LocalCsv = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $LocalCsv) {
    $LocalCsv = Join-Path $Root "data\processed\combined_dataset.csv"
}
if (-not (Test-Path $LocalCsv)) {
    throw "CSV not found: $LocalCsv — run data_cleaning.ipynb first."
}

$RemoteDir = "/workspace/hybrid-ai-framework/data/processed"
Write-Host "Creating remote dir and uploading ..."
ssh -p $Port "${User}@${SshHost}" "mkdir -p $RemoteDir"
scp -P $Port $LocalCsv "${User}@${SshHost}:${RemoteDir}/combined_dataset.csv"
Write-Host "Uploaded to ${RemoteDir}/combined_dataset.csv"
