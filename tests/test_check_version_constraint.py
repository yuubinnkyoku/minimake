import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from minimake import check_version_constraint

assert check_version_constraint("11.4.0", ">=11.0.0") == True
assert check_version_constraint("10.0.0", ">=11.0.0") == False
assert check_version_constraint("11.0.0", ">=11.0.0") == True

assert check_version_constraint("3.12.0", "==3.12.0") == True
assert check_version_constraint("3.11.0", "==3.12.0") == False

print("OK: check_version_constraint works correctly")
