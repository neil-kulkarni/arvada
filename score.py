import random
from graph import Graph
from grammar import Grammar, Rule
from generator import GrammarGenerator

class Scorer():
    """
    Keeps a map of score category to highest-scoring grammar in that category.
    Scores new grammars and updates the score map accordingly.
    Data is a hashmap of auxiliary data used for scoring functions.
    """
    def __init__(self, config, data, grammar, gen):
        self.config = config
        self.data = data
        self.score_map = {'pos':(0, grammar, gen), 'neg':(0, grammar, gen), 'size':(0, grammar, gen), 'ratio':(0, grammar, gen), 'variance':(0, grammar, gen), 'compilation':(0, grammar, gen), 'recur_cc':(0, grammar, gen), 'finite':(0, grammar, gen)}
        self.score_fns = {'pos':Scorer.pos, 'neg':Scorer.neg, 'size':Scorer.size, 'ratio':Scorer.ratio, 'variance':Scorer.variance, 'compilation':Scorer.compilation, 'recur_cc':Scorer.recur_cc, 'finite':Scorer.finite}

    def sample_grammar(self):
        """
        From the list of 'good' grammars that maximize some score, choose one
        With some nonzero probability, generates a random grammar to return
        """
        good_grammars = list(self.score_map.values())
        random_i = random.randint(0, len(good_grammars))
        if random_i < len(good_grammars):
            return good_grammars[random_i][1:]
        else:
            new_gen = GrammarGenerator(self.config)
            new_grammar = new_gen.generate_grammar()
            return new_grammar, new_gen

    def score(self, grammar, gen):
        """
        Scores the grammar according to each of the scoring criteria by calling
        the appropriate scoring function.
        Each scoring function is responsible for updating the score_map
        """
        for category in self.score_fns:
            self.score_fns[category](self, grammar, gen)

    # SCORING FUNCTIONS
    def pos(self, grammar, gen):
        try:
            parser = grammar.parser()
        except:
            return 0

        positive_examples, positive_correct = self.data['positive_examples'], 0
        for positive_example in positive_examples:
            try:
                parser.parse(positive_example)
                positive_correct += 1
            except:
                pass

        pos_score = positive_correct / len(positive_examples)
        if pos_score > self.score_map['pos'][0]:
            self.score_map['pos'] = (pos_score, grammar, gen)

    def neg(self, grammar, gen):
        try:
            parser = grammar.parser()
        except:
            return 0

        negative_examples, negative_correct = self.data['negative_examples'], 0
        for negative_example in negative_examples:
            try:
                parser.parse(negative_example)
                negative_correct += 1
            except:
                pass

        neg_score = 1 - (negative_correct / len(negative_examples))
        if neg_score > self.score_map['neg'][0]:
            self.score_map['neg'] = (neg_score, grammar, gen)

    def size(self, grammar, gen):
        total_rule_size = 0
        for rule_start, rule in grammar.rules.items():
            for body in rule.bodies:
                total_rule_size += 1 + len(body)

        size_score = 4 / total_rule_size
        if size_score > self.score_map['size'][0]:
            self.score_map['size'] = (size_score, grammar, gen)

    def ratio(self, grammar, gen):
        num_t, num_n = 0, 0
        for rule_node in gen.grammar_node.children:
            for symbol_node in rule_node.children:
                if symbol_node.is_terminal:
                    num_t += 1
                else:
                    num_n += 1

        ratio_score = 1 - 2 * abs(num_n / (num_n + num_t) - 1/2)
        if ratio_score > self.score_map['ratio'][0]:
            self.score_map['ratio'] = (ratio_score, grammar, gen)

    def variance(self, grammar, gen):
        max_terminals = len(self.config['TERMINALS'])
        max_nonterminals = len(self.config['NONTERMINALS'])

        seen_terminals, seen_nonterminals = set(), set()
        for rule_node in gen.grammar_node.children:
            for symbol_node in rule_node.children:
                if symbol_node.is_terminal:
                    seen_terminals.add(symbol_node.choice)
                else:
                    seen_nonterminals.add(symbol_node.choice)
        num_t, num_n = len(seen_terminals), len(seen_nonterminals)
        t_variance, n_variance = num_t / max_terminals, num_n / max_nonterminals

        variance_score = t_variance * n_variance
        if variance_score > self.score_map['variance'][0]:
            self.score_map['variance'] = (variance_score, grammar, gen)

    def compilation(self, grammar, gen):
        try:
            parser = grammar.parser()
            compilation_score = 1.0
        except:
            compilation_score = 0.0

        if compilation_score > self.score_map['compilation'][0]:
            self.score_map['compilation'] = (compilation_score, grammar, gen)

    def recur_cc(self, grammar, gen):
        nonterminals = gen.config['NONTERMINALS']
        graph = Graph(['start'] + list(nonterminals))
        for rule_start, rule in grammar.rules.items():
            for rule_body in rule.bodies:
                for elem in rule_body:
                    if elem in nonterminals:
                        graph.add_edge(rule_start, elem)

        recur_cc_score = 1.0 if graph.is_connected() and graph.has_cycle() else 0.0
        if recur_cc_score > self.score_map['recur_cc'][0]:
            self.score_map['recur_cc'] = (recur_cc_score, grammar, gen)

    def finite(self, grammar, gen):
        nonterminals = gen.config['NONTERMINALS']
        X = set() # The set of all nonterminals that can expand to a finite string
        updated = True # Stop looping when there are no more updates

        # Adds rule.start to X if rule.start can expand to a finite string
        # Returns True if there was an update to X
        def update(X, rule):
            # Adds rule_start to X if rule_start can expand to a finite string
            # in this particular rule_body
            # Returns True if there was an update to X via this rule_body
            def update_helper(X, rule_start, rule_body):
                if rule_start in X:
                    return False
                for elem in rule_body:
                    if elem in nonterminals and elem not in X:
                        return False
                X.add(rule_start)
                return True

            if rule.start in X:
                return False
            return any([update_helper(X, rule.start, rule_body) for rule_body in rule.bodies])

        while updated:
            updated = any([update(X, rule) for rule_start, rule in grammar.rules.items()])

        finite_score = 1.0 if len(X) == len(nonterminals) + 1 else 0.0 # Include 'start'
        if finite_score > self.score_map['finite'][0]:
            self.score_map['finite'] = (finite_score, grammar, gen)
