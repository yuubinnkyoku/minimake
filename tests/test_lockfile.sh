#!/bin/bash
set -e

cat > build_tools.json << 'EOF'
{
  "tools": {
    "gcc": {"version": ">=9.0.0"},
    "python": {"version": ">=3.8.0"}
  },
  "targets": {}
}
EOF

python ../src/minimake.py lock --file build_tools.json

test -f build.lock

grep -q '"gcc"' build.lock
grep -q '"python"' build.lock
grep -q '"version"' build.lock

python ../src/minimake.py verify

rm -f build_tools.json build.lock
echo "OK: lockfile generation and verification works"
