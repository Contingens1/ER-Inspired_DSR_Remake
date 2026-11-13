"""Run WitchyBND.exe and print its output. Usage: python run_witchy.py <args...>"""
import subprocess
import sys

WITCHY = r"C:\Users\nemos\workspace\toolsy\WitchyBND-3.0.1.0-win-x64\WitchyBND.exe"

args = sys.argv[1:]
p = subprocess.run([WITCHY] + args, capture_output=True, text=True, timeout=600)
print("RC:", p.returncode)
if p.stdout:
    print("--- stdout ---")
    print(p.stdout[:20000])
if p.stderr:
    print("--- stderr ---")
    print(p.stderr[:8000])
