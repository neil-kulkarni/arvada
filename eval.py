import argparse
import random, sys, os, time
from typing import Dict

from tqdm import tqdm

from parse_tree import ParseTree, ParseNode
from grammar import Grammar, Rule
from start import get_times, START
from lark import Lark
from oracle import CachingOracle, ExternalOracle
import string

"""
High-level command line to launch Arvada evaluation.
 
See __main__ dispatch at the bottom for usage. 
"""
PRECISION_SIZE=1000

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
    test_folder = os.path.join(external_folder, "test_set")
    parser_command = os.path.join(external_folder, f"parse_{bench_name}")

    main(parser_command, log_file, test_folder)

def main(oracle_cmd, log_file_name, test_examples_folder ):
    oracle = ExternalOracle(oracle_cmd)


    real_recall_set = []
    for filename in os.listdir(test_examples_folder):
        full_filename = os.path.join(test_examples_folder, filename)
        test_raw = open(full_filename).read()
        real_recall_set.append(test_raw)
        # TODO: make an option to try


    # Create the log file and write positive and negative examples to it
    # Also write the initial starting grammar to the file
    with open(log_file_name + ".eval", 'w+') as f:
        start_time = time.time()
        import pickle
        learned_grammar = Grammar(START)
        grammar_dict : Dict[str, Rule] = pickle.load(open(log_file_name + ".gramdict", "rb"))
        for key, rule in grammar_dict.items():
            learned_grammar.add_rule(rule)

        try:
            learned_grammar.parser()
            print('\n\nInitial grammar loaded:\n%s' % str(learned_grammar), file=f)
        except Exception as e:
            print('\n\nLoaded grammar does not compile! %s' % str(e), file=f)
            print(learned_grammar, file=f)
            exit()

        precision_set = learned_grammar.sample_positives(PRECISION_SIZE, 5)
        parser: Lark = learned_grammar.parser()

        example_gen_time = time.time()
        num_precision_parsed = 0

        print(f"Precision set (size {len(precision_set)}):", file=f)
        print("Eval of precision:")
        for example in tqdm(precision_set):
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
            print("Recall eval:")
            for example in tqdm(real_recall_set):
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

        print(f'Example gen time: {example_gen_time - start_time}', file=f)
        print(f'Scoring time: {time.time() - example_gen_time}', file=f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest='mode', help='benchmark mode (probably external unless you match the internal format)')
    internal_parser = subparser.add_parser('internal')
    external_parser = subparser.add_parser('external')

    internal_parser.add_argument('bench_folder', help='folder containing the benchmark', type=str)
    internal_parser.add_argument('log_file', help='log file output from search.py', type=str)
    external_parser.add_argument('oracle_cmd', help='the oracle command; should be invocable on a filename via `oracle_cmd filename`, and return a non-zero exit code on invalid inputs', type=str)
    external_parser.add_argument('examples_dir', help='folder containing the test (recall) examples', type=str)
    external_parser.add_argument('log_file', help='log file output from search.py', type=str)
    external_parser.add_argument('-n', '--precision_set_size', help='size of precision set to sample from learned grammar (default 1000)', type=int, default=1000)

    args = parser.parse_args()
    if args.mode == 'internal':
        main_internal(args.bench_folder, args.log_file)
    elif args.mode == 'external':
        if args.precision_set_size is not None:
            PRECISION_SIZE = args.precision_set_size
        main(args.oracle_cmd, args.log_file, args.examples_dir)
    else:
        parser.print_help()
        exit(1)
