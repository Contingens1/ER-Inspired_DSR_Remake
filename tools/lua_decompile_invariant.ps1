# Uruchamia DSLuaDecompiler (z pakietu Soulstruct) z kultura niezmienna - przy polskich ustawieniach
# systemu dekompilator wypisuje liczby z przecinkiem ("2,5"), czego nie da sie potem skompilowac.
# Uzycie: lua_decompile_invariant.ps1 <katalog z bajtkodem *.lua>   -> obok powstaja *.dec.lua
param([Parameter(Mandatory = $true)][string]$Dir)
$exe = Join-Path $env:APPDATA 'Python\Python315\site-packages\soulstruct\base\ai\lua\x64\DSLuaDecompiler.exe'
$inv = [Globalization.CultureInfo]::InvariantCulture
[Globalization.CultureInfo]::DefaultThreadCurrentCulture = $inv
[Threading.Thread]::CurrentThread.CurrentCulture = $inv
$asm = [Reflection.Assembly]::LoadFrom($exe)
Set-Location $Dir
[Environment]::CurrentDirectory = (Resolve-Path $Dir).Path
foreach ($f in Get-ChildItem -LiteralPath $Dir -Filter *.lua | Where-Object { $_.Name -notlike '*.dec.lua' }) {
    [Threading.Thread]::CurrentThread.CurrentCulture = $inv
    try {
        $null = $asm.EntryPoint.Invoke($null, @(, [string[]]@($f.FullName)))
    } catch {
        Write-Output "BLAD $($f.Name): $($_.Exception.InnerException.Message)"
    }
}
Write-Output "gotowe"
