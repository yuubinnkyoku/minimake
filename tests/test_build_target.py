import os
from minimake import load_build_file, build_target

config = load_build_file("build.json")

result = build_target(config, "hello.o")
assert result, "build_target returned False for hello.o"
assert os.path.exists("hello.o"), "hello.o was not created"
print("✓ build_target works correctly")
