import random, sys, os, time
from input import parse_input
from parse_tree import ParseTree, ParseNode
from grammar import Grammar, Rule
from start import build_start_grammar
from lark import Lark

def main(file_name, log_file):
    start_time = time.time() # To compute elapsed time

    # Generate configuration options and oracle grammar
    ORACLE: Grammar
    CONFIG, ORACLE = parse_input(file_name)
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



    # Generate guiding examples and corresponding ParseNodes
    guide_nodes = [[ParseNode(tok, True, []) for tok in ex.split()] for ex in GUIDE_EXAMPLES]

    # Create the log file and write positive and negative examples to it
    # Also write the initial starting grammar to the file
    with open(log_file, 'w+') as f:

        # Build the starting grammars and test them for compilation
        print('Building the starting grammar...'.ljust(50), end='\r')
        start_time = time.time()
        start_grammar : Grammar = build_start_grammar(OR_PARSER, CONFIG, guide_nodes)
        try:
            start_grammar.parser()
            print('\n\nInitial Grammar Created:\n%s' % str(start_grammar), file=f)
        except Exception as e:
            print('\n\nInitial grammar does not compile! %s' % str(e), file=f)
            print(start_grammar, file = f)
            exit()
        build_time = time.time() - start_time

        # Score the start grammar we arrived at earlier, which will add it to the
        # "interesting" set for future iterations
        print('Scoring grammar....'.ljust(50), end='\r')
        recall_set = start_grammar.sample_positives(100, 5)
        precision_set = ORACLE.sample_positives(100, 5)

        parser : Lark = start_grammar.parser()

        recall_num = 0
        print(f"Recall set (size {len(recall_set)}):", file=f)
        for example in recall_set:
            try:
                print("   ", example, file=f)
                OR_PARSER.parse(example)
                recall_num += 1
            except Exception as e:
                continue

        precision_num = 0

        print(f"Precision set (size {len(precision_set)}):", file=f)
        for example in precision_set:
            try:
                print("   ", example, file=f)
                parser.parse(example)
                precision_num += 1
            except Exception as e:
                continue

        print(f'Precision: {precision_num/len(precision_set)}, Recall: {recall_num/len(recall_set)}', file=f)
        print(f'Time spent building grammar: {build_time}s', file = f)
        print(f'Time spent building + scoring grammar: {time.time() - start_time}s', file = f)



if __name__ == '__main__':
    if len(sys.argv) != 3 or not os.path.exists(sys.argv[1]):
        print(f'Usage: python3 {sys.argv[0]} <input_file> <log_file>')
    else:
        main(sys.argv[1], sys.argv[2])

