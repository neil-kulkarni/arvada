#!/bin/bash
# A wrapper for the `bc` utility that calls it once on an input file. Returns 0 if bc executed correctly with no syntax errors; returns 1 if there was a syntax error.

if ! [ -x "$(command -v bc)" ]; then
	echo 'Error: bc is not installed.' >&2
	exit 2
fi

filename=$1
result=$(printf "\nquit\n"| cat $filename - | bc -q 2>&1)
echo $result | grep "syntax error" >&2
exit $?
