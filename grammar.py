from lark import Lark
import random

class Grammar():
    """
    Object representing a string-representation of a context-free grammar.
    This class is intended to be used with the Lark module.
    """
    def __init__(self, start):
        """
        Requires that terminals be wrapped in double quotes.
        Rules is a mapping of rule start name to Rule object.
        """
        # Add the first rule pointing a dummy start nonterminal to start
        start_rule = Rule('start')
        start_rule.add_body([start])
        self.rules = {'start':start_rule}

        # Define cacheable values and their valid bits
        self.cached_str = ""
        self.cached_str_valid = False
        self.cached_parser = None
        self.cached_parser_valid = False

    def add_rule(self, rule):
        self.cached_str_valid = False
        self.cached_parser_valid = False

        if rule.start in self.rules:
            saved_rule = self.rules[rule.start]
            for rule_body in rule.bodies:
                saved_rule.add_body(rule_body)
        else:
            self.rules[rule.start] = rule

    def parser(self):
        if self.cached_parser_valid:
            return self.cached_parser

        self.cached_parser = Lark(str(self).replace('\u03B5', ''))
        self.cached_parser_valid = True
        return self.cached_parser

    def sample_negatives(self, n, terminals, max_size):
        """
        Samples n random strings that do not belong to the grammar.
        Returns the unique subset of these.
        """
        samples = set()
        for i in range(n):
            samples.add(self.generate_negative_example(terminals, max_size))
        return samples

    def generate_negative_example(self, terminals, max_size):
        # Generate the negative example by choosing randomly from the set of terminals
        negative_example = ""
        n_chars = random.randint(1, max_size)
        for _ in range(n_chars):
            rindex = random.randint(0, len(terminals) - 1)
            negative_example += terminals[rindex]
        negative_example = negative_example.replace('"', '')

        # Check if the negative example is in the grammar. Try again if so.
        try:
            self.parser().parse(negative_example)
            return self.generate_negative_example()
        except:
            return negative_example

    def __str__(self):
        if self.cached_str_valid:
            return self.cached_str

        self.cached_str = '\n'.join([str(rule) for rule in self.rules.values()])
        self.cached_str_valid = True
        return self.cached_str

class Rule():
    """
    Object representing the string-represenation of a rule of a CFG.
    There is always an associated grammar with every rule.
    This class is intended to be used with the Lark module.
    """
    def __init__(self, start):
        """
        Start must be a nonterminal.
        Each body is a sequence of terminals and nonterminals.
        If there are multiple bodies, they will be connected via the | op.
        The epsilon terminal is represented under the hood as an empty string,
        but is displayed to the user as the epsilon character.
        """
        self.start = start
        self.bodies = []
        self.cached_str = ""
        self.cache_valid = False

    def add_body(self, body):
        self.cache_valid = False
        if body not in self.bodies:
            self.bodies.append(body)
        return self

    def __str__(self):
        if self.cache_valid:
            return self.cached_str

        self.cached_str = '%s: %s' % (self.start, self._body_str(self.bodies[0]))
        for i in range(1, len(self.bodies)):
            self.cached_str += '\n    | %s' % (self._body_str(self.bodies[i]))

        self.cache_valid = True
        return self.cached_str

    def _body_str(self, body):
        return ' '.join([b if len(b) > 0 else '\u03B5' for b in body])

# Example grammar with nonterminals n1, n2 and terminals a, b
# grammar = Grammar('n1')
# grammar.add_rule(Rule('n1').add_body(['n2', '"a"']).add_body(['']))
# grammar.add_rule(Rule('n2').add_body(['', 'n1', '']))
# parser = grammar.parser()
# print(parser.parse("aa").pretty())
