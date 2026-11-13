# ER-Inspired DSR Remake - end-user setup (called "Konfiguracja" in the UI; it installs nothing).
#
# Locates Mod Engine 2 (automatically or through a folder picker), validates it and writes the files that
# depend on its location: the Mod Engine 2 config (.toml) and the launcher (.bat), optionally a desktop
# shortcut. Nothing is written outside the mod folder (except the optional shortcut) and the game files are
# never touched.
#
# Started by Setup.bat (double-click). Command line (no window):
#   powershell -ExecutionPolicy Bypass -File setup\Setup.ps1 -Silent -ModEngine2Path "D:\ModEngine2" [-Shortcut]
#   -Silent without -ModEngine2Path uses the first Mod Engine 2 found automatically.
#   -SelfTest builds the window without showing it (used by build_release.ps1).
param(
    [string]$ModEngine2Path = '',
    [switch]$Silent,
    [switch]$Shortcut,
    [switch]$SelfTest
)
$ErrorActionPreference = 'Stop'

$ModName = 'ER-Inspired DSR Remake'
$FileBase = 'ER-Inspired_DSR_Remake'
$Version = '{VERSION}'
$ExpectedExeSha = '{EXE_SHA256}'          # DarkSoulsRemastered.exe the DLL hooks were made for
$LauncherExe = 'modengine2_launcher.exe'
$PackageDir = Split-Path -Parent $PSScriptRoot
$TomlPath = Join-Path $PackageDir "$FileBase.toml"
$BatPath = Join-Path $PackageDir "Launch_$FileBase.bat"
$RememberPath = Join-Path $PSScriptRoot 'modengine2_path.txt'

# --- Package check -----------------------------------------------------------------------------------
function Test-Package {
    $missing = @()
    foreach ($rel in 'bin\er_engine.dll', 'bin\er_engine.ini', 'files\chr\c0000.anibnd.dcx', 'files\chr\c0000.esd.dcx') {
        if (-not (Test-Path -LiteralPath (Join-Path $PackageDir $rel))) { $missing += $rel }
    }
    if ($missing.Count) { return "W folderze moda brakuje plików: $($missing -join ', '). Rozpakuj całe archiwum jeszcze raz." }
    if (Test-Path -LiteralPath (Join-Path $PackageDir 'DarkSoulsRemastered.exe')) {
        return 'Mod jest rozpakowany w katalogu gry. Przenieś folder moda w inne miejsce (np. Dokumenty) i uruchom Setup.bat ponownie.'
    }
    return ''
}

# --- Mod Engine 2 validation -------------------------------------------------------------------------
# Returns Ok (launcher present), Dsr (this build knows Dark Souls Remastered) and a message for the user.
function Test-ModEngine2([string]$dir) {
    $r = [pscustomobject]@{ Ok = $false; Dsr = $false; Path = ''; Message = '' }
    if ([string]::IsNullOrWhiteSpace($dir)) { $r.Message = 'Wskaż folder Mod Engine 2.'; return $r }
    $dir = $dir.Trim().Trim('"')
    if ($dir -like "*$LauncherExe") { $dir = Split-Path -Parent $dir }   # the user pasted the path of the exe
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) { $r.Message = "Folder nie istnieje: $dir"; return $r }
    $dir = (Resolve-Path -LiteralPath $dir).ProviderPath.TrimEnd('\')
    $exe = Join-Path $dir $LauncherExe
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        $r.Message = "W tym folderze nie ma pliku $LauncherExe. Wskaż folder, w którym leży ten plik."
        return $r
    }
    $r.Ok = $true
    $r.Path = $dir
    $dsr = (Test-Path -LiteralPath (Join-Path $dir 'launchmod_darksoulsremastered.bat')) -or
           (Test-Path -LiteralPath (Join-Path $dir 'config_darksoulsremastered.toml'))
    if (-not $dsr) {
        try {   # older or repacked builds: look for the game name inside the launcher itself
            $bytes = [IO.File]::ReadAllBytes($exe)
            $dsr = ([Text.Encoding]::ASCII.GetString($bytes) -match 'darksoulsremastered') -or
                   ([Text.Encoding]::Unicode.GetString($bytes) -match 'darksoulsremastered')
        } catch { $dsr = $false }
    }
    $r.Dsr = $dsr
    if ($dsr) { $r.Message = "Mod Engine 2 z obsługą Dark Souls Remastered: $dir" }
    else { $r.Message = "Znaleziono Mod Engine 2, ale ta wersja wygląda na wydanie BEZ obsługi Dark Souls Remastered (brak launchmod_darksoulsremastered.bat). Mod najpewniej się nie uruchomi." }
    return $r
}

