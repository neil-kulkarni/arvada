from collections import defaultdict
from typing import List, Dict, Tuple, Set, Iterable

from lark.load_grammar import GrammarLoader, load_grammar
from lark.grammar import *
from lark.lexer import TerminalDef
import re
import sys
import antlr_utils

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
    """
    Pre-calculates a bunch of statistics about a grammar.
    """
    def __init__(self, generic_rules: Set[GenericRule]):
        self.all_rules = get_rule_map(generic_rules)
        self.derivable_nts = {nt: set() for nt in self.all_rules}
        self.nt_depths = {nt: INFINITY for nt in self.all_rules}
        self.calculate_min_expansion_depths()
        self.calculate_derivable_nts()
        self.derivation_depths = {(nt, other): INFINITY for nt in self.derivable_nts for other in self.derivable_nts[nt]}
        for nt in self.derivable_nts:
            self.derivation_depths[(nt,nt)] = 0
        self.calculate_nt_depths()

    def calculate_min_expansion_depth(self, nt: str):
        if nt == 'expr':
            pass
        rules = self.all_rules[nt]
        min_depth = INFINITY
        for rule in rules:
            if rule.is_terminal:
                min_depth = 0
            else:
                expansion_depths = [self.nt_depths[elem] for elem in rule.expansion]
                if len(expansion_depths) ==0:
                    expansion_depths = [0]
                if all([depth != INFINITY for depth in expansion_depths]):
                    min_depth = min(min_depth, max(expansion_depths) + 1)
        if self.nt_depths[nt] > min_depth:
            self.nt_depths[nt] = min_depth
            return True
        else:
            return False

    def calculate_min_expansion_depths(self):
        updated = True
        while updated:
            updated = False
            for nt in self.all_rules:
                nt_updated = self.calculate_min_expansion_depth(nt)
                if nt_updated:
                    updated = True

    def calculate_derivable_nts_single(self, nt):
        derivable_nts = set()
        for rule in self.all_rules[nt]:
            if not rule.is_terminal:
                for elem in rule.expansion:
                    if elem != nt:
                        derivable_nts.add(elem)
                    derivable_nts.update(self.derivable_nts[elem])
        if derivable_nts != self.derivable_nts[nt]:
            self.derivable_nts[nt] = derivable_nts
            return True
        else:
            return False

    def calculate_derivable_nts(self):
        updated = True
        while updated:
            updated = False
            for nt in self.all_rules:
                nt_updated = self.calculate_derivable_nts_single(nt)
                if nt_updated:
                    updated = True
        # Fixup to prevent infinite recursions
        for nt, derivables in self.derivable_nts.items():
            derivables.discard(nt)


    def calculate_nt_depths_single(self, nt):
        derivable_nts = self.derivable_nts[nt]
        depths = {nt: 0}
        for rule in self.all_rules[nt]:
            if not rule.is_terminal:
                for elem in rule.expansion:
                    if elem != nt:
                        depths[elem] = 1
                    elem_depths = self.get_derivables_and_depths(elem)
                    for deriv, depth in elem_depths.items():
                        if deriv not in depths:
                            depths[deriv] = depth + 1
                        else:
                            depths[deriv] = min(depth + 1, depths[deriv])

        if any([depths[deriv] < self.derivation_depths[(nt, deriv)] for deriv in depths]): #derivable_nts != self.derivable_nts[nt]:
            for deriv in depths:
                self.derivation_depths[(nt, deriv)] = min(depths[deriv], self.derivation_depths[(nt, deriv)])
            return True
        else:
            return False

    def calculate_nt_depths(self):
        updated = True
        while updated:
            updated = False
            for nt in self.all_rules:
                nt_updated = self.calculate_nt_depths_single(nt)
                if nt_updated:
                    updated = True

    ### Public APIs

    def get_derivables_and_depths(self, nt):
        """
        Returns a map of nonterminals derivable from `nt`, and the number of expansions necessary
        to get to each nonterminal (its depths)
        """
        if isinstance(nt, str):
            return {d:v for (nt0, d), v in self.derivation_depths.items() if nt0 == nt}
        elif isinstance(nt, GenericRule):
            rule = nt
            ret = {}
            for nt in rule.expansion:
                if nt in self.all_rules:
                    for d, v in self.get_derivables_and_depths(nt).items():
                        if d in ret:
                            ret[d] = min(ret[d], v+1)
                        else:
                            ret[d] = v + 1
            return ret
        else:
            raise NotImplementedError("ayyyyyyeeee")

    def get_min_rule_depth(self, rule: GenericRule):
        """
        Gets the minimum expansion depth (# rules til termination) for a particular rule
        """
        if rule.is_terminal:
            return 0
        else:
            if len(rule.expansion) > 0:
                return max([self.nt_depths[nt] + 1 for nt in rule.expansion])
            else: return 0

    def get_min_nt_depth(self, nt: str):
        """
        Gets the minimum expansion depth (# rules til termination) for a particular nonterminal
        """
        return self.nt_depths[nt]

    def get_derivable_nts(self, nt:str) -> Set[str]:
        """
        Gets the set of nonterminals derivable from a particular nonterminal `nt`.
        """
        return self.derivable_nts[nt]

