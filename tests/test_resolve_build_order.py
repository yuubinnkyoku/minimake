from minimake import load_build_file, resolve_build_order

config = load_build_file("build.json")

order = resolve_build_order(config, "hello")
assert order is not None, "resolve_build_order returned None"
assert "hello.o" in order, "hello.o not in build order"
assert "hello" in order, "hello not in build order"
assert order.index("hello.o") < order.index("hello"), "hello.o should come before hello"
print("✓ resolve_build_order works correctly")