# --- Mod Engine 2 search -----------------------------------------------------------------------------
function Find-ModEngine2 {
    $found = New-Object System.Collections.Generic.List[string]
    $add = {
        param($dir)
        $t = Test-ModEngine2 $dir
        if ($t.Ok -and -not $found.Contains($t.Path)) { $found.Add($t.Path) }
    }
    # 1. Remembered from the previous run.
    if (Test-Path -LiteralPath $RememberPath) {
        try { & $add ((Get-Content -LiteralPath $RememberPath -Encoding UTF8 -TotalCount 1)) } catch {}
    }
    # 2. Next to the mod, 3. the user's folders, 4. the first levels of every fixed drive.
    $searches = New-Object System.Collections.Generic.List[object]
    $p = $PackageDir
    for ($i = 0; $i -lt 3 -and $p; $i++) { $searches.Add(@($p, 2)); $p = Split-Path -Parent $p }
    if ($env:USERPROFILE -and (Test-Path -LiteralPath $env:USERPROFILE)) {
        Get-ChildItem -LiteralPath $env:USERPROFILE -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notin 'AppData', 'Application Data' -and -not $_.Name.StartsWith('.') } |
            ForEach-Object { $searches.Add(@($_.FullName, 3)) }
    }
    try {
        [IO.DriveInfo]::GetDrives() | Where-Object { $_.DriveType -eq 'Fixed' -and $_.IsReady } | ForEach-Object {
            Get-ChildItem -LiteralPath $_.RootDirectory.FullName -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -notin 'Windows', 'ProgramData', '$Recycle.Bin', 'System Volume Information', 'Users' } |
                ForEach-Object { $searches.Add(@($_.FullName, 2)) }
        }
    } catch {}
    foreach ($s in $searches) {
        try {
            Get-ChildItem -LiteralPath $s[0] -Filter $LauncherExe -File -Recurse -Depth $s[1] -ErrorAction SilentlyContinue |
                ForEach-Object { & $add $_.DirectoryName }
        } catch {}
    }
    # Builds with Dark Souls Remastered support first.
    return @($found | Sort-Object { if ((Test-ModEngine2 $_).Dsr) { 0 } else { 1 } })
}

# --- Game version check (information only) -----------------------------------------------------------
function Get-GameExeInfo {
    try {
        $steam = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -ErrorAction Stop).SteamPath
        if (-not $steam) { return 'Nie znaleziono Steama - pominięto sprawdzenie wersji gry.' }
        $libs = @($steam)
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            Get-Content -LiteralPath $vdf | ForEach-Object {
                if ($_ -match '"path"\s+"(.+)"') { $libs += $Matches[1].Replace('\\', '\') }
            }
        }
        foreach ($lib in $libs) {
            $exe = Join-Path $lib 'steamapps\common\DARK SOULS REMASTERED\DarkSoulsRemastered.exe'
            if (Test-Path -LiteralPath $exe) {
                $sha = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
                if ($sha -eq $ExpectedExeSha) { return "Wersja gry zgodna z modem ($exe)." }
                return "UWAGA: DarkSoulsRemastered.exe ma inną wersję niż ta, dla której powstał mod. Mechaniki z DLL mogą się nie włączyć (szczegóły: bin\er_engine.log). Plik: $exe"
            }
        }
        return 'Nie znaleziono Dark Souls Remastered w bibliotekach Steama - pominięto sprawdzenie wersji gry.'
    } catch {
        return 'Nie udało się sprawdzić wersji gry (pominięto).'
    }
}

