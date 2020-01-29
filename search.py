from lark import Lark

MAX_RULES = 2
MAX_RULE_SIZE = 2
TERMINALS = ['"A"', '"B"']
NONTERMINALS = ['a', 'b']
SYMBOLS = TERMINALS + NONTERMINALS

def parser_matches_examples(parser, positive, negative):
    """
    Returns if all the positive examples belong to the parser and none of
    the negative examples belong to the parser.
    """
    for example in positive:
        try:
            parser.parse(example)
        except:
            return False
    for example in negative:
        try:
            parser.parse(example)
            return False
        except:
            pass
    return True

def generate_grammar_parser():
    """
    Generates all possible valid grammar parsers under the size constraints
    MAX_RULES, MAX_RULE_SIZE, MAX_TERMINALS, MAX_NONTERMINALS.
    """
    for grammar in generate_grammar_string():
        try:
            yield (Lark(grammar), grammar)
        except:
            pass

def generate_grammar_string():
    """
    Generates all possibile grammar strings under the size constraints
    MAX_RULES, MAX_RULE_SIZE, MAX_TERMINALS, MAX_NONTERMINALS.

    Nonterminals are capital letters, terminals are lowercase letters.
    Note that this enforces the constraint that MAX_TERMINALS <= 26
    and MAX_NONTERMINALS <= 26. This constraint is not overly restrictive
    due to the exponential nature of this problem.
    """
    for num_rules in range(1, MAX_RULES + 1):
        for grammar_body in generate_fixed_size_grammar_string(num_rules):
            start_nonterminal = grammar_body[0]
            grammar = 'start: %s\n%s\n' % (start_nonterminal, grammar_body)
            yield postprocess(grammar)

def generate_fixed_size_grammar_string(size):
    """
    Helper function for generate_grammar_string that generates all
    possible versions of a fixed-size grammar.
    """
    if size == 1:
        yield from generate_grammar_rule()
    else:
        for first_rule in generate_grammar_rule():
            for rest_rules in generate_fixed_size_grammar_string(size - 1):
                yield '%s\n%s' % (first_rule, rest_rules)

def generate_grammar_rule():
    """
    Helper function for generate_grammar_string that generates all
    possible versions of a particular grammar rule.
    """
    for rule_name in NONTERMINALS:
        for rule_size in range(1, MAX_RULE_SIZE + 1):
            for rule_body in generate_fixed_size_grammar_rule(rule_size):
                yield '%s: %s' % (rule_name, rule_body)

def generate_fixed_size_grammar_rule(size):
    """
    Helper function for generate_grammar_rule that generates all
    possible versions of a fixed-size grammar rule.
    """
    if size == 1:
        yield from SYMBOLS
    else:
        for rule_start in SYMBOLS:
            for rule_rest in generate_fixed_size_grammar_rule(size - 1):
                yield '%s %s' % (rule_start, rule_rest)

def postprocess(grammar):
    """
    generate_grammar_string naively returns grammars like:

        start: a
        a: a "A"
        a: "B"

    That are not valid inputs to the Lark constructor, since the same rule
    was redefined. This is fixed by sorting the grammar body and inserting |
    symbols in place of the redefined rule. With our example:

        start: a
        a: a "A"
        | "B"

    This method makes assumptions about the input string made all throughout
    this file, namely the structure of the grammar and the type of characters
    used for terminals and nonterminals.
    """
    grammar = grammar.strip()
    index = grammar.find('\n')
    header = grammar[:index + 1]
    body = grammar[index + 1:]

    body_list = sorted(body.split('\n'))
    for i in range(1, len(body_list)):
        if body_list[i][0] == body_list[i-1][0] or body_list[i-1][0] == '|':
            body_list[i] = '|' + body_list[i][2:]

    body = '\n'.join(body_list)
    return header + body

# Draw examples from the grammar:
# start: a
# a: a "A"
# a: "B"
positive_examples = ['B' + 'A'*i for i in range(10)]
negative_examples = ['A' + 'B'*i for i in range(10)]

# Generate all possible grammars of size two
# Store the grammars that match the example grammar in matching_grammars
count, matching_grammars = 0, []
for p, g in generate_grammar_parser():
    print(count)
    print(g)
    if parser_matches_examples(p, positive_examples, negative_examples):
        matching_grammars.append(g)
        print('Success')
    print()
    count += 1

print('Grammars that matched the input examples:')
for g in matching_grammars:
    print(g)
    print()

# Example Grammar and Usage
# https://github.com/lark-parser/lark
#
# grammar = """
# start: expr
# expr: expr op expr
# | value
# op: "+"
# value: "1"
# """
#
# parser = Lark(grammar)
# print(parser.parse("1+1+1").pretty())
