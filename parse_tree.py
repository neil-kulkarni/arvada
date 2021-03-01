import functools
import random
from collections import defaultdict
from typing import List, Iterable

from grammar import Rule, Grammar
from input import clean_terminal
START = 't0'

@functools.lru_cache(maxsize=None)
def fixup_terminal(payload):
    if len(payload) >= 3 and payload.startswith('"') and payload.endswith('"'):
        payload = payload[1:-1]
    return payload


class ParseTreeList:
    """
    A list of parse trees, also encapsulating the grammar induced byt the parse trees.
    Can be used just as a list but provides additional methods to check whether strings
    can be derived by the induced grammar of the list of parse trees.

    TODO: This is currently a fragile data structure as it does not automatically
    update the grammar when there are changes to the list of parse trees.
    """

    def __init__(self, start_list=None, grammar=None):
        self.inner_list = [] if start_list is None else start_list
        if self.inner_list and grammar is None:
            self.grammar = build_grammar(self.inner_list)
        elif start_list and grammar is not None:
            self.grammar = grammar
        self.derivables_from_nt = defaultdict(set)
        self.__compute_derivables()
        self.derivable_cache_hash = hash(tuple(self.inner_list))

    def __getitem__(self, item):
        return self.inner_list[item]

    def __setitem__(self, key, value):
        self.inner_list[key] = value

    def __iter__(self):
        return self.inner_list.__iter__()

    def append(self, value):
        self.inner_list.append(value)

    def represented_strings(self):
        return self.derivable_in_trees('t0')

    def derivable_in_trees(self, nt):
        if self.derivable_cache_hash != hash(tuple(self.inner_list)):
            self.__compute_derivables()
            self.derivable_cache_hash = hash(tuple(self.inner_list))
        return self.derivables_from_nt.get(nt, 0)

    def __compute_derivables(self):
        def __per_tree_helper(tree: ParseNode):
            if tree.is_terminal:
                return tree.payload
            else:
                derivable_here = "".join([__per_tree_helper(c) for c in tree.children])
                self.derivables_from_nt[tree.payload].add(derivable_here)
                return derivable_here

        for tree in self.inner_list:
            __per_tree_helper(tree)

    def represented_by_derived_grammar(self, candidates: Iterable[str]):
        """
        ASSUMES: grammar and the underlying tree list are in sync. That is,
        `self.grammar` is the induced grammar of the tree list represented
        by this object (`self.inner_list`).

        Returns true if all the strings in `candidates` are derivable in the
        grammar induced by this tree list.
        """
        candidates = set(candidates)
        represented_strings = self.represented_strings()
        if candidates.issubset(represented_strings):
            return True
        else:
            grammar_parser = self.grammar.parser()
            for candidate in candidates:
                if candidate not in represented_strings:
                    try:
                        grammar_parser.parse(candidate)
                    except Exception as e:
                        return False

        return True

    def in_my_grammar(self, candidate: str):
        """
        ASSUMES: grammar and the underlying tree list are in sync. That is,
        `self.grammar` is the induced grammar of the tree list represented
        by this object (`self.inner_list`).

        Returns true if `candidate` is derivable by the grammar induced
        by this tree list.
        """
        if candidate in self.represented_strings():
            return True
        else:
            return False
            grammar_parser = self.grammar.parser()
            try:
                grammar_parser.parse(candidate)
                return True
            except Exception as e:
                return False


