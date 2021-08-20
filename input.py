import json
from grammar import *

"""
Utilities for creating a json grammar file from an internal grammar rep. No longer used. 
"""

def parse_input(file_name):
    # Load the JSON dictionary
    f = open(file_name, 'r')
    j = f.read()
    d = json.loads(j)

    # Create configuration options and grammar
    config = d['config']
    config['TERMINALS'] += [''] # Add in the epsilon terminal implicitly
    grammar = grammar_from_dict(d['grammar'], config)

    # Clean the terminals configuration option to double quote terminals
    clean_terminals(config)
    return config, grammar

def clean_terminal(terminal):
    # The epsilon terminal should not appear in quotes
    if len(terminal) == 0:
        return terminal
    return '"%s"' % terminal

def clean_terminals(config):
    config['TERMINALS'] = [clean_terminal(t) for t in config['TERMINALS']]

def grammar_from_dict(grammar_dict , config):
    start, rules = grammar_dict['start'], grammar_dict['rules']
    grammar = Grammar(start)
    for rule in rules:
        rule_start, rule_bodies = rule['start'], rule['bodies']
        for rule_body in rule_bodies:
            rule : Rule = Rule(rule_start)
            clean_body = []
            for symbol in rule_body:
                if symbol in config['TERMINALS']:
                    clean_body.append(clean_terminal(symbol))
                else:
                    clean_body.append(symbol)
                rule.add_body(clean_body)
            grammar.add_rule(rule)
    return grammar