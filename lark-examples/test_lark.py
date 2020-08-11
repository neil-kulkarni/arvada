from lark import Lark
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
parser = parser_maker(l)
