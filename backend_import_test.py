# =
# backend_import_test.py
# Backend Import Health Check
# =

import sys
import os
import traceback
import datetime

# -------------------------------------------------
# UTF-8 Fix (Windows cp932 対策)
# -------------------------------------------------
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace") # type: ignore
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace") # type: ignore

# -------------------------------------------------
# Root Path Setup
# -------------------------------------------------
ROOT = os.path.abspath(".")
if ROOT not in sys.path:
    sys.path.append(ROOT)

# -------------------------------------------------
# Test Target Modules
# -------------------------------------------------
MODULES = [
    "backend",
    "backend.api",
    "backend.api.ai_server",
    "backend.api.routes_chat",
    "backend.api.routes_memory",
    "backend.api.routes_system",
    "backend.api.routes_css",
    "backend.api.routes_note",
    "backend.api.routes_project",
    "backend.api.services.chat_orchestrator",
]

# =
# Header
# =
print("=" * 51)
print("  PYTHON IMPORT TEST")
print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 51)
print(f"  ROOT : {ROOT}")
print(f"  Python : {sys.version.split()[0]}")
print("-" * 51)

# =
# Import Test
# =
results = []

for mod in MODULES:
    try:
        __import__(mod)
        results.append(("OK  ", mod, None))
        print(f"[OK  ] {mod}")
    except ImportError as e:
        results.append(("FAIL", mod, str(e)))
        print(f"[FAIL] {mod}")
        print(f"       ImportError: {e}")
    except Exception as e:
        results.append(("ERR ", mod, str(e)))
        print(f"[ERR ] {mod}")
        print(f"       {type(e).__name__}: {e}")
        traceback.print_exc()
    print()

# =
# Summary
# =
ok_count   = sum(1 for r in results if r[0] == "OK  ")
fail_count = sum(1 for r in results if r[0] != "OK  ")

print("=" * 51)
print("  SUMMARY")
print("-" * 51)
print(f"  Total   : {len(results)}")
print(f"  OK      : {ok_count}")
print(f"  FAILED  : {fail_count}")
print("-" * 51)

if fail_count > 0:
    print("  FAILED MODULES:")
    for status, mod, err in results:
        if status != "OK  ":
            print(f"    [{status}] {mod}")
            if err:
                print(f"           -> {err}")
    print()
    print("  STATUS : INCOMPLETE")
else:
    print("  STATUS : ALL IMPORTS OK")

print("=" * 51)