class ParseTree():

    """
    A ParseTree, which wraps a ParseNode with methods to sample from the
    grammar induced by the tree.
    """
    MAX_TREE_DEPTH = 100

    def __init__(self, gen):
        self.gen = gen
        self.root = ParseNode(gen.grammar_node.start, False, [])

    def sample_strings(self, n, max_tree_depth):
        """
        Samples n random strings from the parse tree.
        Ensures the parse tree does not grow beyond max_tree_depth.
        Returns the unique subset of these and also returns the list of
        ParseNodes that each of these strings were derived from.
        """
        samples, nodes = set(), []
        for i in range(n):
            parse_list = self.sample_string(max_tree_depth)
            parse_string = ''.join([n.payload for n in parse_list])
            if parse_string not in samples:
                samples.add(parse_string)
                nodes.append(parse_list)
        return list(samples), nodes

    def sample_string(self, max_tree_depth):
        self.generate_tree(max_tree_depth)
        return self.sample_string_from_node(self.root)

    def sample_string_from_node(self, parse_node):
        if parse_node.is_terminal:
            parse_node.payload = parse_node.payload.replace('"', '')
            return [parse_node]
        return sum([self.sample_string_from_node(child_node) for child_node in parse_node.children], [])

    def generate_tree(self, max_depth):
        """
        Mutates the root to be the root of a tree of ParseNodes.
        If the root was already pointing at a tree of ParseNodes, clear this
        tree and generate a new tree in order to sample from the grammar.

        The tree will be a well-formed parse tree whose leaves are terminals,
        whose internal nodes are nonterminals, and whose parent-child relations
        represent productions in the grammar.
        """
        self.root.children.clear()
        return self.generate_tree_from_node(self.root, max_depth)

    def generate_tree_from_node(self, parse_node, max_depth, depth=0):
        """
        Mutates an aribtrary parse_node to the the root of a parse tree
        """
        if parse_node.is_terminal:
            return

        # Sample a random rule (as a RuleNode) whose start is the parse_node's payload
        sampled_rule = self.sample_rule_node(parse_node.payload, depth, max_depth)

        # Let the symbols in the production of the sampled rule be children of
        # the current node in the parse tree
        for symbol_node in sampled_rule.children:
            child_parse_node = ParseNode(symbol_node.choice, symbol_node.is_terminal, [])
            parse_node.add_child(child_parse_node)

        # Recurse through each of the children to further build the parse tree
        for child_node in parse_node.children:
            self.generate_tree_from_node(child_node, max_depth, depth + 1)

    def sample_rule_node(self, rule_start, depth, max_depth):
        """
        Takes in a string representation of a nonterminal, rule_start, and returns
        a random RuleNode starting with rule_start from the generator's grammar_node.
        If the depth exceeds the maximum possible depth, we filter the set of
        RuleNodes starting with rule_start to be the set of RuleNodes containing
        the minimum possible amount of nonterminals.
        """
        rules_with_start = [rule_node for rule_node in self.gen.grammar_node.children if rule_node.lhs == rule_start]

        if depth > max_depth:
            # Find the smallest number of nonterminals among any of the RuleNodes
            # in rules_with_start
            number_nonterminals = []
            for rule_node in rules_with_start:
                number_nonterminals.append(sum([not symbol_node.is_terminal for symbol_node in rule_node.children]))
            min_nonterminals = min(number_nonterminals)

            # Filter rules_with_start to contain only the rules that have the
            # smallest number of nonterminals
            rules_with_start = [rules_with_start[i] for i in range(len(rules_with_start)) if
                                number_nonterminals[i] == min_nonterminals]

        rind = random.randint(0, len(rules_with_start) - 1)
        return rules_with_start[rind]


