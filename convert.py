import sys
import json
import jsbeautifier

# Converts the txt representation of the grammar into a json representation
# for the rest of the program. Names the json representation JSON_FILE_NAME.
def main(txt_file_name, json_file_name):
    txt_file = open(txt_file_name, 'r')
    lines = txt_file.readlines()

    # Strip comments and empty lines
    lines = [line.strip() for line in lines if is_valid_line(line)]

    # The first line of the file is the set of terminals. The rest are rules.
    terminals = [token.strip() for token in lines[0].split(',')]
    rules = coalesce_rules(lines[1:])

    # Create and mutate the rule_map before dumping it to JSON
    rule_map = get_rule_map(rules)
    handle_plus_rules(rule_map)
    handle_star_rules(rule_map)
    handle_question_rules(rule_map)

    # Create dictionary mapping to be marshalled into a JSON representation
    json_repr = {}
    json_repr['config'] = {}
    json_repr['config']['TERMINALS'] = terminals
    json_repr['config']['NONTERMINALS'] = list(rule_map.keys())

    json_repr['grammar'] = {}
    json_repr['grammar']['start'] = list(rule_map.keys())[0]
    json_repr['grammar']['rules'] = []

    for rule_start, rule_bodies in rule_map.items():
        rule_dict = {}
        rule_dict['start'] = rule_start
        rule_dict['bodies'] = []

        for rule_body in rule_bodies:
            split_body = [token if token != '/eps' else '' for token in rule_body.split()]
            rule_dict['bodies'].append(split_body)

        json_repr['grammar']['rules'].append(rule_dict)

    # Dump the JSON representation to the output file
    json_dump = json.dumps(json_repr)
    opts = jsbeautifier.default_options()
    opts.indent_size = 2
    output = jsbeautifier.beautify(json_dump, opts)

    output_file = open(json_file_name, 'w+')
    output_file.write(output)
    print('Conversion successful!')
    print('Remember to update the remainder of the configuration options!')

# Mutates the rule map to search for all expressions ending in the rule_token.
# Adds a new rule corresponding to the expression via the passed-in rule_builder
# and names it according to the rule_name function. Updates each rule ending in
# the rule_token to point to the newly created rule
#
# Example Parameters:
# rule_token = '/+'
# rule_name_fn = lambda s: '_%s_plus' % s
# rule_builder_fn = lambda s, n: [s, '%s %s' % (n, s)]
#
# Example Effect:
# program := expr/+
# =>
# program := _expr_plus
# _expr_plus := expr | _expr_plus expr
# If any other rules had expr/+, they would also point to _expr_plus
def handle_custom_rules(rule_map, rule_token, rule_name_fn, rule_builder_fn):
    # Taking the list of the keys forces us to iterate only through keys
    # that were present at the start of this function
    for rule_name in list(rule_map.keys()):

        # The rule_map maps a string rule name to a list of rule bodies
        # We create any new rules necessary in rule_map, and update this
        # list of rule bodies to use the new rule
        rule_bodies = rule_map[rule_name]
        for rule_body_index in range(len(rule_bodies)):
            rule_body = rule_bodies[rule_body_index]

            # Tokenize the rule body to check for any custom tokens
            rule_body_symbols = rule_body.split()
            for i in range(len(rule_body_symbols)):
                symbol = rule_body_symbols[i]

                # If part of a token ends in (non-escaped) rule_token...
                n = len(rule_token)
                if symbol[-n:] == rule_token and symbol[-(n+1)] != '/':
                    cleaned_symbol = symbol[:-n]
                    custom_rule_name = rule_name_fn(cleaned_symbol)

                    # If there is not already a custom rule for this token, create one
                    if not custom_rule_name in rule_map:
                        rule_map[custom_rule_name] = rule_builder_fn(cleaned_symbol, custom_rule_name)

                    # Update the token ending in rule_token to use the new rule
                    rule_body_symbols[i] = custom_rule_name

            # Some tokens in rule_body_symbols may have been updated
            # Regardless, we untokenize the rule_body_symbols back into a
            # string rule_body, where tokens are separated by spaces
            new_rule_body = ' '.join(rule_body_symbols)

            # Update the rule body list to use the (potentially new) rule body
            rule_bodies[rule_body_index] = new_rule_body

