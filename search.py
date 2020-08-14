import random, sys, os, time
from input import parse_input
from parse_tree import ParseTree, ParseNode
from grammar import Grammar, Rule
from start import build_start_grammar
from lark import Lark
from oracle import CachingOracle, ExternalOracle


def main_external(external_folder, log_file, fast = False):
    import os
    bench_name = os.path.basename(external_folder)
    guide_folder = os.path.join(external_folder, "guides")
    test_folder = os.path.join(external_folder, "test_set")
    parser_command = os.path.join(external_folder, f"parse_{bench_name}.py")

    guide_examples = []
    for filename in os.listdir(guide_folder):
        if filename.endswith(".ex"):
            full_filename = os.path.join(guide_folder, filename)
            guide_raw = open(full_filename).read()
            print(f"Guide {filename}:\n{guide_raw}")
            guide = [ParseNode(tok, True, []) for tok in guide_raw]
            guide_examples.append(guide)

    precision_set = []
    for filename in os.listdir(test_folder):
        if filename.endswith(".ex"):
            if len(precision_set) ==0:
                print("first precision example is ", filename)
            full_filename = os.path.join(test_folder, filename)
            test_raw = open(full_filename).read()
            precision_set.append(test_raw)

    if fast:
        grammar_contents = open(os.path.join("lark-examples", f"{bench_name}.lark")).read()
        oracle = CachingOracle(Lark(grammar_contents))
    else:
        oracle = ExternalOracle(parser_command)
    try:
        oracle.parse(precision_set[0])
    except Exception as e:
        print(e)
        print("Woops! The oracle can't parse the precision set.")
        exit(1)

    # Create the log file and write positive and negative examples to it
    # Also write the initial starting grammar to the file
    with open(log_file, 'w+') as f:

        # Build the starting grammars and test them for compilation
        print('Building the starting grammar...'.ljust(50), end='\r')
        start_time = time.time()
        start_grammar : Grammar = build_start_grammar(oracle, guide_examples)
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
        parser : Lark = start_grammar.parser()

        recall_num = 0
        print(f"Recall set (size {len(recall_set)}):", file=f)
        for example in recall_set:
            try:
                print("   ", example, file=f)
                oracle.parse(example)
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
        print(f"Build_time: {build_time}")
        print(f'Precision: {precision_num/len(precision_set)}, Recall: {recall_num/len(recall_set)}')
        print(f'Time spent building grammar: {build_time}s', file = f)
        print(f'Time spent building + scoring grammar: {time.time() - start_time}s', file = f)
        print(f'Parse calls: {oracle.parse_calls}')
        print(f'Parse calls: {oracle.parse_calls}', file = f)

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
        OR_PARSER = CachingOracle(OR_PARSER)
    except Exception as e:
        print(f"Oops! The Lark parser couldn't compile. Here's the error:\n {e.__str__()}\n")
        print('Fix your grammar. Exiting now.')
        exit(1)


    # Generate guiding examples and corresponding ParseNodes
    #guide_nodes = [[ParseNode(tok, True, []) for tok in ex.split()] for ex in GUIDE_EXAMPLES]
    # TODO: this assumes there are no spaces in the inputs...
    guide_nodes = [[ParseNode(tok, True, []) for tok in ex.replace(' ', '')] for ex in GUIDE_EXAMPLES]

    # Create the log file and write positive and negative examples to it
    # Also write the initial starting grammar to the file
    with open(log_file, 'w+') as f:

        # Build the starting grammars and test them for compilation
        print('Building the starting grammar...'.ljust(50), end='\r')
        start_time = time.time()
        start_grammar : Grammar = build_start_grammar(OR_PARSER, guide_nodes)
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
        print(f"Build_time: {build_time}")
        print(f'Precision: {precision_num/len(precision_set)}, Recall: {recall_num/len(recall_set)}')
        print(f'Time spent building grammar: {build_time}s', file = f)
        print(f'Time spent building + scoring grammar: {time.time() - start_time}s', file = f)



if __name__ == '__main__':
    if len(sys.argv) != 4 or not os.path.exists(sys.argv[2]) :
        print(f'Usage: python3 {sys.argv[0]} <mode> <input_file/folder> <log_file>')
        print('where mode is one of {external, internal}')
    elif sys.argv[1] == "internal":
        main(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "external":
        main_external(sys.argv[2], sys.argv[3], True)
    else:
        print(f'Usage: python3 {sys.argv[0]} <mode> <input_file> <log_file>')
        print('where mode is one of {external, internal}')
