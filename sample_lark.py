from collections import defaultdict
from typing import List, Dict, Tuple, Set

from lark.load_grammar import GrammarLoader, load_grammar
from lark.grammar import *
from lark.lexer import TerminalDef
import re
import sys

import random

INFINITY = 1_000_000

class GenericRule:
    def __init__(self, start, expansion, is_terminal):
        self.start = start
        self.is_terminal = is_terminal
        self.expansion = expansion

    def __str__(self):
        return f"{self.start} -> {self.expansion}"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, GenericRule):
            return False
        return self.start == other.start and self.is_terminal == other.is_terminal and self.expansion == other.expansion

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.start, tuple(self.expansion), self.is_terminal))


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
    if lhs == 'LSQB':
        pass
    rhs = terminal.pattern.value
    ret_rules = []
    if rhs.startswith("[") and rhs.endswith("]"):
        for elem in get_range(rhs.strip("[]")):
            ret_rules.append(GenericRule(lhs, [elem], True))
    else:
        ret_rules.append(GenericRule(lhs, [rhs], True))
    return ret_rules

def get_min_expansion_depth(nt: str, all_rules: Dict[str, List[GenericRule]], nt_depths: Dict[str, int]):
    rules = all_rules[nt]
    min_depth = INFINITY
    for rule in rules:
        if rule.is_terminal:
            min_depth = 0
        else:
            expansion_depths = [nt_depths[elem] for elem in rule.expansion]
            if all([depth != INFINITY for depth in expansion_depths]):
                min_depth = min(min_depth, min(expansion_depths) + 1)
    if nt_depths[nt] > min_depth:
        nt_depths[nt] = min_depth
        return True
    else:
        return False

def get_min_expansion_depth_for_gram(all_rules: Dict[str, List[GenericRule]]):
    nt_depths = {nt: INFINITY for nt in all_rules}

    updated = True
    while updated:
        updated = False
        for nt in all_rules:
            nt_updated = get_min_expansion_depth(nt, all_rules, nt_depths)
            if nt_updated:
                updated = True

    return nt_depths

def get_min_expansion_depth_for_rule(rule: GenericRule, nt_depths: Dict[str, int]):
    if rule.is_terminal:
        return 0
    else:
        return max([nt_depths[nt] + 1 for nt in rule.expansion])

def make_generic_rule(rule: Rule) -> List[GenericRule]:
    lhs = rule.origin.name
    rhs = [elem.name for elem in rule.expansion]
    return [GenericRule(lhs, rhs, False)]

def sample_from_rules(start: str, generic_rule_map: Dict[str, GenericRule]) -> Tuple[str, Set[GenericRule]]:
    assert(start in generic_rule_map)
    chosen_expansion: GenericRule = random.choice(generic_rule_map[start])
    if chosen_expansion.is_terminal:
        return chosen_expansion.expansion[0], {chosen_expansion}
    else:
        sampled_str = ''
        rules_samples = {chosen_expansion}
        for elem in chosen_expansion.expansion:
            elem_str, elem_rules = sample_from_rules(elem, generic_rule_map)
            sampled_str += elem_str
            rules_samples.update(elem_rules)
        return sampled_str, rules_samples

def sample_minimal(start: str, generic_rules: Set[GenericRule]) -> Set[str] :
    """
    Given the grammar with start symbol `start` and rules `generic_rules`, creates
    a sample set of inputs that cover every rule in `generic_rules`. Try to minimize
    the size of each individual input.
    """
    pass


def sample_random_bound(start: str, generic_rules: Set[GenericRule]) -> Set[str] :
    """
    Given the grammar with start symbol `start` and rules `generic_rules`, samples
    random inputs until an input is found that covers every rule in `generic_rules`.
    Attempts to bound the size of each individual input
    """
    pass


def sample_random_nobound(start: str, generic_rules: Set[GenericRule]) -> Set[str] :
    """
    Given the grammar with start symbol `start` and rules `generic_rules`, samples
    random inputs until an input is found that covers every rule in `generic_rules`.
    """
    pass


def sample_grammar(grammar_contents: str):
    grammar = load_grammar(grammar_contents, "?")
    all_rules = [rdef[0] for rdef in grammar.rule_defs]
    terms, rules, ignore = grammar.compile(all_rules)
    generic_rules: List[GenericRule] = []
    for term in terms:
        print(term)
        generic_rules.extend(make_generic_terminal(term))
    for rule in rules:
        print(rule)
        generic_rules.extend(make_generic_rule(rule))
    generic_rule_map = defaultdict(list)
    for rule in generic_rules:
        generic_rule_map[rule.start].append(rule)

    generic_rules_set : Set[GenericRule] = set(generic_rules)
    sampled_rules : Set[GenericRule] = set()
    samples : Set[str] = set()
    count = 0
    while len(generic_rules_set.difference(sampled_rules)) > 0 and count < 5000:
        try:
            count += 1
            print(f"Iteration {count}, {len(sampled_rules)/len(generic_rules_set)*100}% sampled", end='\r')
            sample, rules_expanded = sample_from_rules('start', generic_rule_map)
            if len(sampled_rules.union(rules_expanded)) > len(sampled_rules):
                samples.add(sample)
                sampled_rules.update(rules_expanded)
        except RecursionError as e:
            continue

    print(f"Iteration {count}, {len(sampled_rules)*100/len(generic_rules_set)}% sampled")

    nt_depths = get_min_expansion_depth_for_gram(generic_rule_map)
    print(nt_depths)
    for rule in generic_rules_set:
        print(f"{rule} has min expansion depth {get_min_expansion_depth_for_rule(rule, nt_depths)}")

    return samples


if __name__ == "__main__":
    grammar_contents = open(sys.argv[1]).read()
    examples = sample_grammar(grammar_contents)
    for example in examples:
        pass#print(example)
