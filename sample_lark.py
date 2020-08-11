from typing import List

from lark.load_grammar import GrammarLoader, load_grammar
from lark.grammar import *
from lark.lexer import TerminalDef
import re
import sys

class GenericRule:
    def __init__(self, start, expansion, is_terminal):
        self.start = start
        self.is_terminal = is_terminal
        self.expansion = expansion

    def __str__(self):
        return f"{self.start} -> {self.expansion}"

    def __repr__(self):
        return self.__str__()

def get_range(range_str: str):
    ranges = []
    is_first = True
    cur_range = [None, None]
    for char in range_str:
        if is_first:
            cur_range[0] = char
            is_first = False
        elif char == '-':
            continue
        else:
            cur_range[1] = char
            ranges.append(tuple(cur_range))
            is_first = True
    char_range = []
    for rng in ranges:
            char_range.extend([chr(ordinal) for ordinal in range(ord(rng[0]), ord(rng[1]) + 1)])
    return char_range

def make_generic_terminal(terminal: TerminalDef) -> List[GenericRule]:
    lhs = terminal.name
    rhs = terminal.pattern.value
    ret_rules = []
    if rhs.startswith("["):
        for elem in get_range(rhs.strip("[]")):
            ret_rules.append(GenericRule(lhs, [elem], True))
    else:
        ret_rules.append(GenericRule(lhs, [rhs], True))
    return ret_rules

def make_generic_rule(rule: Rule) -> List[GenericRule]:
    lhs = rule.origin.name
    rhs = [elem.name for elem in rule.expansion]
    return [GenericRule(lhs, rhs, False)]

def sample_grammar(grammar_contents: str):
    grammar = load_grammar(grammar_contents, "?")
    terms, rules, ignore = grammar.compile('start')
    generic_rules : List[GenericRule] = []
    for term in terms:
        generic_rules.extend(make_generic_terminal(term))
    for rule in rules:
        generic_rules.extend(make_generic_rule(rule))
    print("GENERIC RULES==================")
    for rule in generic_rules:
        print(rule)

if __name__ == "__main__":
    grammar_contents = open(sys.argv[1]).read()
    sample_grammar(grammar_contents)
