#!/bin/bash
set -e

rm -f hello.o hello

python ../src/minimake.py hello.o hello
test -f hello.o
test -f hello
./hello | grep -q "Hello, minimake!"
echo "✓ Multiple targets build works"
