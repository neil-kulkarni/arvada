import start
from parse_tree import ParseNode
import pickle
from oracle import CachingOracle
from lark import Lark


def test_one():
    gram_name = 'lark-examples/while.lark'
    parser = Lark(open(gram_name).read())
    oracle = CachingOracle(parser)
    oracle.parse("L = n")
    print("hey!")
    start.next_tid, trees, grammar, coalesce_target =pickle.load(open("while-dbl-bug2.pkl", "rb"))
    for tree in trees:
        print(tree)
    print(coalesce_target)
    coalesced = start.coalesce(oracle, trees, grammar, coalesce_target)
    print(coalesced)

def test_two():
    bubble_1 : start.Bubble
    bubble_2 : start.Bubble
    bubble_1, bubble_2 =pickle.load(open("overlap-bug.pkl", "rb"))
    print(bubble_1, bubble_2)
    print(bubble_1.application_breaks_other(bubble_2))


if __name__ == "__main__":
    test_two()