# Mutates the rule map to search for all regex + expressions
# Adds a new rule corresponding to the + expression, and updates each rule
# containing a + expression to point to the newly created rule
#
# Example:
# program := expr/+
# =>
# program := _expr_plus
# _expr_plus := expr | _expr_plus expr
# If any other rules had expr/+, they would also point to _expr_plus
def handle_plus_rules(rule_map):
    plus_rule_token = '/+'
    plus_rule_name_fn = lambda s: '_%s_plus' % s
    plus_rule_builder_fn = lambda s, n: ['%s %s' % (n, s), s]
    handle_custom_rules(rule_map, plus_rule_token, plus_rule_name_fn, plus_rule_builder_fn)

# Mutates the rule map to search for all regex * expressions
# Adds a new rule corresponding to the * expression, and updates each rule
# containing a * expression to point to the newly created rule
#
# Example:
# program := expr/*
# =>
# program := _expr_star
# _expr_star := /eps | _expr_star expr
# If any other rules had expr/*, they would also point to _expr_star
def handle_star_rules(rule_map):
    star_rule_token = '/*'
    star_rule_name_fn = lambda s: '_%s_star' % s
    star_rule_builder_fn = lambda s, n: ['%s %s' % (n, s), '/eps']
    handle_custom_rules(rule_map, star_rule_token, star_rule_name_fn, star_rule_builder_fn)

# Mutates the rule map to search for all regex ? expressions
# Adds a new rule corresponding to the ? expression, and updates each rule
# containing a ? expression to point to the newly created rule
#
# Example:
# program := expr?
# =>
# program := _expr_one_or_none
# _expr_one_or_none := expr | /eps
# If any other rules had expr/?, they would also point to _expr_one_or_none
def handle_question_rules(rule_map):
    question_rule_token = '/?'
    question_rule_name_fn = lambda s: '_%s_one_or_none' % s
    question_rule_builder_fn = lambda s, n: [s, '/eps']
    handle_custom_rules(rule_map, question_rule_token, question_rule_name_fn, question_rule_builder_fn)

# Turns the list of rules (as strings) into a rule map
# Maps the start nonterminal of a rule to a list of strings of its bodies
# There are only multiple rule bodies if there are | statements in the rule
def get_rule_map(rules):
    rule_map = {}
    for rule in rules:
        rule_name, rule_body = rule.split(':=')
        rule_name, rule_body = rule_name.strip(), rule_body.strip()
        rule_map[rule_name] = [body.strip() for body in rule_body.split('|')]
    return rule_map

# Takes in a list where some rules are split among multiple lines and
# coalesces them so that each rule belongs to one line (one entry of rules)
def coalesce_rules(rules):
    rule_idx, ptr = 0, 1
    while rule_idx < len(rules):
        # rule_idx points to a real rule, and ptr points directly after that
        # Loop through and add this rule's | statements to the rule
        while ptr < len(rules) and ':=' not in rules[ptr]:
            rules[rule_idx] += ' ' + rules[ptr]
            ptr += 1

        # Now, the real rule has been updated to include all if its
        # | statements, and ptr points to the next real rule OR
        # it points past the end of the list
        # Set rule_idx to point to the next real rule, and ptr to points
        # directly after that to reset our loop invariant
        rule_idx = ptr
        ptr = ptr + 1

    # Finally, prune out all | lines, since they were not removed
    # in the above loop
    return [rule for rule in rules if ':=' in rule]

# Input lines starting with a # are comment lines and should be ignored
# Ignore all empty lines and lines containing only whitespace
def is_valid_line(line):
    line = line.strip()
    return line != '' and line[0] != '#'

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python3 convert.py <.txt> <.json>')
        exit()
    else:
        main(sys.argv[1], sys.argv[2])
