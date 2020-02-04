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
    if id == "loc5":
        rule_indices = [i - 1 for i, entry in enumerate(LOG) if entry[0] == "loc3"]
        if new_choice > choice:
            # Number of rules has increased, so duplicate random rule
            rule_index = random.randint(0, len(rule_indices) - 1)
            rule_indices += [len(LOG)]
            rule = LOG[rule_indices[rule_index]:rule_indices[rule_index + 1]]
            LOG += rule * (new_choice - choice)
        elif new_choice < choice:
            # Number of rules has decreased, so trim the log
            LOG = LOG[:rule_indices[-(choice - new_choice)]]
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

# Examples
positive_examples = ['b' + 'a'*i for i in range(10)]
negative_examples = ['a' + 'b'*i for i in range(10)]

# Score maximizing vector. Indices correspond to objectives:
# 1. Accuracy (Positive)    2. Accuracy (Negative)  3. Size
SCORE_VEC = [0] * 3
MAX_ITERS = 10

def accuracy_score(grammar):
    try:
        parser = grammar.parser()
    except:
        return 0, 0
    num_pos, num_neg = len(positive_examples), len(negative_examples)

    pos_correct = 0
    for pos in positive_examples:
        try:
            parser.parse(pos)
            pos_correct += 1
        except:
            pass

    neg_correct = 0
    for neg in negative_examples:
        try:
            parser.parse(neg)
            neg_correct += 1
        except:
            pass

    return pos_correct / num_pos, 1 - (neg_correct / num_neg)

def size_score(grammar):
    total_rule_size = 0
    for rule_start, rule in grammar.rules.items():
        for body in rule.bodies:
            total_rule_size += 1 + len(body)
    return 1 / total_rule_size

def print_grammar(grammar):
    p_score, n_score = accuracy_score(prev_grammar)
    s_score = size_score(prev_grammar)
    print('Grammar:\n%s\n\nLog:\n%s\n\nScores:\n%s\n' % (prev_grammar, prev_grammar.log, (p_score, n_score, s_score)))
    print('\n===========\n\n')

setup()
prev_grammar, prev_log = generate_grammar()
prev_grammar.log = prev_log
print_grammar(prev_grammar)

iterations = 0
while iterations < MAX_ITERS:
    setup(prev_grammar)
    next_grammar, next_log = generate_grammar()
    next_grammar.log = next_log
    print_grammar(next_grammar)
    prev_grammar = next_grammar
    iterations += 1

# Grammar creation and perturbance example
# setup()
# first_grammar, first_log = generate_grammar()
# first_grammar.log = first_log
# print('Grammar:\n%s\n\nLog:\n%s\n' % (first_grammar, first_grammar.log))
#
# print('===========\n')
#
# setup(first_grammar)
# second_grammar, second_log = generate_grammar()
# second_grammar.log = second_log
# print('Grammar:\n%s\n\nLog:\n%s\n' % (second_grammar, second_grammar.log))
