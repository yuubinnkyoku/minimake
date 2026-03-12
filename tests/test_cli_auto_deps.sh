#!/bin/bash
set -e

rm -f hello.o hello

python ../src/minimake.py hello 2>&1 | tee output.txt
grep -q "Build order:" output.txt
grep -q "hello.o" output.txt
test -f hello.o
test -f hello
./hello | grep -q "Hello, minimake!"
rm -f output.txt
echo "✓ Auto dependency resolution works"
