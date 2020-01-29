#configurable
ALPHABET = ["A", "B"]
NUM_RULES = 8
MAX_RHS_LEN = 3
MAX_NONTERMINALS = MAX_RULES

#globals
log = []
index = 0
nonterminals = ["T" + str(i) for i in range(0, MAX_NONTERMINALS)]
MODE = "replay"

def choose(id, from_collection):
    if MODE == "replay":
        (id2, len, choice) = log[index]
        index = index + 1
        assert id == id2
        return from_collection[choice]
    else:
        len = len(from_collection)
        choice = random.int(0, len)
        log.append((id, len, choice))
        return from_collection[choice]

def generate_grammar():
    if MODE != "replay":
        log.clear()
    rules = []
    n_rules = choose("loc5", list(range(0, NUM_RULES)))
    for j in range(1, n_rules):
        rules.append(generate_rule())
    return rules

def generate_rule():
    lhs = generate_nonterminal()
    rhs = []
    rhs_len = choose("loc3", list(range(0, MAX_RHS_LEN)))
    for j in range(1, rhs_len):
        is_terminal = choose("loc4", [True, False])
        if is_terminal:
            rhs.append(generate_terminal())
        else:
            rhs.append(generate_nonterminal())
    return (lhs, rhs)

def generate_terminal():
    return choose("loc1", ALPHABET)

def generate_nonterminal():
    return choose("loc2", nonterminals)
