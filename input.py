import json
from generator import *

def parse_input(file_name):
    # Load the JSON dictionary
    f = open(file_name, 'r')
    j = f.read()
    d = json.loads(j)

    # Create configuration options and grammar
    config = d['config']
    config['TERMINALS'] += [''] # Add in the epsilon terminal implicitly
    gen, grammar = generator_from_dict(d['grammar'], config)

    # Clean the terminals configuration option to double quote terminals
    clean_terminals(config)
    return config, gen, grammar

def clean_terminal(terminal):
    # The epsilon terminal should not appear in quotes
    if len(terminal) == 0:
        return terminal
    return '"%s"' % terminal

def clean_terminals(config):
    config['TERMINALS'] = [clean_terminal(t) for t in config['TERMINALS']]

def generator_from_dict(grammar_dict, config):
    start, rules = grammar_dict['start'], grammar_dict['rules']
    grammar_node = GrammarNode(config, start, [])
    for rule in rules:
        rule_start, rule_bodies = rule['start'], rule['bodies']
        for rule_body in rule_bodies:
            rule_node = RuleNode(config, rule_start, [])
            for symbol in rule_body:
                if symbol in config['TERMINALS']:
                    symbol_node = SymbolNode(config, clean_terminal(symbol), True)
                else:
                    symbol_node = SymbolNode(config, symbol, False)
                rule_node.children.append(symbol_node)
            grammar_node.children.append(rule_node)
    grammar_gen = GrammarGenerator(config, grammar_node)
    grammar = grammar_gen.generate_grammar()
    return grammar_gen, grammar
