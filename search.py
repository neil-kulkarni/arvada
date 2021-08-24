import argparse
import random, sys, os, time
from input import parse_input
from parse_tree import ParseTree, ParseNode
from grammar import Grammar, Rule
from start import build_start_grammar, get_times
from lark import Lark
from oracle import CachingOracle, ExternalOracle
import string

"""
High-level command line to launch Arvada search.

See __main__ dispatch at the bottom for usage. 
"""

USE_PRETOKENIZATION = True

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
    if USE_PRETOKENIZATION:
       print("Using approximate pre-tokenization stage")

    guide_examples = []
    for filename in os.listdir(guide_examples_folder):
        full_filename = os.path.join(guide_examples_folder, filename)
        guide_raw = open(full_filename).read()
        if USE_PRETOKENIZATION:
            guide = approx_tokenize(guide_raw)
        else:
            guide = [ParseNode(c, True, []) for c in guide_raw]
        guide_examples.append(guide)

    average_guide_len = sum([len(g) for g in guide_examples])/len(guide_examples)
    if average_guide_len > 40:
        bbl_bounds = (6, 20)
    else:
        bbl_bounds = (3, 10)

    # Create the log file and write positive and negative examples to it
    # Also write the initial starting grammar to the file
    with open(log_file_name, 'w+') as f:

        # Build the starting grammars and test them for compilation
        print('Building the starting grammar...'.ljust(50), end='\r')
        start_time = time.time()
        start_grammar: Grammar = build_start_grammar(oracle, guide_examples, bbl_bounds)
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
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest='mode', help='benchmark mode (probably external unless you match the internal format)')
    internal_parser = subparser.add_parser('internal')
    external_parser = subparser.add_parser('external')

    internal_parser.add_argument('bench_folder', help='folder containing the benchmark', type=str)
    internal_parser.add_argument('log_file', help='name of file to write output log to', type=str)

    external_parser.add_argument('oracle_cmd', help='the oracle command; should be invocable on a filename via `oracle_cmd filename`, and return a non-zero exit code on invalid inputs', type=str)
    external_parser.add_argument('examples_dir', help='folder containing the training examples', type=str)
    external_parser.add_argument('log_file', help='name of file to write output log to', type=str)
    external_parser.add_argument('--no-pretokenize',  help=f'assign each character to its own leaf node, rather than grouping characters of same lassc', action='store_true', dest='no_pretokenize')
    external_parser.add_argument('--group_punctuation', help=f'group sequences of punctuation during pretokenization', action='store_true')
    external_parser.add_argument('--group_upper_lower',
                                 help=f'group uppercase characters with lowerchase characters during pretokenization', action='store_true')
    #TODO: what is this error?
    args = parser.parse_args()
    if args.mode == 'internal':
        main_internal(args.bench_folder, args.log_file, random_guides=False)
    elif args.mode == 'external':
        if args.no_pretokenize:
            USE_PRETOKENIZATION = False
        if args.group_punctuation:
            GROUP_PUNCTUATION = True
        if args.group_upper_lower:
            SPLIT_UPPER_AND_LOWER = False
        main(args.oracle_cmd, args.examples_dir, args.log_file)
    else:
        parser.print_help()
        exit(1)

