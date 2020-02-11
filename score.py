import random
from log import Log
from grammar import Grammar, Rule

class Scorer():
    """
    Keeps a map of score category to highest-scoring grammar in that category.
    Scores new grammars and updates the score map accordingly.
    Data is a hashmap of auxiliary data used for scoring functions.
    """
    def __init__(self, config, data, grammar, log):
        self.config = config
        self.data = data
        self.score_map = {'pos':(0, grammar, log), 'neg':(0, grammar, log), 'size':(0, grammar, log)}
        self.score_fns = {'pos':Scorer.pos, 'neg':Scorer.neg, 'size':Scorer.size}

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
            new_log = Log(self.config)
            new_grammar = new_log.generate_grammar()
            return new_grammar, new_log

    def score(self, grammar, log):
        """
        Scores the grammar according to each of the scoring criteria by calling
        the appropriate scoring function.
        Each scoring function is responsible for updating the score_map
        """
        for category in self.score_fns:
            self.score_fns[category](self, grammar, log)

    # SCORING FUNCTIONS
    def pos(self, grammar, log):
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
            self.score_map['pos'] = (pos_score, grammar, log)

    def neg(self, grammar, log):
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
            self.score_map['neg'] = (neg_score, grammar, log)

    def size(self, grammar, log):
        total_rule_size = 0
        for rule_start, rule in grammar.rules.items():
            for body in rule.bodies:
                total_rule_size += 1 + len(body)

        size_score = 4 / total_rule_size
        if size_score > self.score_map['size'][0]:
            self.score_map['size'] = (size_score, grammar, log)
