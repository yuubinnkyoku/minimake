import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from minimake import get_tool_version

gcc_version = get_tool_version("gcc")
assert gcc_version is not None, "gcc version should not be None"
assert "." in gcc_version, f"gcc version should contain '.', got {gcc_version}"

python_version = get_tool_version("python")
assert python_version is not None, "python version should not be None"
assert "." in python_version, f"python version should contain '.', got {python_version}"

print("OK: get_tool_version works correctly")