# --- Writing the mod files ---------------------------------------------------------------------------
function Write-ModFiles([string]$me2Dir, [bool]$makeShortcut) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    # Paths inside the config are relative to the config file, so the mod folder can be moved freely;
    # only the launcher .bat depends on where Mod Engine 2 is.
    $toml = @"
# $ModName v$Version - Mod Engine 2 configuration (Dark Souls Remastered).
# Generated by Setup.bat. Paths are relative to this file.
[modengine]
debug = false
external_dlls = [
    "bin/er_engine.dll",
]

[extension.mod_loader]
enabled = true
loose_params = false
mods = [
    { enabled = true, name = "er_inspired_dsr_remake", path = "files" },
]

[extension.scylla_hide]
enabled = false
"@
    [IO.File]::WriteAllText($TomlPath, $toml.Replace("`r`n", "`n").Replace("`n", "`r`n"), $utf8NoBom)

    $bat = @"
@echo off
chcp 65001 >nul
rem $ModName v$Version - launcher generated by Setup.bat. Offline play only.
rem Mod Engine 2 location (run Setup.bat again if you move it):
set "MODENGINE2=$me2Dir"
cd /d "%~dp0"
if not exist "%MODENGINE2%\$LauncherExe" (
    echo Nie znaleziono Mod Engine 2 w "%MODENGINE2%".
    echo Uruchom ponownie Setup.bat i wskaz folder Mod Engine 2.
    pause
    exit /b 1
)
rem Update check (GitHub). Switch off: bin\er_engine.ini, [Update] CheckForUpdates=0.
if exist "%~dp0setup\Update.ps1" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\Update.ps1"
"%MODENGINE2%\$LauncherExe" -t dsr -c "%~dp0$FileBase.toml"
"@
    [IO.File]::WriteAllText($BatPath, $bat.Replace("`r`n", "`n").Replace("`n", "`r`n"), $utf8NoBom)
    [IO.File]::WriteAllText($RememberPath, $me2Dir, $utf8NoBom)

    $lnk = ''
    if ($makeShortcut) {
        $desktop = [Environment]::GetFolderPath('Desktop')
        $lnk = Join-Path $desktop "$ModName.lnk"
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut($lnk)
        $sc.TargetPath = $BatPath
        $sc.WorkingDirectory = $PackageDir
        $sc.Description = "$ModName v$Version (offline)"
        $sc.Save()
    }
    return $lnk
}

# --- Silent mode -------------------------------------------------------------------------------------
if ($Silent) {
    $pkg = Test-Package
    if ($pkg) { Write-Host "BŁĄD: $pkg"; exit 1 }
    if (-not $ModEngine2Path) {
        $auto = Find-ModEngine2
        if (-not $auto.Count) { Write-Host 'BŁĄD: nie znaleziono Mod Engine 2. Podaj -ModEngine2Path.'; exit 1 }
        $ModEngine2Path = $auto[0]
    }
    $t = Test-ModEngine2 $ModEngine2Path
    Write-Host $t.Message
    if (-not $t.Ok) { exit 1 }
    $lnk = Write-ModFiles $t.Path ([bool]$Shortcut)
    Write-Host "Zapisano: $TomlPath"
    Write-Host "Zapisano: $BatPath"
    if ($lnk) { Write-Host "Skrót: $lnk" }
    Write-Host (Get-GameExeInfo)
    if (-not $t.Dsr) { exit 2 }
    exit 0
}

# --- Window ------------------------------------------------------------------------------------------
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$form = New-Object System.Windows.Forms.Form
$form.Text = "$ModName v$Version - konfiguracja"
$form.ClientSize = New-Object System.Drawing.Size(640, 372)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.Font = New-Object System.Drawing.Font('Segoe UI', 9)

