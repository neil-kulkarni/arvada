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
    `random_guides`: learn from the guide examples in random-guides instead of guides
    """
    import os
    bench_name = os.path.basename(external_folder)
    if random_guides:
        guide_folder = os.path.join(external_folder, "random-guides")
    else:
        guide_folder = os.path.join(external_folder, "guides")
    parser_command = os.path.join(external_folder, f"parse_{bench_name}")

    main(parser_command, guide_folder, log_file)


def main(oracle_cmd, guide_examples_folder,  log_file_name):
    oracle = ExternalOracle(oracle_cmd)

    guide_examples = []
    for filename in os.listdir(guide_examples_folder):
        full_filename = os.path.join(guide_examples_folder, filename)
        guide_raw = open(full_filename).read()
        guide = approx_tokenize(guide_raw)
        guide_examples.append(guide)


    # Create the log file and write positive and negative examples to it
    # Also write the initial starting grammar to the file
    with open(log_file_name, 'w+') as f:

        # Build the starting grammars and test them for compilation
        print('Building the starting grammar...'.ljust(50), end='\r')
        start_time = time.time()
        start_grammar: Grammar = build_start_grammar(oracle, guide_examples)
        build_time = time.time() - start_time

        oracle_time_spent = oracle.time_spent
        oracle_parse_calls = oracle.parse_calls
        oracle_real_calls = oracle.real_calls

        print(f'Pickling grammar...')
        import pickle
        pickle.dump(start_grammar.rules, open(log_file_name + ".gramdict", "wb"))


        print(f'Time spent in oracle calls: {oracle_time_spent}', file=f)
        print(f'Time spent in oracle calls: {oracle_time_spent}')
        print(f'Time spent building grammar: {build_time}s', file=f)
        print(f'Time spent building grammar: {build_time}s', )
        print(f'Scoring time: {time.time() - build_time - start_time}', file=f)
        print(f'Time breakdown: {get_times()}', file=f)
        print(f'Time breakdown: {get_times()}')
        print(f'Parse calls: {oracle_parse_calls}, {oracle_real_calls}')
        print(f'Parse calls: {oracle_parse_calls}, {oracle_real_calls}', file=f)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: python3 {sys.argv[0]} <mode>')
        print('where mode is one of {internal, internal-r, external}')
        print(f'run with python3 {sys.argv[0]} <mode> to see detailed help')
        exit(1)
    elif sys.argv[1] == "external":
        if len(sys.argv) < 5 or not os.path.exists(sys.argv[3]):
            print(f'Usage: python3 {sys.argv[0]} external <oracle_cmd> <training_example_dir> <log_file>')
            print('<oracle_cmd> should be a string which can be invoked with `<oracle_cmd> filename` (so can include options)')
            exit(1)
        main(sys.argv[2], sys.argv[3], sys.argv[4])
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
