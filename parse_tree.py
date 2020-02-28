class ParseTree():
    def __init__(self, gen):
        self.gen = gen
        self.root = ParseNode(gen.grammar_node.start, False, [])

    def sample_unique(self, n):
        """
        Samples n unique strings from the parse tree.
        """
        samples = set()
        while len(samples) < n:
            samples.add(self.sample_string())
        return samples

    def sample_string(self):
        self.generate_tree()
        return self.sample_string_from_node(self.root)

    def sample_string_from_node(self, parse_node):
        if parse_node.is_terminal:
            return parse_node.payload
        return ''.join([self.sample_string_from_node(child_node) for child_node in parse_node.children])

    def generate_tree(self):
        """
        Mutates the root to be the root of a tree of ParseNodes.
        If the root was already pointing at a tree of ParseNodes, clear this
        tree and generate a new tree in order to sample from the grammar.

        The tree will be a well-formed parse tree whose leaves are terminals,
        whose internal nodes are nonterminals, and whose parent-child relations
        represent productions in the grammar.
        """
        self.root.children.clear()
        return self.generate_tree_from_node(self.root)

    def generate_tree_from_node(self, parse_node):
        """
        Mutates an aribtrary parse_node to the the root of a parse tree
        """
        if parse_node.is_terminal:
            return

        # Sample a random rule (as a RuleNode) whose start is the parse_node's payload
        sampled_rule = self.sample_rule_node(parse_node.payload)

        # Let the symbols in the production of the sampled rule be children of
        # the current node in the parse tree
        for symbol_node in sampled_rule.children:
            child_parse_node = ParseNode(symbol_node.choice, symbol_node.is_terminal, [])
            parse_node.add_child(child_parse_node)

        # Recurse through each of the children to further build the parse tree
        for child_node in parse_node.children:
            self.generate_tree_from_node(child_node)

    def sample_rule_node(self, rule_start):
        """
        Takes in a string representation of a nonterminal, rule_start, and returns
        a random RuleNode starting with rule_start from the generator's grammar_node.
        """
        rules_with_start = [rule_node.lhs == rule_start for rule_node in self.gen.grammar_node.children]
        rind = random.randint(0, len(rules_with_start) - 1)
        return self.gen.grammar_node.children[rind]

class ParseNode():
    def __init__(self, payload, is_terminal, children):
        """
        Payload is a string representing either a terminal or a nonterminal.
        The boolean flag is_terminal differentiates between the two.
        Children of a ParseNode are also ParseNodes.
        """
        self.payload = payload
        self.children = children
        self.is_terminal = is_terminal

    def add_child(self, child):
        self.children.append(child)

    def is_leaf(self):
        return len(self.children) == 0
