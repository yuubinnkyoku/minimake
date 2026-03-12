from minimake import load_build_file

config = load_build_file("build.json")
assert config is not None, "load_build_file returned None"
assert "targets" in config, "No targets in config"
assert "hello.o" in config["targets"], "hello.o target not found"
assert "hello" in config["targets"], "hello target not found"
print("✓ load_build_file works correctly")