def fixup_nts(grammar_contents) -> str:
    rule_re = re.compile("([a-zA-Z_]+)\s*:(.*)")
    to_lowercase = []
    for line in grammar_contents.split("\n"):
        if rule_re.search(line) is not None:
            m = rule_re.search(line)
            rule_start_name = m.group(1)
            if rule_start_name == rule_start_name.upper():
                to_lowercase.append(rule_start_name)
    to_lowercase.sort(reverse=True)
    for to_translate in to_lowercase:
        lower = to_translate.lower()
        grammar_contents = grammar_contents.replace(to_translate, lower)
    return grammar_contents

def get_rule_map(rules: Iterable[GenericRule]) -> Dict[str, List[GenericRule]]:
    generic_rule_map = defaultdict(list)
    for rule in rules:
        generic_rule_map[rule.start].append(rule)
    return generic_rule_map

class GenericRuleCreator:
    def __init__(self, grammar_contents):
        grammar_contents = fixup_nts(grammar_contents)
        print(grammar_contents)
        grammar = load_grammar(grammar_contents, "?")
        all_rules = [rdef[0] for rdef in grammar.rule_defs]
        terms, rules, ignore = grammar.compile(all_rules)

        self.generic_rules: List[GenericRule] = []
        for term in terms:
            self.generic_rules.extend(self.make_generic_terminal(term))
        for rule in rules:
            self.generic_rules.extend(self.make_generic_rule(rule))
        print(self.generic_rules)

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
    generic_rule_map = get_rule_map(generic_rules)
    sampled_rules: Set[GenericRule] = set()
    grammar_stats = GrammarStats(generic_rules)

    samples: Set[str] = set()

    def some_derivable_not_expanded_nt(nt: str):
        return not all([is_fully_expanded(derivable) for derivable in grammar_stats.get_derivable_nts(nt)])

    def some_derivable_not_expanded(rule: GenericRule):
        derivables = set(rule.expansion)
        for nt in rule.expansion:
            derivables.update(grammar_stats.get_derivable_nts(nt))
        return not all([is_fully_expanded(derivable) for derivable in derivables])

    def unexpanded_derivables(rule:GenericRule):
        derivables = set(rule.expansion)
        for nt in rule.expansion:
            derivables.update(grammar_stats.get_derivable_nts(nt))
        return [derivable for derivable in derivables if not is_fully_expanded(derivable)]

    def is_fully_expanded(nt: str):
        for rule in generic_rule_map[nt]:
            if rule not in sampled_rules:
                return False
        return True

    def all_fully_expanded():
        return all([is_fully_expanded(nt) for nt in generic_rule_map])

    def rule_with_min_distance_to_child(child_to_expand: str, rule_list: List[GenericRule]):
        """
        Choose a random rule in `rule_list` that has the minimal distance to expand to `child_to_expand`[-.
        """
        depth_to_child = [grammar_stats.get_derivables_and_depths(rule)[child_to_expand]
                          for rule in rule_list
                          if child_to_expand in grammar_stats.get_derivables_and_depths(rule)]
        min_expansion_depth = min(depth_to_child)
        chosen_expansion = random.choice([rule for rule in rule_list if
                                          child_to_expand in grammar_stats.get_derivables_and_depths(rule)
                                          and grammar_stats.get_derivables_and_depths(rule)[
                                              child_to_expand] == min_expansion_depth])
        return chosen_expansion

    def sample_smallest(start: str) -> Tuple[str, Set[GenericRule]]:
        """
        Samples the smallest (in terms of depth) possible expansion of `start`
        """
        minimal_expansion_depth = min([grammar_stats.get_min_rule_depth(rule) for rule in generic_rule_map[start]])
        minimal_expansions = [rule for rule in generic_rule_map[start]
                          if grammar_stats.get_min_rule_depth(rule) == minimal_expansion_depth]
        chosen_expansion = random.choice(minimal_expansions)
        if chosen_expansion.is_terminal:
            return chosen_expansion.expansion[0], {chosen_expansion}
        else:
            sampled_str = ''
            rules_samples = {chosen_expansion}
            for elem in chosen_expansion.expansion:
                elem_str, elem_rules = sample_smallest(elem)
                sampled_str += elem_str
                rules_samples.update(elem_rules)
            return sampled_str, rules_samples

    def sample_next(start: str, child_to_expand = None) -> Tuple[str, Set[GenericRule]]:
        """
        Samples the next expansion of `start`, which should exercise one yet-unexercised rule
        in the grammar. If `child_to_expand` is not null, one of the expansions of `child_to_expand`
        should be the yet-unexercised rule.
        """

        unexplored = [rule for rule in generic_rule_map[start] if rule not in sampled_rules]
        if len(unexplored) > 0:
            """
            First case: there is an expansion of `start` that has not yet been exercise. Choose
            one to exercise, and then choose all the smallest expansions for any other non-terminals.
            """
            chosen_expansion = random.choice(unexplored)
            if chosen_expansion.is_terminal:
                return chosen_expansion.expansion[0], {chosen_expansion}
            else:
                sampled_str = ''
                rules_samples = {chosen_expansion}
                for elem in chosen_expansion.expansion:
                    elem_str, elem_rules = sample_smallest(elem)
                    sampled_str += elem_str
                    rules_samples.update(elem_rules)
                return sampled_str, rules_samples

        has_unexplored_children = [rule for rule in generic_rule_map[start] if some_derivable_not_expanded(rule)]
        if len(has_unexplored_children) > 0:
            """
            Otherwise, if we are not done, then one of our expansions 
            """
            # get the rules we need to expand
            unexpanded_children = [unex for rule in has_unexplored_children for unex in unexpanded_derivables(rule)]
            # choose one to expand
            if child_to_expand is None:
                child_to_expand = random.choice(unexpanded_children)
            # Choose the next expansion based on the one with lowest depth to get to it
            chosen_expansion = rule_with_min_distance_to_child(child_to_expand, has_unexplored_children)
            # this expansion should already have been sampled, else we would have explored it earlier
            assert(chosen_expansion in sampled_rules and not chosen_expansion.is_terminal)

            # Now choose the element to expand in that expansion
            element_depths_to_child = [grammar_stats.get_derivables_and_depths(elem).get(child_to_expand, INFINITY)
                                       for elem in chosen_expansion.expansion]
            min_elem_depth_to_child = min(element_depths_to_child)
            elem_to_expand_idx = random.choice([idx for idx, elem in enumerate(chosen_expansion.expansion)
                                                if element_depths_to_child[idx] == min_elem_depth_to_child])

            # Now perform the expansion.
            sampled_str = ''
            rules_samples = {chosen_expansion}
            for idx, elem in enumerate(chosen_expansion.expansion):
                if idx == elem_to_expand_idx:
                    elem_str, elem_rules = sample_next(elem, child_to_expand)
                else:
                    elem_str, elem_rules = sample_smallest(elem)
                sampled_str += elem_str
                rules_samples.update(elem_rules)
            return sampled_str, rules_samples

        else:
            """
            Otherwise we're a totally explored start symbol, so just get the smallest thing.
            """
            return sample_smallest(start)


    #### Main body

    count = 0
    while not all_fully_expanded():
        sample, rules_expanded = sample_next('start')
        count += 1
        if len(sampled_rules.union(rules_expanded)) > len(sampled_rules):
            samples.add(sample)
            sampled_rules.update(rules_expanded)
        else:
            print(sample)
            raise NotImplementedError("Every sample_next should add a new rule...")
    return samples

