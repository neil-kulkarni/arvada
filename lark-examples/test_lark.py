from lark import Lark
from lark.load_grammar import load_grammar
import re

import sys

if len(sys.argv) != 2:
	print(f"Usage: {sys.argv[1]} grammar-file")
	exit(1)

def parser_maker(l):
	def parser(input):
		print(l.parse(input))
	return parser

grammar = open(sys.argv[1]).read()
l = Lark(grammar)
parsez = parser_maker(l)

gram = load_grammar(grammar, "stdin", re)
terminals, rules, ignore_tokens = gram.compile('start')
