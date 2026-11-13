# Runs one script from this folder on the analysed decrypted exe (project DSR_dec), read-only, no analysis.
# Usage: run_script.ps1 <Script.java> <args...>
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Mandatory = $true, Position = 0)][string]$Script, [string]$Project = 'DSR_dec', [string]$Program = 'DSR_decrypted.exe',
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$ScriptArgs)
$jdk = 'C:\Users\nemos\workspace\toolsy\jdk25\jdk-25'
$env:JAVA_HOME = $jdk
$env:PATH = "$jdk\bin;$env:PATH"
$env:GHIDRA_HEADLESS_MAXMEM = '16G'
$env:JAVA_TOOL_OPTIONS = '-Duser.name=nemos'
$env:GHIDRA_HEADLESS_JAVA_OPTIONS = '-Dapplication.settingsdir=C:\Users\nemos\workspace\toolsy\ghidra_settings'
$p = "$(Split-Path (Split-Path $PSScriptRoot))\work\ghidra"
& 'C:\Users\nemos\workspace\toolsy\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat' `
    "$p\proj" $Project -process $Program -noanalysis -readOnly -scriptPath $PSScriptRoot `
    -postScript $Script @ScriptArgs 2>&1 | Select-String -Pattern 'done|zapisano|caller|ERROR|Exception'
