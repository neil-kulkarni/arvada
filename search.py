import random, sys, os, time
from score import Scorer
from input import parse_input
from parse_tree import ParseTree, ParseNode
from grammar import Grammar, Rule
from generator import GrammarGenerator
from start import build_start_grammar

def main(file_name, log_file, max_iters):
    start_time = time.time() # To compute elapsed time

    # Generate configuration options and oracle grammar
    CONFIG, ORACLE_GEN, ORACLE = parse_input(file_name)
    POS_EXAMPLES, NEG_EXAMPLES = CONFIG['POS_EXAMPLES'], CONFIG['NEG_EXAMPLES']
    MAX_ITERS, MAX_NEG_EXAMPLE_SIZE = max_iters, CONFIG['MAX_NEG_EXAMPLE_SIZE']
    TERMINALS, MAX_TREE_DEPTH = CONFIG['TERMINALS'], CONFIG['MAX_TREE_DEPTH']
    GUIDE_EXAMPLES = CONFIG['GUIDE']

    # Test to make sure that the oracle at least compiles, and throws an exception if not
    try:
        OR_PARSER = ORACLE.parser()
    except Exception as e:
        print(f"Oops! The Lark parser couldn't compile. Here's the error:\n {e.__str__()}\n")
        print('Fix your grammar. Exiting now.')
        exit(1)

    # Generate positive examples
    oracle_parse_tree = ParseTree(ORACLE_GEN)
    print('Generating positive examples...'.ljust(50), end='\r')
    positive_examples, positive_nodes = oracle_parse_tree.sample_strings(POS_EXAMPLES, MAX_TREE_DEPTH)
    print('Generating negative examples...'.ljust(50), end='\r')
    negative_examples = ORACLE.sample_negatives(NEG_EXAMPLES, TERMINALS, MAX_NEG_EXAMPLE_SIZE)
    DATA = {'positive_examples': positive_examples, 'negative_examples': negative_examples}

    # Generate guiding examples and corresponding ParseNodes
    guide_nodes = [[ParseNode(tok, True, []) for tok in ex.split()] for ex in GUIDE_EXAMPLES]
    if len(guide_nodes) == 0: guide_nodes = positive_nodes

    # Create the log file and write positive and negative examples to it
    # Also write the initial starting grammar to the file
    with open(log_file, 'w+') as f:
        # Print the positive and negative examples
        print('\n\nPositive Examples:\n', file=f)
        for pos in positive_examples:
            print(pos, file=f)

        print('\n\nNegative Examples:\n', file=f)
        for neg in negative_examples:
            print(neg, file=f)

        # Build the starting grammars and test them for compilation
        print('Building the starting grammar...'.ljust(50), end='\r')
        start_gen = build_start_grammar(OR_PARSER, CONFIG, DATA, guide_nodes)
        try:
            start_gen.generate_grammar().parser()
            print('\n\nInitial Grammar Created:\n%s' % str(start_gen.generate_grammar()), file=f)
        except Exception as e:
            print('\n\nInitial grammar does not compile! %s' % str(e), file=f)
            exit()

    # Generate random intial grammar and score it. Then, score the start grammar
    # we arrived at earlier, which will add it to the "interesting" set for
    # future iterations. Then, sample many more random grammars so that overall
    # variance is reduced.
    print('Scoring initial grammars...'.ljust(50), end='\r')
    gen = GrammarGenerator(CONFIG)
    grammar = gen.generate_grammar()
    scorer = Scorer(CONFIG, DATA, grammar, gen)
    scorer.score(grammar, gen)

    start_grammar = start_gen.generate_grammar()
    scorer.score(start_grammar, start_gen)

    for _ in range(len(positive_examples)):
        gen = GrammarGenerator(CONFIG)
        grammar = gen.generate_grammar()
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
        print(f'\nTime elapsed: %.2f seconds, Iterations: %d' % (time.time()-start_time, iterations), file=f)

        # Print a delimeter for the next time information is logged
        print('\n\n==========', file=f)

    # Main Program Loop
    print(''.ljust(50), end='\r')
    iterations = 0
    while iterations < MAX_ITERS:
        if iterations % 500 == 0:
            log_results(scorer, log_file)

        good_grammar, good_gen = scorer.sample_grammar()
        gen = good_gen.copy()
        gen.mutate()
        grammar = gen.generate_grammar()
        scorer.score(grammar, gen)
        print('Iters:', iterations, '\tScores:', ', '.join(['{:.2f}'.format(v[0]) for v in scorer.score_map.values()]), end='\r')
        iterations += 1

    # Print final results to the log
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
