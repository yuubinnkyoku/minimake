import os
import time
from pathlib import Path
from minimake import load_build_file, needs_rebuild

config = load_build_file("build.json")

Path("hello.o").unlink(missing_ok=True)
assert needs_rebuild(config, "hello.o"), "Should need rebuild when target doesn't exist"

Path("hello.o").touch()
time.sleep(0.1)
Path("hello.c").touch()
assert needs_rebuild(config, "hello.o"), "Should need rebuild when input is newer"

Path("hello.c").touch()
time.sleep(0.1)
Path("hello.o").touch()
assert not needs_rebuild(config, "hello.o"), "Should not need rebuild when target is newer"

Path("hello.o").unlink(missing_ok=True)
print("✓ needs_rebuild works correctly")
