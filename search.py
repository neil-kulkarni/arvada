import random, sys, os, time
from score import Scorer
from input import parse_input
from parse_tree import ParseTree, ParseNode
from grammar import Grammar, Rule
from generator import GrammarGenerator
from start import build_start_grammar

def main(file_name, log_file):
    start_time = time.time() # To compute elapsed time

    # Generate configuration options and oracle grammar
    CONFIG, ORACLE_GEN, ORACLE = parse_input(file_name)
    POS_EXAMPLES, NEG_EXAMPLES = CONFIG['POS_EXAMPLES'], CONFIG['NEG_EXAMPLES']
    MAX_NEG_EXAMPLE_SIZE = CONFIG['MAX_NEG_EXAMPLE_SIZE']
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

    # Score the start grammar we arrived at earlier, which will add it to the
    # "interesting" set for future iterations
    print('Scoring initial grammars...'.ljust(50), end='\r')
    start_grammar = start_gen.generate_grammar()
    scorer = Scorer(CONFIG, DATA, start_grammar, start_gen)
    scorer.score(start_grammar, start_gen)


if __name__ == '__main__':
    if len(sys.argv) != 3 or not os.path.exists(sys.argv[1]):
        print(f'Usage: python3 {sys.argv[0]} <input_file> <log_file>')
    else:
        main(sys.argv[1], sys.argv[2])
