import sys, pickle
from lark import Lark

def compute_stats(name, rules):
    rule_count = len(rules)
    terminals = set()
    nonterminals = set()
    for rule in rules:
        nonterminals.add(rule.origin)
        for sym in rule.expansion:
            if sym.is_term:
                terminals.add(sym)
            else:
                nonterminals.add(sym)
    print('Rules:', rule_count)
    print('Terms:', len(terminals))
    print('NTrms:', len(nonterminals))
    print('-')

for i in range(1, len(sys.argv)):
    name = sys.argv[i]
    print(name)
    parser = Lark(open(name, 'r').read())
    compute_stats(name, parser.rules)

