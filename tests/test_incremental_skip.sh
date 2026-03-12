#!/bin/bash
set -e

rm -f hello.o hello

python ../src/minimake.py hello
test -f hello.o
test -f hello

python ../src/minimake.py hello 2>&1 | tee output.txt
grep -q "Skipping hello.o" output.txt
grep -q "Skipping hello" output.txt
rm -f output.txt
echo "✓ Incremental build skips up-to-date targets"
