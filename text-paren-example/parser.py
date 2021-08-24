#!/usr/bin/python3
from lark import Lark
import sys

grammar = """
start: expr
expr: "p" expr "p"
    | expr "o" expr
    | "n"
"""

if len(sys.argv) != 2:
    print("ERROR: requires a single filename as argument", file=sys.stderr)
    exit(1)
else:
    input_contents = open(sys.argv[1]).read().rstrip()
    parser = Lark(grammar)
    parser.parse(input_contents)
