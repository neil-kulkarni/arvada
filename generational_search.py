import random, sys, os, time
from score import Scorer
from input import parse_input
from parse_tree import ParseTree
from grammar import Grammar, Rule
from generator import GrammarGenerator

def main(file_name, log_file, max_iters):
    start_time = time.time() # To compute elapsed time

    # Generate configuration options and oracle grammar
    CONFIG, ORACLE_GEN, ORACLE = parse_input(file_name)
    POS_EXAMPLES, NEG_EXAMPLES = CONFIG['POS_EXAMPLES'], CONFIG['NEG_EXAMPLES']
    MAX_ITERS, MAX_NEG_EXAMPLE_SIZE = max_iters, CONFIG['MAX_NEG_EXAMPLE_SIZE']
    TERMINALS, MAX_TREE_DEPTH = CONFIG['TERMINALS'], CONFIG['MAX_TREE_DEPTH']

    # Generate positive examples
    oracle_parse_tree = ParseTree(ORACLE_GEN)
    positive_examples = oracle_parse_tree.sample_strings(POS_EXAMPLES, MAX_TREE_DEPTH)
    negative_examples = ORACLE.sample_negatives(NEG_EXAMPLES, TERMINALS, MAX_NEG_EXAMPLE_SIZE)
    DATA = {'positive_examples': positive_examples, 'negative_examples': negative_examples}

    # Test to make sure that the oracle at least compiles, and throws an exception if not
    try:
        OR_PARSER = ORACLE.parser()
        OR_PARSER.parse(next(iter(positive_examples)))
    except Exception as e:
        print(f"Oops! Lark couldn't parse the first positive example. Here's the error:\n {e.__str__()}\n")
        print('Fix your grammar. Exiting now.')
        exit(1)

    # Create the log file and write positive and negative examples to it
    with open(log_file, 'w+') as f:
        # Print the positive and negative examples
        print('\n\nPositive Examples:\n', file=f)
        for pos in positive_examples:
            print(pos, file=f)

        print('\n\nNegative Examples:\n', file=f)
        for neg in negative_examples:
            print(neg, file=f)

    # Generate intial grammar and score it
    gen = GrammarGenerator(CONFIG)
    grammar = gen.generate_grammar()
    scorer = Scorer(CONFIG, DATA, grammar, gen)
    scorer.score(grammar, gen)

    # Prints iteration information to the log file
    def log_results(scorer, log_file):
        f = open(log_file, 'a')

        # Print the target grammar
        print('\n\nTarget Grammar:\n{}'.format(ORACLE.__str__()), file=f)

        # Print the current score maximizing grammars
        print('\n\nScore Maximizing Grammars\n', file=f)
        for category in scorer.score_map:
            score, grammar, gen = scorer.score_map[category]
            print('Category:', category, file=f)
            print('Grammar:', file=f)
            print(grammar, file=f)
            print('Score:', score, file=f)
            print(file=f)

        # Print the total time elapsed
        print(f'\nTime elapsed: {time.time()-start_time} seconds, Iterations: {iterations}', file=f)

        # Print a delimeter for the next time information is logged
        print('\n\n==========', file=f)

    # Main Program Loop
    iterations = 0
    while iterations < MAX_ITERS:
        if iterations % 500 == 0:
            log_results(scorer, log_file)

        good_grammar, good_gen = scorer.sample_grammar()
        new_gen = good_gen.copy()
        new_gen.mutate()
        new_grammar = new_gen.generate_grammar()
        scorer.score(new_grammar, new_gen)
        print('Iters:', iterations, '\tScores:', ', '.join(['{:.2f}'.format(v[0]) for v in scorer.score_map.values()]), end='\r')
        iterations += 1

    log_results(scorer, log_file)

if __name__ == '__main__':
    if len(sys.argv) != 4 or not os.path.exists(sys.argv[1]):
        print('Usage: python3 generational_search.py <input_file> <log_file> <max_iters>')
    else:
        try:
            max_iters = int(sys.argv[3])
        except:
            print('Usage: python3 generational_search.py <input_file> <log_file> <max_iters>')
            exit()
        main(sys.argv[1], sys.argv[2], max_iters)
