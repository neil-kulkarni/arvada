import random, sys, os, time
from input import parse_input
from parse_tree import ParseTree, ParseNode
from grammar import Grammar, Rule
from start import build_start_grammar, get_times
from lark import Lark
from oracle import CachingOracle, ExternalOracle
import string

"""
High-level command line to launch Arvada search. Currently assumes the benchmark is structured
as created by sample_lark. TODO: allow for general specification of guide examples + oracle command

See __main__ dispatch at the bottom for usage. 
"""

GROUP_PUNCTUATION = False
SPLIT_UPPER_AND_LOWER = True

def approx_tokenize(guide_raw:str):
    def get_category(c):
        if not SPLIT_UPPER_AND_LOWER and c in string.ascii_letters:
            return "LETTER"
        if SPLIT_UPPER_AND_LOWER and c in string.ascii_uppercase:
            return "UPPER"
        if SPLIT_UPPER_AND_LOWER and c in string.ascii_lowercase:
            return "LOWER"
        if c in string.digits:
            return "DIGIT"
        if GROUP_PUNCTUATION and c in string.punctuation:
            return "PUNCTUATION"
        if c in string.whitespace:
            return "WHITESPACE"
        else:
            return None
    prev_category = None
    cur_token = ""
    start = True
    tokens = []
    for c in guide_raw:
        cur_category = get_category(c)
        if cur_category is not None and cur_category == prev_category:
            cur_token += c
        else:
            if not start:
                tokens.append(ParseNode(cur_token, True, []))
            cur_token = c
        prev_category = cur_category
        start = False
    if cur_token != "":
        tokens.append(ParseNode(cur_token, True, []))
    return tokens


def main_internal(external_folder, log_file, random_guides=False):
    """
    `external_folder`: the base folder for the benchmark, which contains:
      - random-guides: dir of random guide examples
      - guides: dir of minimal guide examples
      - test_set: dir of held-out test examples
      - parse_bench_name: the parser command (oracle). assume bench_name is the
        base (i.e. without parent directories) name of external_folder
    `log_file`: where to write results
    `fast`: use internal caching oracle created with the Lark grammar, instead
            of the external command
    `random_guides`: learn from the guide examples in random-guides instead of guides
    """
    import os
    bench_name = os.path.basename(external_folder)
    if random_guides:
        guide_folder = os.path.join(external_folder, "random-guides")
    else:
        guide_folder = os.path.join(external_folder, "guides")
    test_folder = os.path.join(external_folder, "test_set")
    parser_command = os.path.join(external_folder, f"parse_{bench_name}")

    main(parser_command, guide_folder, log_file, test_folder)


