import random
from grammar import Grammar, Rule

# Configurable
ALPHABET = ['"a"', '"b"']
MAX_NONTERMINALS = 3
NONTERMINALS = ["T" + str(i) for i in range(0, MAX_NONTERMINALS)]
NUM_RULES = 4
MAX_RHS_LEN = 3

# Global Logging
LOG = []
INDEX = 0
REPLAY_MODE = False

def setup(from_grammar=None):
    global LOG, INDEX, REPLAY_MODE
    if from_grammar is None:
        LOG.clear()
        INDEX = 0
        REPLAY_MODE = False
    else:
        LOG = list(from_grammar.log)
        INDEX = 0
        REPLAY_MODE = True
        perturb_log()

def generate_grammar():
    start = generate_nonterminal()
    grammar = Grammar(start)
    n_rules = choose("loc5", list(range(1, NUM_RULES)))
    for _ in range(n_rules):
        grammar.add_rule(generate_rule())
    return grammar, list(LOG)

def generate_rule():
    lhs = generate_nonterminal()
    rhs = []
    rhs_len = choose("loc3", list(range(1, MAX_RHS_LEN)))
    for _ in range(rhs_len):
        is_terminal = choose("loc4", [True, False])
        if is_terminal:
            rhs.append(generate_terminal())
        else:
            rhs.append(generate_nonterminal())
    return Rule(lhs).add_body(rhs)

def generate_terminal():
    return choose("loc1", ALPHABET)

def generate_nonterminal():
    return choose("loc2", NONTERMINALS)

def choose(id, from_collection):
    global INDEX
    if REPLAY_MODE:
        (id2, n, choice) = LOG[INDEX]
        INDEX = INDEX + 1
        assert id == id2
        return from_collection[choice]
    else:
        n = len(from_collection)
        choice = random.randint(0, n - 1)
        LOG.append((id, n, choice))
        return from_collection[choice]

def perturb_log():
    global LOG
    log_index = random.randint(0, len(LOG) - 1)
    (id, n, choice) = LOG[log_index]
    new_choice = random.randint(0, n - 1)
    if id == "loc5" and new_choice > choice:
        # Number of rules has increased, so duplicate random rule
        rule_indices = [i - 1 for i, entry in enumerate(LOG) if entry[0] == "loc3"]
        rule_index = random.randint(0, len(rule_indices) - 1)
        rule_indices += [len(LOG)]
        rule = LOG[rule_indices[rule_index]:rule_indices[rule_index + 1]]
        LOG += rule * (new_choice - choice)
    elif id == "loc3":
        # Size of a rule has changed, so duplicate choices
        rule_indices = [i - 1 for i, entry in enumerate(LOG) if entry[0] == "loc3"]
        rule_indices += [len(LOG)]
        rule_index = rule_indices.index(log_index - 1)
        before, after = LOG[:rule_indices[rule_index]], LOG[rule_indices[rule_index + 1]:]
        rule = LOG[rule_indices[rule_index]:rule_indices[rule_index + 1]]
        if new_choice < choice:
            rule = rule[:-(choice - new_choice)*2]
        else:
            last = rule[-2:] * (new_choice - choice)
            rule = rule + last
        LOG = before + rule + after
        pass
    elif id == "loc4" and choice != new_choice:
        # Generate a terminal instead of a nonterminal or vice versa
        next_entry = LOG[log_index + 1]
        if next_entry[0] == "loc1":
            LOG[log_index + 1] = ("loc2", len(NONTERMINALS), random.randint(0, len(NONTERMINALS) - 1))
        else:
            LOG[log_index + 1] = ("loc1", len(ALPHABET), random.randint(0, len(ALPHABET) - 1))
    LOG[log_index] = (id, n, new_choice)

setup()
first_grammar, first_log = generate_grammar()
first_grammar.log = first_log
print('Grammar:\n%s\n\nLog:\n%s\n' % (first_grammar, first_grammar.log))

print('===========\n')

setup(first_grammar)
second_grammar, second_log = generate_grammar()
second_grammar.log = second_log
print('Grammar:\n%s\n\nLog:\n%s\n' % (second_grammar, second_grammar.log))
