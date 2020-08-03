import random
from collections import defaultdict
from typing import List

class ParseTree():

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
            rules_with_start = [rules_with_start[i] for i in range(len(rules_with_start)) if number_nonterminals[i] == min_nonterminals]

        rind = random.randint(0, len(rules_with_start) - 1)
        return rules_with_start[rind]

class ParseNode():
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

    def add_child(self, child):
        self.children.append(child)

    def is_leaf(self):
        return len(self.children) == 0

    def pretty_payload(self):
        return '  ' + (self.payload if len(self.payload) > 0 else '\u03B5') + '  '

    def copy(self):
        """
        Produces a new object that is logically equal to this ParseNode, but
        does not reference the same object.
        """
        if self.is_terminal:
            assert(len(self.children) == 0)
            return ParseNode(self.payload, True, [])
        else:
            copy_children : List[ParseNode] = [child.copy() for child in self.children]
            return ParseNode(self.payload, False, copy_children)

    def __eq__(self, other):
        if not isinstance(other, ParseNode):
            return False
        if self.payload != other.payload or self.is_terminal != other.is_terminal or len(self.children) != len(other.children):
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
        def place_in_middle(s : str, strlen : int):
            # Creates a string of length STRLEN in which s is placed in the middle
            # Assumes len(S) < STRLEN
            left_pad = (strlen - len(s)) // 2
            right_pad = (strlen - len(s) + 1) // 2
            return (' ' * left_pad) + s + (' ' * right_pad)

        if self.is_terminal:
            return self.pretty_payload()

        child_strs = [str(c) for c in self.children]
        child_str_widths = [len(c_str.split('\n')[0]) for c_str in child_strs]
        pointing_strs_left = [place_in_middle('/', w) for w in child_str_widths[:(len(self.children))//2]]
        pointing_strs_mid = [place_in_middle('|', w) for w in child_str_widths[(len(self.children))//2:(len(self.children) + 1)//2]]
        pointing_strs_right = [place_in_middle('\\', w) for w in child_str_widths[(len(self.children)+ 1)//2:]]
        pointing_str = ''.join(pointing_strs_left + pointing_strs_mid + pointing_strs_right)
        top = place_in_middle(self.pretty_payload().strip(), len(pointing_str))
        max_depth = max([len(child_str.split('\n')) for child_str in child_strs])
        pasted_children_layers = defaultdict(str)
        for child_str in child_strs:
            splits = child_str.split('\n')
            splits = splits + ([' ' * len(splits[0])] *(max_depth - len(splits)))
            for layer, line in enumerate(splits):
                pasted_children_layers[layer] += line
        pasted_children = '\n'.join([pasted_children_layers[i] for i in range(len(pasted_children_layers))])
        return '\n'.join([top, pointing_str, pasted_children])

    def __repr__(self):
        if len(self.children) == 1 and self.children[0].is_terminal:
            return self.children[0].payload
        else:
            return self.payload
