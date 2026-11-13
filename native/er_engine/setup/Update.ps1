# ER-Inspired DSR Remake - update check (run by the launcher before every game start).
#
# Asks the GitHub API for the latest release of {REPO}. When it is newer than this package, shows a prompt;
# on "Yes" downloads the release .zip, checks it, backs up the current mod files to _backup\v<old>\ and
# replaces them. Kept: bin\er_engine.ini (user values merged into the new file), the launcher .bat,
# setup\modengine2_path.txt and the log. The game folder and Mod Engine 2 are never touched.
# Any network or GitHub error = silent skip, so the game always starts.
#
# Switch off: bin\er_engine.ini, section [Update], CheckForUpdates=0.
# Command line:
#   -Manual            also report "no update" and errors (window)
#   -Yes               no windows: answer "yes" to the prompt and print the messages (tests, automation)
#   -FromZip <zip> -Yes  install a local package without network (used by build_release.ps1)
param(
    [switch]$Manual,
    [string]$FromZip = '',
    [switch]$Yes
)
$ErrorActionPreference = 'Stop'

$ModName = 'ER-Inspired DSR Remake'
$FileBase = 'ER-Inspired_DSR_Remake'
$Version = '{VERSION}'
$Repo = '{REPO}'
$PackageDir = Split-Path -Parent $PSScriptRoot
$IniPath = Join-Path $PackageDir 'bin\er_engine.ini'
$Preserved = @('bin\er_engine.ini', 'bin\er_engine.log', 'setup\modengine2_path.txt')
$MirroredDirs = @('bin', 'files', 'setup')

function Show-Box([string]$text, [string]$buttons = 'OK', [string]$icon = 'Information') {
    if ($FromZip -or $Yes) { Write-Host $text; return 'Yes' }
    Add-Type -AssemblyName System.Windows.Forms
    $owner = New-Object System.Windows.Forms.Form
    $owner.TopMost = $true
    $owner.ShowInTaskbar = $false
    try { return [string][System.Windows.Forms.MessageBox]::Show($owner, $text, "$ModName - aktualizacja", $buttons, $icon) }
    finally { $owner.Dispose() }
}

function Get-IniValue([string]$path, [string]$section, [string]$key, [string]$default) {
    if (-not (Test-Path -LiteralPath $path)) { return $default }
    $cur = ''
    foreach ($line in [IO.File]::ReadAllLines($path)) {
        $t = $line.Trim()
        if ($t -match '^\[(.+)\]$') { $cur = $Matches[1]; continue }
        if ($cur -eq $section -and $t -match '^([^;=]+?)\s*=\s*(.*)$' -and $Matches[1] -eq $key) { return $Matches[2].Trim() }
    }
    return $default
}

# New ini text with the values the user had in the old one (same section and key). New keys keep defaults.
function Merge-Ini([string]$oldPath, [string]$newPath) {
    if (-not (Test-Path -LiteralPath $oldPath)) { return }
    $old = @{}
    $cur = ''
    foreach ($line in [IO.File]::ReadAllLines($oldPath)) {
        $t = $line.Trim()
        if ($t -match '^\[(.+)\]$') { $cur = $Matches[1]; continue }
        if ($t -match '^([^;=]+?)\s*=\s*(.*)$') { $old["$cur|$($Matches[1])"] = $Matches[2].Trim() }
    }
    $cur = ''
    $out = foreach ($line in [IO.File]::ReadAllLines($newPath)) {
        $t = $line.Trim()
        if ($t -match '^\[(.+)\]$') { $cur = $Matches[1]; $line; continue }
        if ($t -match '^([^;=]+?)\s*=' -and $old.ContainsKey("$cur|$($Matches[1])")) { "$($Matches[1])=$($old["$cur|$($Matches[1])"])"; continue }
        $line
    }
    [IO.File]::WriteAllLines($newPath, [string[]]$out)
}

function ConvertTo-Version([string]$s) {
    $v = $null
    if ([Version]::TryParse(($s.Trim() -replace '^[vV]', ''), [ref]$v)) { return $v }
    return $null
}

# --- Check -------------------------------------------------------------------------------------------
if (-not $FromZip) {
    if ((Get-IniValue $IniPath 'Update' 'CheckForUpdates' '1') -eq '0' -and -not $Manual) { exit 0 }
    $local = ConvertTo-Version $Version
    if (-not $local -or $Repo -like '{*') { exit 0 }   # development copy, placeholders not filled in
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        $headers = @{ 'User-Agent' = 'ER-Inspired-DSR-Remake-updater'; 'Accept' = 'application/vnd.github+json' }
        $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers $headers -TimeoutSec 6
    } catch {
        if ($Manual) { [void](Show-Box "Nie udało się sprawdzić aktualizacji (brak sieci albo GitHub niedostępny).`n$($_.Exception.Message)" 'OK' 'Warning') }
        exit 0
    }
    $remote = ConvertTo-Version ([string]$rel.tag_name)
    $asset = @($rel.assets | Where-Object { $_.name -like "${FileBase}_v*.zip" }) | Select-Object -First 1
    if (-not $remote -or $remote -le $local -or -not $asset) {
        if ($Manual) { [void](Show-Box "Masz najnowszą wersję ($Version).") }
        exit 0
    }
    $notes = ([string]$rel.body).Trim()
    if ($notes.Length -gt 700) { $notes = $notes.Substring(0, 700) + '...' }
    $q = "Dostępna jest nowa wersja moda: $($rel.tag_name) (masz v$Version).`n`n$notes`n`n" +
         "Pobrać i zainstalować teraz? ($([int]($asset.size / 1MB)) MB)`n" +
         "Zmieniane są tylko pliki w folderze moda; Twoje ustawienia z bin\er_engine.ini zostają, a obecna wersja trafia do _backup.`n`n" +
         "Nie = zagraj na obecnej wersji (pytanie wróci przy następnym uruchomieniu)."
    if ((Show-Box $q 'YesNo' 'Question') -ne 'Yes') { exit 0 }
}