def main(oracle_cmd, guide_examples_folder,  log_file_name, test_examples_folder = None):
    oracle = ExternalOracle(oracle_cmd)

    guide_examples = []
    for filename in os.listdir(guide_examples_folder):
        full_filename = os.path.join(guide_examples_folder, filename)
        guide_raw = open(full_filename).read()
        guide = approx_tokenize(guide_raw)
        guide_examples.append(guide)

    if test_examples_folder is not None:
        real_recall_set = []
        for filename in os.listdir(test_examples_folder):
            full_filename = os.path.join(test_examples_folder, filename)
            test_raw = open(full_filename).read()
            real_recall_set.append(test_raw)
        # TODO: make an option to try
        # try:
        #     oracle.parse(test_raw)
        # except Exception as e:
        #     print(f"Woops! The oracle can't parse the test set: {full_filename}")
        #     exit(1)
    else:
        real_recall_set = None

    # Create the log file and write positive and negative examples to it
    # Also write the initial starting grammar to the file
    with open(log_file_name, 'w+') as f:

        # Build the starting grammars and test them for compilation
        print('Building the starting grammar...'.ljust(50), end='\r')
        start_time = time.time()
        start_grammar: Grammar = build_start_grammar(oracle, guide_examples)
        try:
            start_grammar.parser()
            print('\n\nInitial Grammar Created:\n%s' % str(start_grammar), file=f)
        except Exception as e:
            print('\n\nInitial grammar does not compile! %s' % str(e), file=f)
            print(start_grammar, file=f)
            exit()
        build_time = time.time() - start_time

        # Score the start grammar we arrived at earlier, which will add it to the
        # "interesting" set for future iterations
        oracle_time_spent = oracle.time_spent
        oracle_parse_calls = oracle.parse_calls
        oracle_real_calls = oracle.real_calls

        precision_set = start_grammar.sample_positives(1000, 5)
        parser: Lark = start_grammar.parser()

        print('Scoring grammar....'.ljust(50), end='\r')

        num_precision_parsed = 0

        print(f"Precision set (size {len(precision_set)}):", file=f)
        for example in precision_set:
            try:
                oracle.parse(example, timeout=10)
                print("   ", example, file=f)
                num_precision_parsed += 1
            except Exception as e:
                print("   ", example, " <----- FAILURE", file=f)
                continue

        num_recall_parsed = 0

        if real_recall_set is not None:
            print(f"Recall set (size {len(real_recall_set)}):", file=f)
            for example in real_recall_set:
                try:
                    parser.parse(example)
                    print("   ", example, file=f)
                    num_recall_parsed += 1
                except Exception as e:
                    print("   ", example, " <----- FAILURE", file=f)
                    continue

            print(
                f'Recall: {num_recall_parsed / len(real_recall_set)}, Precision: {num_precision_parsed / len(precision_set)}',
                file=f)
            print(
                f'Recall: {num_recall_parsed / len(real_recall_set)}, Precision: {num_precision_parsed / len(precision_set)}')
        else:
            print(
                f'Recall: [no test set provided], Precision: {num_precision_parsed / len(precision_set)}',
                file=f)
            print(
                f'Recall: [no test set provided], Precision: {num_precision_parsed / len(precision_set)}')

        print(f'Time spent in oracle calls: {oracle_time_spent}', file=f)
        print(f'Time spent in oracle calls: {oracle_time_spent}')
        print(f'Time spent building grammar: {build_time}s', file=f)
        print(f'Time spent building grammar: {build_time}s', )
        print(f'Time breakdown: {get_times()}', file=f)
        print(f'Time breakdown: {get_times()}')
        print(f'Parse calls: {oracle_parse_calls}, {oracle_real_calls}')
        print(f'Parse calls: {oracle_parse_calls}, {oracle_real_calls}', file=f)
        print(f'Pickling grammar...')
        import pickle
        start_grammar.parser = None
        pickle.dump(start_grammar.rules, open(log_file_name + ".gramdict", "wb"))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: python3 {sys.argv[0]} <mode>')
        print('where mode is one of {internal, internal-r, external}')
        print(f'run with python3 {sys.argv[0]} <mode> to see detailed help')
        exit(1)
    elif sys.argv[1] == "external":
        if len(sys.argv) < 5 or not os.path.exists(sys.argv[3]):
            print(f'Usage: python3 {sys.argv[0]} external <oracle_cmd> <training_example_dir> <log_file> (<test_example_dir>)')
            print('<oracle_cmd> should be a string which can be invoked with `<oracle_cmd> filename` (so can include options)')
            exit(1)
        main(sys.argv[2], sys.argv[3], sys.argv[4], None if len(sys.argv) == 5 else sys.argv[5])
    elif sys.argv[1] == "internal":
        if len(sys.argv) != 4 or not os.path.exists(sys.argv[2]):
            print(f'Usage: python3 {sys.argv[0]} <mode> <input_file> <log_file>')
            print('where mode is one of {internal, internal-r}')
            exit(1)
        main_internal(sys.argv[2], sys.argv[3], random_guides=False)
    elif sys.argv[1] == "internal-r":
        if len(sys.argv) != 4 or not os.path.exists(sys.argv[2]):
            print(f'Usage: python3 {sys.argv[0]} <mode> <input_file> <log_file>')
            print('where mode is one of {internal, internal-r}')
            exit(1)
        main_internal(sys.argv[2], sys.argv[3], random_guides=True)
    else:
        print(f'Usage: python3 {sys.argv[0]} <mode> [other args...]')
        print('where mode is one of {internal, internal-r, external}')
        print(f'run with python3 {sys.argv[0]} <mode> to see detailed help')
