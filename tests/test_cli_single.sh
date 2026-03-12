#!/bin/bash
set -e

rm -f hello.o hello

python ../src/minimake.py hello.o
test -f hello.o
echo "✓ Single target build works"
