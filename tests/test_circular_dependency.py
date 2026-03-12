from minimake import resolve_build_order

config = {
    "targets": {
        "a": {"deps": ["b"], "command": "echo a"},
        "b": {"deps": ["a"], "command": "echo b"}
    }
}

try:
    resolve_build_order(config, "a")
    assert False, "Should have raised ValueError for circular dependency"
except ValueError as e:
    assert "Circular dependency" in str(e), "Error message should mention circular dependency"
    print("✓ Circular dependency detection works correctly")
