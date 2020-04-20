import random
from grammar import Grammar, Rule

class GrammarGenerator():
    """
    Tree-like structure to record random choices made during grammar creation.
    Used for play-back to recreate the same grammar or for mutation to recreate
    a similar, but perturbed, grammar.
    """
    def __init__(self, config, grammar_node=None):
        self.config = config
        if grammar_node is not None:
            self.grammar_node = grammar_node
        else:
            node = GrammarNode(config, None, []) # Create a dummy GrammarNode
            node.mutate_start()
            node.mutate_size()
            self.grammar_node = node

    def copy(self):
        return GrammarGenerator(self.config, self.grammar_node.copy())

    def mutate(self):
        self.grammar_node.mutate()

    def generate_grammar(self):
        grammar = Grammar(self.grammar_node.start)
        for rule_node in self.grammar_node.children:
            grammar.add_rule(self.generate_rule(rule_node))
        return grammar

    def generate_rule(self, rule_node):
        lhs = rule_node.lhs
        rhs = [symbol_node.choice for symbol_node in rule_node.children]
        return Rule(lhs).add_body(rhs)

    def get_nonterminals(self):
        nonterminals = set()
        nonterminals.add(self.grammar_node.start)
        for rule_node in self.grammar_node.children:
            nonterminals.add(rule_node.lhs)
            for symbol_node in rule_node.children:
                if not symbol_node.is_terminal:
                    nonterminals.add(symbol_node.choice)
        return nonterminals

    def get_terminals(self):
        terminals = set() # Includes the epsilon terminal
        for rule_node in self.grammar_node.children:
            for symbol_node in rule_node.children:
                if symbol_node.is_terminal:
                    terminals.add(symbol_node.choice)
        return terminals

    def __str__(self):
        return str(self.grammar_node)

class GrammarNode():
    """
    Represents the tree of choices made when determining a grammar.

    Config is a hashmap of configuration options with the following values:
        - TERMINALS : List of strings surrounded by quotes
        - NONTERMINALS = List of strings
        - NUM_RULES = Integer
        - MAX_RHS_LEN = Integer
    """
    def __init__(self, config, start, children):
        self.config = config
        self.start = start
        self.children = children

        # Definitions for ease of use
        self.max_size = config['NUM_RULES']
        self.nonterminals = config['NONTERMINALS']

    def copy(self):
        return GrammarNode(self.config, self.start, [c.copy() for c in self.children])

    def mutate(self):
        choice = random.randint(0, 2)
        if choice == 0:
            self.mutate_start()
        elif choice == 1:
            self.mutate_size()
        else:
            self.mutate_rule()

    def mutate_start(self):
        new_node = SymbolNode(self.config, None, True) # Create a dummy SymbolNode
        while new_node.is_terminal or new_node.choice == self.start:
            new_node.mutate()
        self.start = new_node.choice

    def mutate_size(self):
        old_size, new_size = self.grammar_size, random.randint(1, self.max_size)
        while new_size == old_size:
            new_size = random.randint(1, self.max_size)
        if new_size < old_size:
            # Delete old_size - new_size random rules
            for _ in range(new_size, old_size):
                random_i = random.randint(0, self.grammar_size - 1)
                self.delete_rule(random_i)
        else:
            # Add new_size - old_size random rules
            for _ in range(old_size, new_size):
                random_i = random.randint(0, self.grammar_size)
                self.add_random_rule(random_i)

    def mutate_rule(self):
        random_i = random.randint(0, self.grammar_size - 1)
        self.children[random_i].mutate()

    def delete_rule(self, i):
        self.children.pop(i)

    def add_random_rule(self, i):
        new_rule = RuleNode(self.config, None, []) # Create a dummy RuleNode
        new_rule.mutate_lhs()
        new_rule.mutate_size()
        self.children.insert(i, new_rule)

    @property
    def grammar_size(self):
        return len(self.children)

    def __str__(self):
        str_repr = 'start: %s' % (self.start)
        for child in self.children:
            str_repr += '\n%s' % (str(child))
        return str_repr

class RuleNode():
    """
    Represents the subtree of choices made about a rule.
    """
    def __init__(self, config, lhs, children):
        self.config = config
        self.lhs = lhs
        self.children = children

        # Definitions for ease of use
        self.max_size = config['MAX_RHS_LEN']
        self.nonterminals = config['NONTERMINALS']

    def copy(self):
        return RuleNode(self.config, self.lhs, [c.copy() for c in self.children])

    def mutate(self):
        choice = random.randint(0, 2)
        if choice == 0:
            self.mutate_lhs()
        elif choice == 1:
            self.mutate_size()
        else:
            self.mutate_symbol()

    def mutate_lhs(self):
        new_node = SymbolNode(self.config, None, True) # Create a dummy SymbolNode
        while new_node.is_terminal or new_node.choice == self.lhs:
            new_node.mutate()
        self.lhs = new_node.choice

    def mutate_size(self):
        old_size, new_size = self.rule_size, random.randint(1, self.max_size)
        while new_size == old_size:
            new_size = random.randint(1, self.max_size)
        if new_size < old_size:
            # Delete old_size - new_size random symbols
            for _ in range(new_size, old_size):
                random_i = random.randint(0, self.rule_size - 1)
                self.delete_symbol(random_i)
        else:
            # Add new_size - old_size random symbols
            for _ in range(old_size, new_size):
                random_i = random.randint(0, self.rule_size)
                self.add_random_symbol(random_i)

    def mutate_symbol(self):
        random_i = random.randint(0, self.rule_size - 1)
        self.children[random_i].mutate()

    def delete_symbol(self, i):
        self.children.pop(i)

    def add_random_symbol(self, i):
        new_node = SymbolNode(self.config, None, False) # Create a dummy SymbolNode
        new_node.mutate()
        self.children.insert(i, new_node)

    @property
    def rule_size(self):
        return len(self.children)

    def __str__(self):
        str_repr = '%s:' % (self.lhs)
        for child in self.children:
            str_repr += ' %s' % (str(child))
        return str_repr

class SymbolNode():
    """
    Represents a choice made for a symbol (a terminal or a nonterminal).
    The epsilon terminal is defined by a choice of ''.
    """
    def __init__(self, config, choice, is_terminal):
        self.config = config
        self.choice = choice
        self.is_terminal = is_terminal

        # Definitions for ease of use
        self.terminals = config['TERMINALS']
        self.nonterminals = config['NONTERMINALS']
        self.len_t = len(self.terminals)
        self.len_n = len(self.nonterminals)

    def copy(self):
        return SymbolNode(self.config, self.choice, self.is_terminal)

    def mutate(self):
        flip = random.randint(0, 1)
        if not flip:
            new_index = random.randint(0, self.n - 1)
            while self.choice == self.value(new_index):
                new_index = random.randint(0, self.n - 1)
            self.choice = self.value(new_index)
        else:
            self.is_terminal = not self.is_terminal
            new_index = random.randint(0, self.n - 1)
            self.choice = self.value(new_index)

    def value(self, index):
        return self.terminals[index] if self.is_terminal else self.nonterminals[index]

    @property
    def n(self):
        return self.len_t if self.is_terminal else self.len_n

    def __str__(self):
        return self.choice if len(self.choice) > 0 else '\u03B5'

# Example Configuration Options
# TERMINALS = ['"a"', '"b"']
# NONTERMINALS = ["T" + str(i) for i in range(0, 3)]
# CONFIG = {'TERMINALS':TERMINALS, 'NONTERMINALS':NONTERMINALS, 'NUM_RULES':4, 'MAX_RHS_LEN':3}