def sample_n_random(start: str, generic_rules: Set[GenericRule], n) -> Set[str]:
    """
    Given the grammar with start symbol `start` and rules `generic_rules`, samples
    n random inputs.
    """
    generic_rule_map = get_rule_map(generic_rules)
    samples: Set[str] = set()
    grammar_stats = GrammarStats(generic_rules)

    def one_random_sample(start: str, bound, depth = 0) -> str:
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
            return chosen_expansion.expansion[0]
        else:
            sampled_str = ''
            for elem in chosen_expansion.expansion:
                elem_str = one_random_sample(elem, bound, depth + 1)
                sampled_str += elem_str
            return sampled_str


    last_update_count = 0
    while len(samples) < n:
        if len(samples) < n/3:
            bound = 5
        elif len(samples) < 2 * n/3:
            bound = 10
        else:
            bound = 15
        try:
            sample = one_random_sample('start', bound)
            samples.add(sample)
        except RecursionError as e:
            continue

    return samples


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


def print_stats(samples: Set[str], name: str):
    num_samples = len(samples)
    avg_len = sum([len(sample) for sample in samples])/num_samples
    max_len = max([len(sample) for sample in samples])
    print(f"{name}: {num_samples} samples of mean len {avg_len}, max len {max_len}")

def sample_grammar(grammar_contents: str):

    generic_rules = GenericRuleCreator(grammar_contents).get_rules()
    pure_random_samples = sample_random_nobound('start', generic_rules)
    print_stats(pure_random_samples, "random_nobound")
    #bounded_random_samples = sample_random_bound('start', generic_rules)
   # print_stats(bounded_random_samples, "random_bound")

    for sample in pure_random_samples:
        print("------")
        print(sample)

    minimal_samples = sample_minimal('start', generic_rules)
    print_stats(minimal_samples, "minimal")

    for sample in minimal_samples:
        print("=====")
        print(sample)