$intro = New-Object System.Windows.Forms.Label
$intro.Location = New-Object System.Drawing.Point(16, 12)
$intro.Size = New-Object System.Drawing.Size(608, 68)
$intro.Text = "Ten mod wymaga programu Mod Engine 2 w wersji z obsługą Dark Souls Remastered." + [Environment]::NewLine +
    "Wskaż folder, w którym leży $LauncherExe. To narzędzie tylko zapisuje tę ścieżkę i tworzy plik uruchamiający grę z modem." + [Environment]::NewLine +
    "Niczego nie instaluje ani nie kopiuje do gry ani do Mod Engine 2. Graj wyłącznie offline."
$form.Controls.Add($intro)

$lblPath = New-Object System.Windows.Forms.Label
$lblPath.Location = New-Object System.Drawing.Point(16, 88)
$lblPath.Size = New-Object System.Drawing.Size(400, 18)
$lblPath.Text = 'Folder Mod Engine 2:'
$form.Controls.Add($lblPath)

$txtPath = New-Object System.Windows.Forms.TextBox
$txtPath.Location = New-Object System.Drawing.Point(16, 108)
$txtPath.Size = New-Object System.Drawing.Size(408, 23)
$form.Controls.Add($txtPath)

$btnBrowse = New-Object System.Windows.Forms.Button
$btnBrowse.Location = New-Object System.Drawing.Point(432, 106)
$btnBrowse.Size = New-Object System.Drawing.Size(92, 27)
$btnBrowse.Text = 'Przeglądaj...'
$form.Controls.Add($btnBrowse)

$btnFind = New-Object System.Windows.Forms.Button
$btnFind.Location = New-Object System.Drawing.Point(530, 106)
$btnFind.Size = New-Object System.Drawing.Size(94, 27)
$btnFind.Text = 'Szukaj'
$form.Controls.Add($btnFind)

$status = New-Object System.Windows.Forms.Label
$status.Location = New-Object System.Drawing.Point(16, 142)
$status.Size = New-Object System.Drawing.Size(608, 58)
$form.Controls.Add($status)

$chkShortcut = New-Object System.Windows.Forms.CheckBox
$chkShortcut.Location = New-Object System.Drawing.Point(16, 206)
$chkShortcut.Size = New-Object System.Drawing.Size(400, 22)
$chkShortcut.Text = 'Utwórz skrót na pulpicie'
$chkShortcut.Checked = $true
$form.Controls.Add($chkShortcut)

$result = New-Object System.Windows.Forms.Label
$result.Location = New-Object System.Drawing.Point(16, 236)
$result.Size = New-Object System.Drawing.Size(608, 76)
$form.Controls.Add($result)

$btnInstall = New-Object System.Windows.Forms.Button
$btnInstall.Location = New-Object System.Drawing.Point(16, 324)
$btnInstall.Size = New-Object System.Drawing.Size(150, 34)
$btnInstall.Text = 'Utwórz launcher'
$btnInstall.Enabled = $false
$form.Controls.Add($btnInstall)
$form.AcceptButton = $btnInstall

$btnPlay = New-Object System.Windows.Forms.Button
$btnPlay.Location = New-Object System.Drawing.Point(176, 324)
$btnPlay.Size = New-Object System.Drawing.Size(150, 34)
$btnPlay.Text = 'Uruchom grę z modem'
$btnPlay.Enabled = $false
$form.Controls.Add($btnPlay)

$btnClose = New-Object System.Windows.Forms.Button
$btnClose.Location = New-Object System.Drawing.Point(514, 324)
$btnClose.Size = New-Object System.Drawing.Size(110, 34)
$btnClose.Text = 'Zamknij'
$form.Controls.Add($btnClose)
$form.CancelButton = $btnClose

$green = [System.Drawing.Color]::FromArgb(0, 110, 40)
$red = [System.Drawing.Color]::FromArgb(180, 30, 30)
$amber = [System.Drawing.Color]::FromArgb(150, 95, 0)

$validate = {
    $t = Test-ModEngine2 $txtPath.Text
    $status.Text = $t.Message
    $status.ForeColor = if (-not $t.Ok) { $red } elseif ($t.Dsr) { $green } else { $amber }
    $btnInstall.Enabled = $t.Ok
}