class ParseNode():
    """
    A ParseNode, which represents the current state of the "trees" we are building
    up in the Arvada algorithm.
    """

    def __init__(self, payload, is_terminal, children):
        """
        Payload is a string representing either a terminal or a nonterminal.
        The boolean flag is_terminal differentiates between the two.
        Children of a ParseNode are also ParseNodes.
        The payload of the epsilon terminal is the empty string.
        """
        self.payload = payload
        self.children = children
        self.is_terminal = is_terminal
        self.cache_valid = False
        self.cached_string = None
        self.cached_nts = None

    def update_cache_info(self):
        for child in self.children:
            child.update_cache_info()
        self.cached_string = self.derived_string()
        self.cached_nts = self.all_nts()
        self.cache_valid = True

    def all_nts(self):
        if self.cache_valid:
            return self.cached_nts
        if self.is_terminal:
            return set()
        my_nts = {self.payload}
        for child in self.children:
            my_nts.update(child.all_nts())
        return my_nts

    def add_child(self, child):
        self.children.append(child)

    def is_leaf(self):
        return len(self.children) == 0

    def pretty_payload(self):
        return '  ' + (self.payload if len(self.payload) > 0 else '\u03B5') + '  '

    def derived_string(self):
        if self.cache_valid:
            return self.cached_string

        if self.is_terminal:
            return fixup_terminal(self.payload)
        else:
            return ''.join([c.derived_string() for c in self.children])

    def copy(self):
        """
        Produces a new object that is logically equal to this ParseNode, but
        does not reference the same object.
        """
        if self.is_terminal:
            assert (len(self.children) == 0)
            return ParseNode(self.payload, True, [])
        else:
            copy_children: List[ParseNode] = [child.copy() for child in self.children]
            return ParseNode(self.payload, False, copy_children)

    def __eq__(self, other):
        if not isinstance(other, ParseNode):
            return False
        if self.payload != other.payload or self.is_terminal != other.is_terminal or len(self.children) != len(
                other.children):
            return False
        for idx in range(len(self.children)):
            if not self.children[idx] == other.children[idx]:
                return False
        return True

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.payload, self.is_terminal, tuple(self.children)))

    def __str__(self):
        def place_in_middle(s: str, strlen: int):
            # Creates a string of length STRLEN in which s is placed in the middle
            # Assumes len(S) < STRLEN
            left_pad = (strlen - len(s)) // 2
            right_pad = (strlen - len(s) + 1) // 2
            return (' ' * left_pad) + s + (' ' * right_pad)

        if self.is_terminal:
            return self.pretty_payload()

        child_strs = [str(c) for c in self.children]
        child_str_widths = [len(c_str.split('\n')[0]) for c_str in child_strs]
        pointing_strs_left = [place_in_middle('/', w) for w in child_str_widths[:(len(self.children)) // 2]]
        pointing_strs_mid = [place_in_middle('|', w) for w in
                             child_str_widths[(len(self.children)) // 2:(len(self.children) + 1) // 2]]
        pointing_strs_right = [place_in_middle('\\', w) for w in child_str_widths[(len(self.children) + 1) // 2:]]
        pointing_str = ''.join(pointing_strs_left + pointing_strs_mid + pointing_strs_right)
        top = place_in_middle(self.pretty_payload().strip(), len(pointing_str))
        max_depth = max([len(child_str.split('\n')) for child_str in child_strs])
        pasted_children_layers = defaultdict(str)
        for child_str in child_strs:
            splits = child_str.split('\n')
            splits = splits + ([' ' * len(splits[0])] * (max_depth - len(splits)))
            for layer, line in enumerate(splits):
                pasted_children_layers[layer] += line
        pasted_children = '\n'.join([pasted_children_layers[i] for i in range(len(pasted_children_layers))])
        return '\n'.join([top, pointing_str, pasted_children])

    def __repr__(self):
        if len(self.children) == 1 and self.children[0].is_terminal:
            return self.children[0].payload
        else:
            return self.payload


def build_grammar(trees):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    TREES is a list of fully constructed parse trees. This method builds a
    GrammarNode that is the disjunction of the parse trees, and returns it.
    """

    def build_rules(grammar_node, parse_node, rule_map):
        """
        Adds the rules defined in PARSE_NODE and all of its subtrees to the
        GRAMMAR_NODE via recursion. RULE_MAP is used to keep track of duplicate
        rules, so they are not added multiple times to the grammar.
        """
        # Terminals and nodes with no children do not define rules
        if parse_node.is_terminal or len(parse_node.children) == 0:
            return

        # The current ParseNode defines a rule. Add this rule to the grammar.
        #        t0
        #       / | \
        #     t1  a  b
        #    / |
        #    ...
        # E.g. the ParseNode t0 defines the rule t0 -> t1 a b
        rule_body = [clean_terminal(child.payload) if child.is_terminal
                     else child.payload
                     for child in parse_node.children]
        rule = Rule(parse_node.payload)
        rule.add_body(rule_body)
        rule_str = ''.join([elem for elem in rule_body])
        if rule.start not in rule_map: rule_map[rule.start] = set()
        if rule_str not in rule_map[rule.start]:
            grammar_node.add_rule(rule)
            rule_map[rule.start].add(rule_str)

        # Recurse on the children of this ParseNode so the rule they define
        # are also added to the grammar.
        for child in parse_node.children:
            build_rules(grammar_node, child, rule_map)

    # Construct the initial grammar node without children, then fill them.
    grammar, rule_map = Grammar(START), {}
    for tree in trees:
        build_rules(grammar, tree, rule_map)
    return grammar
