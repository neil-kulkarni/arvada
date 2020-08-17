import re

from lark import Lark
import random

random.seed(0)

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
        self.cached_parser = None
        self.str_cache_hash = self._rule_hash()
        self.parser_cache_hash = self._rule_hash()

    def _rule_hash(self):
        return hash(tuple([(start, rule._body_hash()) for start, rule in self.rules.items()]))

    def str_cache_valid(self):
        return self.str_cache_hash == self._rule_hash()

    def parser_cache_valid(self):
        return self.parser_cache_hash == self._rule_hash()

    def add_rule(self, rule):
        if rule.start in self.rules:
            saved_rule = self.rules[rule.start]
            for rule_body in rule.bodies:
                saved_rule.add_body(rule_body)
        else:
            self.rules[rule.start] = rule

        self.cache_hash = self._rule_hash()

    def parser(self):
        if self.parser_cache_valid():
            return self.cached_parser

        self.cached_parser = Lark(str(self).replace('\u03B5', ''))
        self.parser_cache_hash = self._rule_hash()
        return self.cached_parser

    def sample_negatives(self, n, terminals, max_size):
        """
        Samples n random strings that do not belong to the grammar.
        Returns the unique subset of these.
        """
        samples = set()
        attempts = 0
        while len(samples) < n and attempts < 10*n:
            samples.add(self.generate_negative_example(terminals, max_size))
            attempts += 1
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
            return self.generate_negative_example(terminals, max_size)
        except:
            return negative_example

    def sample_positives(self, n, max_depth):
        """
        Samples n random strings that do not belong to the grammar.
        Returns the unique subset of these.
        """
        samples = set()
        attempts = 0
        while len(samples) < n and attempts < 10*n:
            attempts += 1
            try:
                sample = self.generate_positive_example(max_depth)
                if len(sample) > 300:
                    continue
                samples.add(sample)
            except RecursionError:
                continue
        return samples

    def generate_positive_example(self, max_depth, start_nonterminal='start', cur_depth=0):
        """
        Samples a random positive example from the grammar, with max_depth as much as possible.
        """
        # Helper function: gets all the nonterminals for a body
        def body_nonterminals(grammar, body):
            nonterminals = []
            for item in body:
                if item in grammar.rules:
                    nonterminals.append(item)
            return nonterminals
        bodies = self.rules[start_nonterminal].bodies
        # If we've reached the max depth, try to choose a non-recursive rule.
        if cur_depth >= max_depth:
            terminal_bodies = [body for body in bodies if len(body_nonterminals(self, body)) == 0]
            if len(terminal_bodies) > 0:
                terminal_body = terminal_bodies[random.randint(0, len(terminal_bodies)-1)]
                return "".join([elem.replace('"', '') for elem in terminal_body])
            # Otherwise... guess we'll have to try to stop later.
        body_to_expand = bodies[random.randint(0, len(bodies) -1)]
        nonterminals_to_expand = body_nonterminals(self, body_to_expand)
        expanded_body = [self.generate_positive_example(max_depth, elem, cur_depth + 1)
                                if elem in nonterminals_to_expand
                                else elem.replace('"', '')   # really just wanna non-clean up the terminals
                                for elem in body_to_expand]
        return "".join(expanded_body)

    def __str__(self):
        if self.str_cache_valid():
            return self.cached_str

        self.cached_str = '\n'.join([str(rule) for rule in self.rules.values()])
        self.str_cache_hash = self._rule_hash()
        return self.cached_str

    def pretty_print(self):

        ret = '\n'.join([rule.pretty_print() for rule in self.rules.values()])

        return ret


    def size(self):
        return sum([rule.size() for rule in self.rules.values()])

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
        self.cache_hash = 0

    def add_body(self, body):
        self.cache_valid = False
        if body not in self.bodies:
            self.bodies.append(body)
        return self

    def _cache_valid(self):
        return self.cache_hash == self._body_hash()

    def _body_hash(self):
        return hash(tuple([tuple(body) for body in self.bodies]))

    def __str__(self):
        if self._cache_valid():
            return self.cached_str

        self.cached_str = '%s: %s' % (self.start, self._body_str(self.bodies[0]))
        for i in range(1, len(self.bodies)):
            self.cached_str += '\n    | %s' % (self._body_str(self.bodies[i]))

        self.cache_hash = self._body_hash()
        return self.cached_str

    def _body_str(self, body):
        return ' '.join([b if len(b) > 0 else '\u03B5' for b in body])

    def size(self):
        return 1 + sum([len(body) for body in self.bodies])

    def pretty_print(self):

        ret = '%s: %s' % (self.start, self.pretty_body(self.bodies[0]))
        for i in range(1, len(self.bodies)):
            ret += '\n    | %s' % (self.pretty_body(self.bodies[i]))

        return ret

    def pretty_body(self, body):
        ret = ""
        built_up_terminals = ""
        is_first = True
        for child in body:
            if re.match("t[0-9]+", child):
                if not is_first:
                    ret += " "
                if len(built_up_terminals) > 0:
                    ret += '"' +built_up_terminals + '"'
                    built_up_terminals = ""
                    ret += " "
                ret += child
            elif child == '':
                if not is_first:
                    ret += " "
                ret += '\u03B5'
            else:
                built_up_terminals += child.strip('"')
            is_first = False

        if len(built_up_terminals) > 0:
            if len(ret) > 0:
                ret += " "
            if len(built_up_terminals) > 0:
                ret += '"' + built_up_terminals + '"'

        return ret



# Example grammar with nonterminals n1, n2 and terminals a, b
# grammar = Grammar('n1')
# grammar.add_rule(Rule('n1').add_body(['n2', '"a"']).add_body(['']))
# grammar.add_rule(Rule('n2').add_body(['', 'n1', '']))
# parser = grammar.parser()
# print(parser.parse("aa").pretty())
