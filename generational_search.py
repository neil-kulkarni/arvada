import random
from log import Log
from score import Scorer
from grammar import Grammar, Rule

# Generate positive and negative examples
# Soon, this will be replaced by an Oracle
def generate_negative_example():
    example = ""
    n_chars = random.randint(1, 10)
    for _ in range(n_chars):
        if random.randint(0, 1) == 1:
            example += "a"
        else:
            example += "b"
    if example in positive_examples:
        return generate_negative_example()
    else:
        return example

positive_examples = ['b' + 'a'*i for i in range(10)]
negative_examples = [generate_negative_example() for i in range(10)]

# Configuration Options
TERMINALS = ['"a"', '"b"']
NONTERMINALS = ["T" + str(i) for i in range(0, 3)]
CONFIG = {'TERMINALS':TERMINALS, 'NONTERMINALS':NONTERMINALS, 'NUM_RULES':4, 'MAX_RHS_LEN':3}
DATA = {'positive_examples':positive_examples, 'negative_examples':negative_examples}
MAX_ITERS = 10000

# Generate initial grammar and score it
log = Log(CONFIG)
grammar = log.generate_grammar()
scorer = Scorer(CONFIG, DATA, grammar, log)
scorer.score(grammar, log)

# Main Program Loop
iterations = 0
while iterations < MAX_ITERS:
    good_grammar, good_log = scorer.sample_grammar()
    new_log = good_log.copy()
    new_log.mutate()
    new_grammar = new_log.generate_grammar()
    scorer.score(new_grammar, new_log)
    print('Iters:', iterations, '\tScores:', [v[0] for v in scorer.score_map.values()])
    iterations += 1

print('\n\n====== RESULTS ======\n\n')
for category in scorer.score_map:
    score, grammar, log = scorer.score_map[category]
    print('Category:', category)
    print('Grammar:')
    print(grammar)
    print('Score:', score)
    print()
