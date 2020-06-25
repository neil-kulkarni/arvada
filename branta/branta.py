"""
Main driver for smart stochastic grammar search algorithm.
"""
import sys
import argparse
from input import parse_input
from typing import Union
from parse_tree import ParseTree
from branta.oracle import GrammarOracle, SubprocessOracle
from branta.search import search

def get_argparse():
    parser = argparse.ArgumentParser(description='Synthesize a grammar from an oracle + positive + negative examples.')
    subparsers = parser.add_subparsers(help="try to match an external program or an internal grammar", dest='mode')

    # Internal mode
    parser_internal = subparsers.add_parser("internal", help="internal mode (for testing against ground-truth grammars)")
    parser_internal.add_argument("--config", required=True, help="config/json file name")
    parser_internal.add_argument("--positives", required=False, help="positive examples; by default, generate random ones")
    parser_internal.add_argument("--negatives", required=False, help="negative examples; by default, generate random ones")
    parser_internal.add_argument("-l", "--log", default="branta.log", help="log file name")

    # external mode
    parser_external = subparsers.add_parser("external", help="external mode (for testing against external oracles)")
    parser_external.add_argument("--oracle", required=True, help="oracle subcommand")
    parser_external.add_argument("--guides", required=True, help="guide examples")
    parser_external.add_argument("--positives", required=True, help="positive examples")
    parser_external.add_argument("--negatives", required=True, help="negative examples")
    parser_external.add_argument("-l", "--log", default="branta.log", help="log file name")

    return parser

def internal_main(config_name: str, positives_name: Union[str, None] = None, negatives_name: Union[str, None] = None):
    # Generate configuration options and oracle grammar
    CONFIG, ORACLE_GEN, grammar = parse_input(config_name)
    POS_EXAMPLES, NEG_EXAMPLES = CONFIG['POS_EXAMPLES'], CONFIG['NEG_EXAMPLES']
    MAX_NEG_EXAMPLE_SIZE = CONFIG['MAX_NEG_EXAMPLE_SIZE']
    TERMINALS, MAX_TREE_DEPTH = CONFIG['TERMINALS'], CONFIG['MAX_TREE_DEPTH']
    GUIDE_EXAMPLES = CONFIG['GUIDE']

    oracle_parse_tree = ParseTree(ORACLE_GEN)
    print('Generating positive examples...'.ljust(50), end='\r')
    positive_examples, positive_nodes = oracle_parse_tree.sample_strings(POS_EXAMPLES, MAX_TREE_DEPTH)
    print('Generating negative examples...'.ljust(50), end='\r')
    negative_examples = grammar.sample_negatives(NEG_EXAMPLES, TERMINALS, MAX_NEG_EXAMPLE_SIZE)

    oracle = GrammarOracle(grammar)
    return oracle, GUIDE_EXAMPLES, positive_examples, negative_examples




def main():
    arg_parser = get_argparse()
    args = arg_parser.parse_args(sys.argv[1:])

    if args.mode is None:
        arg_parser.print_help()
        exit(1)
    elif args.mode == 'internal':
        config_name = args.config
        log_name = args.log
        # TODO: support positive/negative examples provided on command line

        print("HELLOOOO")
        oracle, guides, positives, negatives = internal_main(config_name)
        search(oracle, guides, positives, negatives)
    else:
        # External mode, not yet implemented.
        pass


if __name__ == "__main__":
    main()