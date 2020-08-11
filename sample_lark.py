from collections import defaultdict
from typing import List, Dict, Tuple, Set, Iterable

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

class GrammarStats:

    def __init__(self, generic_rules: List[GenericRule]):
        self.all_rules = get_rule_map(generic_rules)
        self.calculate_min_expansion_depths()

    def calculate_min_expansion_depth(self, nt: str):
        rules = self.all_rules[nt]
        min_depth = INFINITY
        for rule in rules:
            if rule.is_terminal:
                min_depth = 0
            else:
                expansion_depths = [self.nt_depths[elem] for elem in rule.expansion]
                if all([depth != INFINITY for depth in expansion_depths]):
                    min_depth = min(min_depth, min(expansion_depths) + 1)
        if self.nt_depths[nt] > min_depth:
            self.nt_depths[nt] = min_depth
            return True
        else:
            return False

    def calculate_min_expansion_depths(self):
        self.nt_depths = {nt: INFINITY for nt in self.all_rules}
        updated = True
        while updated:
            updated = False
            for nt in self.all_rules:
                nt_updated = self.calculate_min_expansion_depth(nt)
                if nt_updated:
                    updated = True


    def get_min_rule_depth(self, rule: GenericRule):
        if rule.is_terminal:
            return 0
        else:
            return max([self.nt_depths[nt] + 1 for nt in rule.expansion])

    def get_min_nt_depth(self, nt: str):
        return self.nt_depths[nt]



def get_rule_map(rules: Iterable[GenericRule]) -> Dict[str, List[GenericRule]]:
    generic_rule_map = defaultdict(list)
    for rule in rules:
        generic_rule_map[rule.start].append(rule)
    return generic_rule_map

class GenericRuleCreator:
    def __init__(self, grammar_contents):
        grammar = load_grammar(grammar_contents, "?")
        all_rules = [rdef[0] for rdef in grammar.rule_defs]
        terms, rules, ignore = grammar.compile(all_rules)
        self.generic_rules: List[GenericRule] = []
        for term in terms:
            self.generic_rules.extend(self.make_generic_terminal(term))
        for rule in rules:
            self.generic_rules.extend(self.make_generic_rule(rule))

    def get_range(self, range_str: str):
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


    def make_generic_terminal(self, terminal: TerminalDef) -> List[GenericRule]:
        lhs = terminal.name
        rhs = terminal.pattern.value
        ret_rules = []
        if rhs.startswith("[") and rhs.endswith("]"):
            for elem in self.get_range(rhs.strip("[]")):
                ret_rules.append(GenericRule(lhs, [elem], True))
        else:
            ret_rules.append(GenericRule(lhs, [rhs], True))
        return ret_rules

    def make_generic_rule(self, rule: Rule) -> List[GenericRule]:
        lhs = rule.origin.name
        rhs = [elem.name for elem in rule.expansion]
        return [GenericRule(lhs, rhs, False)]

    def get_rules(self) -> Set[GenericRule]:
        return set(self.generic_rules)


def sample_minimal(start: str, generic_rules: Set[GenericRule]) -> Set[str]:
    """
    Given the grammar with start symbol `start` and rules `generic_rules`, creates
    a sample set of inputs that cover every rule in `generic_rules`. Try to minimize
    the size of each individual input.
    """
    pass


def sample_random_bound(start: str, generic_rules: Set[GenericRule], bound=2) -> Set[str]:
    """
    Given the grammar with start symbol `start` and rules `generic_rules`, samples
    random inputs until an input is found that covers every rule in `generic_rules`.
    Attempts to bound the size of each individual input
    """
    generic_rule_map = get_rule_map(generic_rules)
    sampled_rules: Set[GenericRule] = set()
    samples: Set[str] = set()
    grammar_stats = GrammarStats(generic_rules)

    def one_random_sample(start: str, depth = 0) -> Tuple[str, Set[GenericRule]]:
        """
        Samples one random input starting at symbol `start`
        """
        assert (start in generic_rule_map)
        if depth > bound:
            minimal_expansion_depth = min([grammar_stats.get_min_rule_depth(rule) for rule in generic_rule_map[start]])
            minimal_expansions = [rule for rule in generic_rule_map[start]
                                  if grammar_stats.get_min_rule_depth(rule) == minimal_expansion_depth]
            chosen_expansion: GenericRule = random.choice(minimal_expansions)
        else:
            chosen_expansion: GenericRule = random.choice(generic_rule_map[start])
        if chosen_expansion.is_terminal:
            return chosen_expansion.expansion[0], {chosen_expansion}
        else:
            sampled_str = ''
            rules_samples = {chosen_expansion}
            for elem in chosen_expansion.expansion:
                elem_str, elem_rules = one_random_sample(elem, depth + 1)
                sampled_str += elem_str
                rules_samples.update(elem_rules)
            return sampled_str, rules_samples

    count = 0
    last_update_count = 0
    while len(generic_rules.difference(sampled_rules)) > 0 and count < 50000:
        if bound != INFINITY and count - last_update_count > 1000:
            bound = bound + 2
        try:
            count += 1
            print(f"Iteration {count}, {len(sampled_rules) / len(generic_rules) * 100}% sampled", end='\r')
            sample, rules_expanded = one_random_sample('start')
            if len(sampled_rules.union(rules_expanded)) > len(sampled_rules):
                last_update_count = count
                samples.add(sample)
                sampled_rules.update(rules_expanded)
        except RecursionError as e:
            continue

    if count == 5000:
        print(f"Failed to sample the following rules: {generic_rules.difference(sampled_rules)}")

    return samples


def sample_random_nobound(start: str, generic_rules: Set[GenericRule]) -> Set[str]:
    """
    Given the grammar with start symbol `start` and rules `generic_rules`, samples
    random inputs until an input is found that covers every rule in `generic_rules`.
    """
    return sample_random_bound(start, generic_rules, INFINITY)


def sample_grammar(grammar_contents: str):
    def print_stats(samples: Set[str], name: str):
        num_samples = len(samples)
        avg_len = sum([len(sample) for sample in samples])/num_samples
        max_len = max([len(sample) for sample in samples])
        print(f"{name}: {num_samples} samples of mean len {avg_len}, max len {max_len}")

    generic_rules = GenericRuleCreator(grammar_contents).get_rules()
    pure_random_samples = sample_random_nobound('start', generic_rules)
    print_stats(pure_random_samples, "random_nobound")
    bounded_random_samples = sample_random_bound('start', generic_rules)
    print_stats(bounded_random_samples, "random_bound")



if __name__ == "__main__":
    grammar_contents = open(sys.argv[1]).read()
    examples = sample_grammar(grammar_contents)