$search = {
    $form.Cursor = [System.Windows.Forms.Cursors]::WaitCursor
    $status.ForeColor = [System.Drawing.SystemColors]::ControlText
    $status.Text = 'Szukam Mod Engine 2 na dyskach...'
    $form.Refresh()
    $found = @(Find-ModEngine2)
    $form.Cursor = [System.Windows.Forms.Cursors]::Default
    if ($found.Count) {
        $txtPath.Text = $found[0]
        & $validate
        if ($found.Count -gt 1) { $status.Text += [Environment]::NewLine + "(znaleziono $($found.Count) kopie; inną wskażesz przyciskiem Przeglądaj)" }
    } else {
        $status.ForeColor = $red
        $status.Text = 'Nie znaleziono Mod Engine 2. Pobierz go (README, sekcja Wymagania), rozpakuj i wskaż folder przyciskiem Przeglądaj.'
        $btnInstall.Enabled = $false
    }
}

$txtPath.Add_TextChanged($validate)
$btnFind.Add_Click($search)
$btnClose.Add_Click({ $form.Close() })

$btnBrowse.Add_Click({
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = "Wskaż folder Mod Engine 2 (ten, w którym leży $LauncherExe)"
    $dlg.ShowNewFolderButton = $false
    $cur = (Test-ModEngine2 $txtPath.Text).Path
    if ($cur) { $dlg.SelectedPath = $cur }
    if ($dlg.ShowDialog($form) -eq [System.Windows.Forms.DialogResult]::OK) {
        $picked = $dlg.SelectedPath
        # Accept the parent of the real folder too (e.g. the unpacked archive with one subfolder inside).
        if (-not (Test-ModEngine2 $picked).Ok) {
            $inner = Get-ChildItem -LiteralPath $picked -Filter $LauncherExe -File -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($inner) { $picked = $inner.DirectoryName }
        }
        $txtPath.Text = $picked
    }
})

$btnInstall.Add_Click({
    $t = Test-ModEngine2 $txtPath.Text
    if (-not $t.Ok) { & $validate; return }
    if (-not $t.Dsr) {
        $ans = [System.Windows.Forms.MessageBox]::Show($form,
            'Ta wersja Mod Engine 2 wygląda na wydanie bez obsługi Dark Souls Remastered. Mod najpewniej się nie uruchomi.' + [Environment]::NewLine + [Environment]::NewLine + 'Kontynuować mimo to?',
            $ModName, 'YesNo', 'Warning')
        if ($ans -ne [System.Windows.Forms.DialogResult]::Yes) { return }
    }
    try {
        $lnk = Write-ModFiles $t.Path $chkShortcut.Checked
        $result.ForeColor = $green
        $msg = "Gotowe. Grę z modem uruchamiasz plikiem Launch_$FileBase.bat"
        if ($lnk) { $msg += ' albo skrótem na pulpicie' }
        $result.Text = $msg + '.' + [Environment]::NewLine + (Get-GameExeInfo)
        $btnPlay.Enabled = $true
    } catch {
        $result.ForeColor = $red
        $result.Text = "Nie udało się zapisać plików: $($_.Exception.Message)"
    }
})

$btnPlay.Add_Click({
    if (Test-Path -LiteralPath $BatPath) {
        Start-Process -FilePath $BatPath -WorkingDirectory $PackageDir
        $form.Close()
    }
})

$pkgError = Test-Package
if ($pkgError) {
    $status.ForeColor = $red
    $status.Text = $pkgError
    $txtPath.Enabled = $false; $btnBrowse.Enabled = $false; $btnFind.Enabled = $false
} elseif ($ModEngine2Path) {
    $txtPath.Text = $ModEngine2Path
} elseif (-not $SelfTest) {
    $form.Add_Shown($search)
}

if ($SelfTest) {
    # Build check without showing the window: controls created, handlers attached, validation callable.
    $txtPath.Text = $ModEngine2Path
    & $validate
    Write-Host "SelfTest OK: controls=$($form.Controls.Count) install_enabled=$($btnInstall.Enabled) status=$($status.Text)"
    $form.Dispose()
    exit 0
}
[void]$form.ShowDialog()
$form.Dispose()
