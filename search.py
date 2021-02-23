import random, sys, os, time
from input import parse_input
from parse_tree import ParseTree, ParseNode
from grammar import Grammar, Rule
from start import build_start_grammar
from lark import Lark
from oracle import CachingOracle, ExternalOracle
import string

"""
High-level command line to launch Arvada search. Currently assumes the benchmark is structured
as created by sample_lark. TODO: allow for general specification of guide examples + oracle command

See __main__ dispatch at the bottom for usage. 
"""


def approx_tokenize(guide_raw:str):
    def get_category(c):
        if c in string.ascii_letters:
            return "LETTER"
        if c in string.digits:
            return "DIGIT"
        if c in string.punctuation:
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
        if cur_category == prev_category:
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


def main_external(external_folder, log_file, fast = False, random_guides=False):
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

    guide_examples = []
    for filename in os.listdir(guide_folder):
        if filename.endswith(".ex"):
            full_filename = os.path.join(guide_folder, filename)
            guide_raw = open(full_filename).read()
            #guide = [ParseNode(tok, True, []) for tok in guide_raw]
            guide = approx_tokenize(guide_raw)
            guide_examples.append(guide)

    real_recall_set = []
    for filename in os.listdir(test_folder):
        if filename.endswith(".ex"):
            full_filename = os.path.join(test_folder, filename)
            test_raw = open(full_filename).read()
            real_recall_set.append(test_raw)

    if fast:
        grammar_contents = open(os.path.join("lark-examples", f"{bench_name}.lark")).read()
        oracle = CachingOracle(Lark(grammar_contents))
    else:
        oracle = ExternalOracle(parser_command)
    try:
        oracle.parse(real_recall_set[0])
    except Exception as e:
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
        precision_set = start_grammar.sample_positives(100, 5)
        parser : Lark = start_grammar.parser()

        num_precision_parsed = 0
        print(f"Precision set (size {len(precision_set)}):", file=f)
        for example in precision_set:
            try:
                print("   ", example, file=f)
                oracle.parse(example)
                num_precision_parsed += 1
            except Exception as e:
                continue

        num_recall_parsed = 0

        print(f"Recall set (size {len(real_recall_set)}):", file=f)
        for example in real_recall_set:
            try:
                print("   ", example, file=f)
                parser.parse(example)
                num_recall_parsed += 1
            except Exception as e:
                continue

        print(f'Recall: {num_recall_parsed/len(real_recall_set)}, Precision: {num_precision_parsed/len(precision_set)}', file=f)
        print(f"Build_time: {build_time}")
        print(f'Recall: {num_recall_parsed/len(real_recall_set)}, Precision: {num_precision_parsed/len(precision_set)}')
        print(f'Time spent building grammar: {build_time}s', file = f)
        print(f'Time spent building + scoring grammar: {time.time() - start_time}s', file = f)
        print(f'Parse calls: {oracle.parse_calls}, {oracle.real_calls}')
        print(f'Parse calls: {oracle.parse_calls}, {oracle.real_calls}', file = f)
        print(f'Pickling grammar...')
        import pickle
        pickle.dump(start_grammar, open(log_file + ".gram", "wb"))


if __name__ == '__main__':
    if len(sys.argv) != 4 or not os.path.exists(sys.argv[2]) :
        print(f'Usage: python3 {sys.argv[0]} <mode> <input_file/folder> <log_file>')
        print('where mode is one of {external, external-r}')
        if not os.path.exists(sys.argv[2]):
            print(f"err: {sys.argv[2]} not found")
    elif sys.argv[1] == "internal":
        print("NO LONGER SUPPORTED")
    elif sys.argv[1] == "external":
        main_external(sys.argv[2], sys.argv[3], False)
    elif sys.argv[1] == "external-r":
        main_external(sys.argv[2], sys.argv[3], False, random_guides=True)
    else:
        print(f'Usage: python3 {sys.argv[0]} <mode> <input_file> <log_file>')
        print('where mode is one of {external, internal}')
