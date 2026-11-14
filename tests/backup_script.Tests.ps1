# No Docker daemon or production data: simulate Docker responses to test recovery.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$temp = Join-Path ([IO.Path]::GetTempPath()) ('senso-ps-' + [guid]::NewGuid())
New-Item -ItemType Directory $temp | Out-Null
$identity = Join-Path $temp 'identity.txt'
Set-Content $identity 'test-placeholder-not-a-key'
$global:sensoCalls = [Collections.Generic.List[string]]::new()
$global:sensoRunning = $true
function global:docker {
    $command = $args -join ' '
    $global:sensoCalls.Add($command)
    $global:LASTEXITCODE = 0
    if ($command -match '^compose .* ps -aq app$') { 'fake-app' }
    elseif ($command -eq 'inspect fake-app') {
        @{ State = @{ Running = $global:sensoRunning }; Mounts = @(
            @{ Destination = '/data'; Type = 'volume'; Name = 'fake-data' }
        ) } | ConvertTo-Json -Depth 5 -Compress
    } elseif ($command -match '^run .* backup --file') {
        $global:LASTEXITCODE = 17  # Encryption, integrity, or disk failure.
    } elseif ($command -eq "volume ls --format {{.Name}}") {
        'senso-restore-existing'
    }
}
try {
    foreach ($running in @($true, $false)) {
        $global:sensoRunning = $running
        $global:sensoCalls.Clear()
        $failed = $false
        try {
            & "$repo/ops/backup.ps1" -Action Backup -Identity $identity `
                -Recipient 'age1test' -BackupDirectory $temp
        } catch { $failed = $true }
        if (!$failed) { throw 'Backup failure was not reported' }
        $started = @($global:sensoCalls | Where-Object { $_ -match ' start app$' }).Count -eq 1
        if ($started -ne $running) { throw 'Original running/stopped state was not preserved' }
    }
    Set-Content (Join-Path $temp 'test.age') 'test-placeholder-not-an-archive'
    $global:sensoCalls.Clear()
    $failed = $false
    try {
        & "$repo/ops/backup.ps1" -Action Restore -Identity $identity -File 'test.age' `
            -RestoreVolume 'senso-restore-existing' -BackupDirectory $temp
    } catch { $failed = $true }
    if (!$failed) { throw 'Existing restore volume was not rejected' }
    if (@($global:sensoCalls | Where-Object { $_ -match '^run ' }).Count) {
        throw 'Existing restore volume was modified'
    }
    'PASS: PowerShell restart-on-failure, stopped-state preservation, existing-volume rejection'
} finally {
    Remove-Item -Recurse -Force $temp
    Remove-Item Function:\docker
    Remove-Variable sensoCalls,sensoRunning -Scope Global
}