# --- Install -----------------------------------------------------------------------------------------
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('er_remake_update_' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
$backup = ''
$copied = $false
try {
    if (Get-Process -Name DarkSoulsRemastered -ErrorAction SilentlyContinue) { throw 'Dark Souls Remastered jest uruchomiony. Zamknij grę i uruchom launcher ponownie.' }
    New-Item -ItemType Directory -Force $tmp | Out-Null
    $zip = Join-Path $tmp 'package.zip'
    if ($FromZip) {
        Copy-Item -LiteralPath $FromZip $zip
    } else {
        Write-Host "Pobieranie $($asset.name)..."
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -Headers @{ 'User-Agent' = 'ER-Inspired-DSR-Remake-updater' } -UseBasicParsing -TimeoutSec 300
        if ((Get-Item $zip).Length -ne [long]$asset.size) { throw 'Pobrany plik ma zły rozmiar (przerwane pobieranie?).' }
        if ([string]$asset.digest -match '^sha256:([0-9a-fA-F]{64})$' -and (Get-FileHash $zip -Algorithm SHA256).Hash -ne $Matches[1].ToUpper()) {
            throw 'Suma kontrolna pobranego pliku się nie zgadza.'
        }
    }
    $ex = Join-Path $tmp 'x'
    Expand-Archive -LiteralPath $zip -DestinationPath $ex
    $new = Get-ChildItem -LiteralPath $ex -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'bin\er_engine.dll') } | Select-Object -First 1
    if (-not $new -or -not (Test-Path -LiteralPath (Join-Path $new.FullName 'setup\Setup.ps1'))) { throw 'Archiwum nie wygląda na paczkę tego moda.' }
    $newDir = $new.FullName

    # Backup of the current version (only the latest backup is kept).
    $backRoot = Join-Path $PackageDir '_backup'
    if (Test-Path -LiteralPath $backRoot) { Remove-Item -LiteralPath $backRoot -Recurse -Force }
    $backup = Join-Path $backRoot "v$Version"
    New-Item -ItemType Directory -Force $backup | Out-Null
    foreach ($d in $MirroredDirs) { if (Test-Path -LiteralPath (Join-Path $PackageDir $d)) { Copy-Item -LiteralPath (Join-Path $PackageDir $d) $backup -Recurse } }
    Get-ChildItem -LiteralPath $PackageDir -File | Where-Object { $_.Name -notlike 'Launch_*.bat' } | Copy-Item -Destination $backup

    # Replace: mod-owned folders are mirrored (files gone from the new version are removed), preserved files stay.
    $copied = $true
    foreach ($d in $MirroredDirs) {
        $dst = Join-Path $PackageDir $d
        if (Test-Path -LiteralPath $dst) {
            Get-ChildItem -LiteralPath $dst -File -Recurse | ForEach-Object {
                $rel = $_.FullName.Substring($PackageDir.Length + 1)
                if ($Preserved -notcontains $rel -and -not (Test-Path -LiteralPath (Join-Path $newDir $rel))) { Remove-Item -LiteralPath $_.FullName -Force }
            }
        }
        Get-ChildItem -LiteralPath (Join-Path $newDir $d) -File -Recurse | ForEach-Object {
            $rel = $_.FullName.Substring($newDir.Length + 1)
            $target = Join-Path $PackageDir $rel
            if ($rel -eq 'bin\er_engine.ini') {
                Copy-Item -LiteralPath $_.FullName "$target.new" -Force
                Merge-Ini $target "$target.new"
                Move-Item -LiteralPath "$target.new" $target -Force
                return
            }
            if ($Preserved -contains $rel) { return }
            New-Item -ItemType Directory -Force (Split-Path -Parent $target) | Out-Null
            Copy-Item -LiteralPath $_.FullName $target -Force
        }
    }
    Get-ChildItem -LiteralPath $newDir -File | Copy-Item -Destination $PackageDir -Force
    $newVer = (Get-Content -LiteralPath (Join-Path $newDir 'setup\Update.ps1') -Raw) -replace '(?s).*?\$Version = ''([^'']+)''.*', '$1'
    [void](Show-Box "Zaktualizowano do v$newVer. Poprzednia wersja jest w folderze _backup\v$Version.`nGra uruchomi się teraz z nową wersją.")
    exit 0
} catch {
    $err = $_.Exception.Message
    if ($copied -and $backup -and (Test-Path -LiteralPath $backup)) {
        try {   # put the previous version back
            foreach ($d in $MirroredDirs) {
                $src = Join-Path $backup $d
                if (Test-Path -LiteralPath $src) { Copy-Item -LiteralPath $src $PackageDir -Recurse -Force }
            }
            Get-ChildItem -LiteralPath $backup -File | Copy-Item -Destination $PackageDir -Force
            $err += "`nPrzywrócono poprzednią wersję."
        } catch { $err += "`nNie udało się przywrócić poprzedniej wersji - skopiuj ręcznie zawartość _backup\v$Version do folderu moda." }
    }
    [void](Show-Box "Aktualizacja nie powiodła się: $err`n`nGra uruchomi się na obecnej wersji." 'OK' 'Warning')
    exit 1
} finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }
}
