"""
Main driver for smart stochastic grammar search algorithm.
"""
import sys
import argparse

def get_argparse():
    parser = argparse.ArgumentParser(description='Synthesize a grammar from an oracle + positive + negative examples.')
    subparsers = parser.add_subparsers(help="try to match an external program or an internal grammar")

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


def main():
    arg_parser = get_argparse()
    args = arg_parser.parse_args(sys.argv[1:])

    # TODO: populate everything


if __name__ == "__main__":
    main()