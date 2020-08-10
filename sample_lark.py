from lark.load_grammar import GrammarLoader, load_grammar
from lark.grammar import *
import re
import sys

def sample_grammar(grammar_contents: str):
    grammar = load_grammar(grammar_contents, "?")
    print(grammar)
    terms, rules, ignore = grammar.compile('start')
    print(grammar.rule_defs)

    print("TERMS\n")
    print(terms)
    print("===Rules===\n", rules)
    for rule in rules:
        print(f"{rule.origin} -> {rule.expansion}")
    print(ignore)

if __name__ == "__main__":
    grammar_contents = open(sys.argv[1]).read()
    sample_grammar(grammar_contents)
