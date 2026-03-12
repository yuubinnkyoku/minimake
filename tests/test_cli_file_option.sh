#!/bin/bash
set -e

cat > custom.json << 'EOF'
{
  "targets": {
    "test.txt": {
      "command": "echo 'test' > test.txt"
    }
  }
}
EOF

python ../src/minimake.py --file custom.json test.txt
test -f test.txt
grep -q "test" test.txt
rm -f custom.json test.txt
echo "✓ --file option works"
