#!/bin/bash
set -e

rm -f hello.o hello

python ../src/minimake.py hello

sleep 1
touch hello.c

python ../src/minimake.py hello 2>&1 | tee output.txt
grep -q "Building hello.o" output.txt
rm -f output.txt
echo "✓ Incremental build rebuilds when source changes"
