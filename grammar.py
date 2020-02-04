from lark import Lark

class Grammar():
    """
    Object representing a string-representation of a context-free grammar.
    This class is intended to be used with the Lark module.
    """
    def __init__(self, terminals, nonterminals, start):
        """
        Requires that terminals be wrapped in double quotes.
        Terminals and nonterminals must be unique.
        Start must be a nonterminal.
        Rules is a mapping of rule start name to Rule object.
        """
        self.T = terminals
        self.N = nonterminals
        self.start = start

        # Add the first rule pointing a dummy start nonterminal to start
        start_rule = Rule('start')
        start_rule.add_body([start])
        self.rules = {'start':start_rule}

        # Define cacheable values and their dirty bits
        self.cached_str = ""
        self.cached_str_valid = False
        self.cached_parser = None
        self.cached_parser_valid = False

    def add_rule(self, rule_start, rule_body):
        """
        Requires the elements in rule_body to be terminals or nonterminals.
        Requires rule_start to be a nonterminal.
        """
        self.cached_str_valid = False
        self.cached_parser_valid = False

        if rule_start in self.rules:
            rule = self.rules[rule_start]
            rule.add_body(rule_body)
        else:
            rule = Rule(rule_start)
            rule.add_body(rule_body)
            self.rules[rule_start] = rule

    def parser(self):
        if self.cached_parser_valid:
            return self.cached_parser

        self.cached_parser = Lark(str(self))
        self.cached_parser_valid = True
        return self.cached_parser

    def __str__(self):
        if self.cached_str_valid:
            return self.cached_str

        self.cached_str = '\n'.join([str(rule) for rule in self.rules.values()])
        self.cached_str_valid = True
        return self.cached_str

class Rule():
    """
    Object representing the string-represenation of a rule of a CFG.
    This class is intended to be used with the Lark module.
    """
    def __init__(self, start):
        self.start = start
        self.bodies = []
        self.cached_str = ""
        self.cache_valid = False

    def add_body(self, body):
        self.cache_valid = False
        self.bodies.append(body)

    def __str__(self):
        if self.cache_valid:
            return self.cached_str

        self.cached_str = '%s: %s' % (self.start, self._body_str(self.bodies[0]))
        for i in range(1, len(self.bodies)):
            self.cached_str += '\n    | %s' % (self._body_str(self.bodies[i]))

        self.cache_valid = True
        return self.cached_str

    def _body_str(self, body):
        return ' '.join(body)

# Example grammar with nonterminals T1, T2 and terminals a, b
# grammar = Grammar(['"a"', '"b"'], ['T' + str(i) for i in range(1, 3)], 'T1')
# grammar.add_rule('T1', ['"a"', 'T2'])
# grammar.add_rule('T1', ['"b"', 'T2'])
# grammar.add_rule('T2', ['"b"'])
# parser = grammar.parser()
# print(parser.parse("ab").pretty())
