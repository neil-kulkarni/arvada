import random, sys, os
from score import Scorer
from input import parse_input
from grammar import Grammar, Rule
from generator import GrammarGenerator

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
DATA = {'positive_examples':positive_examples, 'negative_examples':negative_examples}

def main(file_name, max_iters):
    # Generate configuration options and initial grammar
    CONFIG, gen, grammar = parse_input(file_name)
    MAX_ITERS = max_iters

    # Generate scorer object and score initial grammar
    scorer = Scorer(CONFIG, DATA, grammar, gen)
    scorer.score(grammar, gen)

    # Main Program Loop
    iterations = 0
    while iterations < MAX_ITERS:
        good_grammar, good_gen = scorer.sample_grammar()
        new_gen = good_gen.copy()
        new_gen.mutate()
        new_grammar = new_gen.generate_grammar()
        scorer.score(new_grammar, new_gen)
        print('Iters:', iterations, '\tScores:', [v[0] for v in scorer.score_map.values()])
        iterations += 1

    print('\n\n====== RESULTS ======\n\n')
    for category in scorer.score_map:
        score, grammar, gen = scorer.score_map[category]
        print('Category:', category)
        print('Grammar:')
        print(grammar)
        print('Score:', score)
        print()

if __name__ == '__main__':
    if len(sys.argv) != 3 or not os.path.exists(sys.argv[1]):
        print('Usage: python3 generational_search.py <input_file> <max_iters>')
    else:
        try:
            max_iters = int(sys.argv[2])
            main(sys.argv[1], max_iters)
        except:
            print('Usage: python3 generational_search.py <input_file> <max_iters>')