def main(folder_root, grammar_contents_name, antlr_mode):
    import os

    if "ANTLR_RUNTIME" not in os.environ:
        print("Please set ANTLR_RUNTIME to the location of the antlr runtime")
        exit(1)


    grammar_contents = ''
    grammar_contents_lines = []
    plain_name = os.path.basename(os.path.splitext(grammar_contents_name)[0])
    plain_name = plain_name.replace("-", "_")

    results_folder = os.path.join(folder_root, plain_name)

    try:
        os.mkdir(results_folder)
    except OSError as e:
        print(e)
        print(f"[!!!] Couldn't create {results_folder}. Underlying error above.")
        exit(1)

    try:
        grammar_contents = open(grammar_contents_name).read()
        grammar_contents_lines = [line.rstrip() for line in open(grammar_contents_name).readlines()]
    except IOError as e:
        print(e)
        print(f"[!!!] Couldn't open {grammar_contents_name}. Underlying error above.")
        exit(1)

    nolr_grammar_lines = []
    try:
        nolr_grammar_lines = [line.rstrip() for line in open(grammar_contents_name.replace(".lark", "_nolr.lark")).readlines()]
        print("Found a version without left recursion, using that to populate antlr parser")
    except IOError as e:
        print("Didn't find a version with left recursion removed")

    generic_rules = GenericRuleCreator(grammar_contents).get_rules()

    parse_program_contents= f"""#!/usr/bin/python3
import sys
from lark import Lark

target_grammar = \"\"\"{grammar_contents}\"\"\"

def main():
    if len(sys.argv) != 2:
        print("Usage: {sys.argv[0]} <input-file>")
        exit(1)

    in_file = sys.argv[1]
    parser = Lark(target_grammar)
    v = parser.parse(open(in_file).read().rstrip())
    exit(0)

if __name__ == '__main__':
    main()

    """

    cpp_dir = os.path.join(results_folder, "cpp-build")

    try:
        if antlr_mode:
            gram_name = "g_" + plain_name
            os.mkdir(cpp_dir)
            if nolr_grammar_lines:
                antlr_contents = antlr_utils.lark_to_antlr(gram_name, nolr_grammar_lines)
            else:
                antlr_contents = antlr_utils.lark_to_antlr(gram_name, grammar_contents_lines)
            antlr_file_name = os.path.join(cpp_dir, f"{gram_name}.g4")
            antlr_file = open(antlr_file_name, "w")
            antlr_file.write(antlr_contents)
            antlr_file.close()

            cmake_file_name = os.path.join(cpp_dir, f"CMakeLists.txt")
            cmake_file = open(cmake_file_name, "w")
            cmake_file.write(antlr_utils.cmake_contents(gram_name))
            cmake_file.close()

            parser_file_name = os.path.join(cpp_dir, f"file_parser.cpp")
            parser_file = open(parser_file_name, "w")
            parser_file.write(antlr_utils.parser_contents(gram_name, "file"))
            parser_file.close()

            # make and copy out of the cpp dir
            import subprocess
            wd = os.getcwd()
            os.chdir(cpp_dir)
            subprocess.run(["cmake", "."], check=True)
            subprocess.run(["make"], check=True)

            os.chdir(wd)
            import shutil
            shutil.copy(os.path.join(cpp_dir, "file_parser"), os.path.join(results_folder, f"parse_{plain_name}"))
        else:
            parse_program_file = open(os.path.join(results_folder, f"parse_{plain_name}"), "w")
            parse_program_file.write(parse_program_contents)
            parse_program_file.close()
    except EnvironmentError as e:
        print(e)
        print(f"[!!!] Couldn't write + compile the parser.")
        if wd is not None:
            os.chdir(wd)
        exit(1)


    guide_examples_folder = os.path.join(results_folder, "guides")
    try:
        os.mkdir(guide_examples_folder)
    except OSError as e:
        print(e)
        print(f"[!!!] Couldn't create {guide_examples_folder}. Underlying error above.")
        exit(1)

    minimal_samples = sample_minimal('start', generic_rules)
    print_stats(minimal_samples, "Guides")
    for i, minimal_sample in enumerate(minimal_samples):
        sample_name = os.path.join(guide_examples_folder, f"guide-{i}.ex")
        try:
            sample_file = open(sample_name, "w")
            sample_file.write(minimal_sample)
            sample_file.close()
        except EnvironmentError as e:
            print(e)
            print(f"[!!!] Couldn't write guide example to {sample_name}. Underlying error above.")
            exit(1)

    test_set_folder = os.path.join(results_folder, "test_set")
    try:
        os.mkdir(test_set_folder)
    except OSError as e:
        print(e)
        print(f"[!!!] Couldn't create {test_set_folder}. Underlying error above.")
        exit(1)

    test_samples = sample_n_random('start', generic_rules, 100)
    print_stats(test_samples, "Test set")

    for i, test_sample in enumerate(test_samples):
        sample_name = os.path.join(test_set_folder, f"test-{i}.ex")
        try:
            sample_file = open(sample_name, "w")
            sample_file.write(test_sample)
            sample_file.close()
        except EnvironmentError as e:
            print(e)
            print(f"[!!!] Couldn't write guide example to {sample_name}. Underlying error above.")
            exit(1)



if __name__ == "__main__":
    if len(sys.argv) == 3:
        folder_root = sys.argv[1]
        grammar_contents_name = sys.argv[2]
        main(folder_root, grammar_contents_name, True)
    else:
        grammar_contents = open(sys.argv[1]).read()
        examples = sample_grammar(grammar_contents)
