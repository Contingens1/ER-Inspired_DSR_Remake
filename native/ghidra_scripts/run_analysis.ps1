# Analiza exe DSR w Ghidrze bez GUI + wyszukanie funkcji z ID animacji gracza.
# Wynik: work\ghidra\out\anim_id_refs.csv, log: work\ghidra\out\headless.log
$jdk = 'C:\Users\nemos\workspace\toolsy\jdk25\jdk-25'
$env:JAVA_HOME = $jdk
$env:PATH = "$jdk\bin;$env:PATH"
$env:GHIDRA_HEADLESS_MAXMEM = '24G'  # analyzeHeadless czyta te zmienna, nie MAXMEM
# Osobny katalog ustawien Ghidry - obejscie bledu OSGi 'data file must be inside the data dir'.
$env:GHIDRA_HEADLESS_JAVA_OPTIONS = '-Dapplication.settingsdir=C:\Users\nemos\workspace\toolsy\ghidra_settings'
$root = Split-Path (Split-Path $PSScriptRoot)
$p = "$root\work\ghidra"
New-Item -ItemType Directory -Force "$p\proj", "$p\out" | Out-Null
& 'C:\Users\nemos\workspace\toolsy\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat' `
    "$p\proj" $Project -import $Exe `
    -overwrite -scriptPath $PSScriptRoot -preScript LightAnalysis.java `
    -postScript FindAnimIdRefs.java "$p\out" -analysisTimeoutPerFile 7200 -log "$p\out\headless.log" 2>&1 |
    Select-String -Pattern 'FUNC |ERROR|JDK|REPORT'





