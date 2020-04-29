import random, sys, os
import time
from score import Scorer
from input import parse_input
from parse_tree import ParseTree
from grammar import Grammar, Rule
from generator import GrammarGenerator

def fancy_positive_sampling(oracle_parse_tree, POS_EXAMPLES, MAX_TREE_DEPTH):
    positive_examples = []
    MIN_DEPTH=2
    num_steps = len(list(range(MIN_DEPTH, MAX_TREE_DEPTH)))
    buckets = 2 * num_steps
    num_per_bucket = POS_EXAMPLES // buckets
    extra = POS_EXAMPLES - num_per_bucket * buckets
    mid = (MAX_TREE_DEPTH -1 + MIN_DEPTH)/2
    for i in range(MIN_DEPTH, MAX_TREE_DEPTH):
        if i == MIN_DEPTH:
            positive_examples.extend(oracle_parse_tree.sample_strings(num_per_bucket * 3 + extra, i))
        elif i < mid:
            positive_examples.extend(oracle_parse_tree.sample_strings(num_per_bucket * 3, i))
        elif i > mid:
            positive_examples.extend(oracle_parse_tree.sample_strings(num_per_bucket, i))
        elif i == mid:
            positive_examples.extend(oracle_parse_tree.sample_strings(num_per_bucket * 2, i))
    return positive_examples


def main(file_name, log_file, max_iters):
    start_time = time.time()
    # Generate configuration options and oracle grammar
    CONFIG, ORACLE_GEN, ORACLE = parse_input(file_name)
    POS_EXAMPLES, NEG_EXAMPLES = CONFIG['POS_EXAMPLES'], CONFIG['NEG_EXAMPLES']
    MAX_ITERS, MAX_NEG_EXAMPLE_SIZE = max_iters, CONFIG['MAX_NEG_EXAMPLE_SIZE']
    TERMINALS, MAX_TREE_DEPTH = CONFIG['TERMINALS'], CONFIG['MAX_TREE_DEPTH']

    # Generate positive examples
    oracle_parse_tree = ParseTree(ORACLE_GEN)
    positive_examples = oracle_parse_tree.sample_strings(POS_EXAMPLES, MAX_TREE_DEPTH)

    try:
        # Test to make sure at least the oracle runs
        OR_PARSER = ORACLE.parser()
        OR_PARSER.parse(next(iter(positive_examples))) # Throws an exception if lark fails
    except Exception as e:
        print(f"Oops! Lark couldn't parse the first positive example. Here's the error:\n {e.__str__()}\n")
        print("Fix your grammar. Exiting now.")
        exit(1)

    negative_examples = ORACLE.sample_negatives(NEG_EXAMPLES, TERMINALS, MAX_NEG_EXAMPLE_SIZE)
    DATA = {'positive_examples': positive_examples, 'negative_examples': negative_examples}

    # Generate intial grammar and score it
    gen = GrammarGenerator(CONFIG)
    grammar = gen.generate_grammar()
    scorer = Scorer(CONFIG, DATA, grammar, gen)
    scorer.score(grammar, gen)

    def print_results(logfile):
        f = open(logfile, "w")
        print("Positive Examples:", file=f)
        for pos in positive_examples:
            print(pos, file=f)
        print("Negative Examples:", file=f)
        for neg in negative_examples:
            print(neg, file=f)
        print("Target grammar:\n{}\n".format(ORACLE.__str__()), file=f)
        print('\n\n====== RESULTS ======\n\n', file=f)
        for category in scorer.score_map:
            score, grammar, gen = scorer.score_map[category]
            print('Category:', category, file=f)
            print('Grammar:', file=f)
            print(grammar, file=f)
            print('Score:', score, file=f)
            print(file=f)
        print(f"Time elapsed: {time.time()-start_time} seconds, Iterations: {iterations}", file=f)

    # Main Program Loop
    iterations = 0
    while iterations < MAX_ITERS:
        if iterations % 500 == 0:
            print_results(log_file)
        good_grammar, good_gen = scorer.sample_grammar()
        new_gen = good_gen.copy()
        new_gen.mutate()
        new_grammar = new_gen.generate_grammar()
        scorer.score(new_grammar, new_gen)
        print('Iters:', iterations, '\tScores:', ", ".join(["{:.2f}".format(v[0]) for v in scorer.score_map.values()]), end='\r')
        iterations += 1

    print_results(log_file)

if __name__ == '__main__':
    if len(sys.argv) != 4 or not os.path.exists(sys.argv[1]):
        print('Usage: python3 generational_search.py <input_file> <log_file> <max_iters>')
    else:
        try:
            log_file = sys.argv[2]
            max_iters = int(sys.argv[3])
        except:
            print('Usage: python3 generational_search.py <input_file> <log_file> <max_iters>')
            exit()
        main(sys.argv[1], log_file, max_iters)
