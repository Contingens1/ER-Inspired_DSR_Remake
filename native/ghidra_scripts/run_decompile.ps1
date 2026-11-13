# Dekompilacja wybranych funkcji z juz przeanalizowanego projektu (bez ponownej analizy).
# Uzycie: run_decompile.ps1 14053efb0 140547880 ...
param([string]$Project = 'DSR', [string]$Program = 'DarkSoulsRemastered.exe', [Parameter(ValueFromRemainingArguments = $true)][string[]]$Addrs)
$jdk = 'C:\Users\nemos\workspace\toolsy\jdk25\jdk-25'
$env:JAVA_HOME = $jdk
$env:PATH = "$jdk\bin;$env:PATH"
$env:GHIDRA_HEADLESS_MAXMEM = '16G'
$env:GHIDRA_HEADLESS_JAVA_OPTIONS = '-Dapplication.settingsdir=C:\Users\nemos\workspace\toolsy\ghidra_settings'
$p = "$(Split-Path (Split-Path $PSScriptRoot))\work\ghidra"
New-Item -ItemType Directory -Force "$p\decomp" | Out-Null
& 'C:\Users\nemos\workspace\toolsy\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat' `
    "$p\proj" $Project -process $Program -noanalysis -readOnly -scriptPath $PSScriptRoot `
    -postScript DecompileFuncs.java "$p\decomp" @Addrs 2>&1 | Select-String -Pattern 'zapisano|caller|brak funkcji|ERROR'

