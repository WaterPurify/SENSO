# Run from the repository root, in Windows PowerShell 5.1+ or PowerShell 7.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Backup','Verify','Restore')][string]$Action,
    [Parameter(Mandatory=$true)][string]$Identity,
    [string]$Recipient,
    [string]$File,
    [string]$RestoreVolume,
    [string]$BackupDirectory = './backup'
)
$ErrorActionPreference = 'Stop'
function Docker-Run {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed (exit $LASTEXITCODE)" }
}
$repo = Split-Path $PSScriptRoot -Parent
Push-Location $repo
try {
    $identityPath = (Resolve-Path $Identity).Path
    if (!(Test-Path $identityPath -PathType Leaf)) { throw 'Identity must be a key file' }
    New-Item -ItemType Directory -Force $BackupDirectory | Out-Null
    $backupPath = (Resolve-Path $BackupDirectory).Path
    if (!$File) {
        if ($Action -ne 'Backup') { throw '-File is required' }
        $File = 'senso-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.tar.age'
    }
    if ([IO.Path]::GetFileName($File) -ne $File -or $File.Contains('..')) {
        throw '-File must be a filename inside BackupDirectory'
    }
    if ($Action -eq 'Backup' -and !$Recipient) { throw '-Recipient is required' }
    if ($Action -ne 'Backup' -and !(Test-Path (Join-Path $backupPath $File))) {
        throw 'Backup file does not exist'
    }
    Docker-Run build -f ops/Dockerfile -t senso-backup:local .
    $run = @('run','--rm','--network','none','--read-only',
        '--security-opt','no-new-privileges:true',
        '--mount',"type=bind,source=$identityPath,target=/keys/identity.txt,readonly",
        '--mount',"type=bind,source=$backupPath,target=/backup")
    if ($Action -eq 'Backup') {
        $container = @(Docker-Run compose -f compose.prod.yaml ps -aq app)
        if ($container.Count -ne 1) { throw 'Expected exactly one production app container' }
        $details = (Docker-Run inspect $container[0] | ConvertFrom-Json)[0]
        $mount = @($details.Mounts | Where-Object { $_.Destination -eq '/data' })
        if ($mount.Count -ne 1 -or $mount[0].Type -ne 'volume') {
            throw 'Expected a named data volume'
        }
        $volume = $mount[0].Name
        $wasRunning = $details.State.Running
        try {
            Docker-Run compose -f compose.prod.yaml stop -t 60 app
            $other = @(Docker-Run ps -q --filter "volume=$volume")
            if ($other.Count -gt 0) { throw 'Another running container uses the data volume' }
            Docker-Run @run --mount "type=volume,source=$volume,target=/data,readonly" `
                senso-backup:local backup --file "/backup/$File" --recipient $Recipient
        } finally {
            if ($wasRunning) { Docker-Run compose -f compose.prod.yaml start app }
        }
    } elseif ($Action -eq 'Verify') {
        Docker-Run @run senso-backup:local verify --file "/backup/$File"
    } else {
        if (!$RestoreVolume -or $RestoreVolume -notmatch '^senso-restore-[a-zA-Z0-9_-]+$') {
            throw 'Use a NEW volume name beginning with senso-restore-'
        }
        $existing = @(Docker-Run volume ls --format '{{.Name}}')
        if ($existing -contains $RestoreVolume) { throw 'Refusing to reuse an existing volume' }
        Docker-Run volume create $RestoreVolume | Out-Null
        Docker-Run @run --mount "type=volume,source=$RestoreVolume,target=/data" `
            senso-backup:local restore --file "/backup/$File"
        Write-Host "Restored to $RestoreVolume. Production is unchanged. Test before switching."
    }
} finally {
    Pop-Location
}
