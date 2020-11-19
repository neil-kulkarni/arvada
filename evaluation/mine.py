import sys
from grammar import Grammar
from grammar import Rule

def get_grammar_str(f):
	line = f.readline()
	while not line.startswith('Initial Grammar Created'): line = f.readline()
	line = f.readline()
	grammar_str = ''
	while not line.startswith('Precision set'):
		grammar_str += line
		line = f.readline()
	return grammar_str.strip()

def split_rules(gram_str):
	rule_strs = []
	curr_rule = ''
	for line in gram_str.split('\n'):
		if line.startswith('   '):
				curr_rule += str(line) + '\n'
		else:
				rule_strs.append(str(curr_rule).strip())
				curr_rule = str(line) + '\n'
	
	rule_strs.append(str(curr_rule).strip())
	return rule_strs[1:]

def create_rule_obj(rule_str):
	bodies = rule_str.split('\n')
	ind = bodies[0].find(':')
	start_nt, start_rule = bodies[0][:ind], bodies[0][ind + 1:]
	rule = Rule(start_nt)
	rule.add_body(start_rule.strip().split())
	for body in bodies[1:]:
		ind = body.find('|')
		front, rest = body[:ind + 1], body[ind + 1:]
		rule.add_body(rest.strip().split())
	return rule

def compute_stats(grammar):
	rule_count = 0
	terminals = set()
	nonterminals = set()

	for rule_start, rule_obj in grammar.rules.items():
		nonterminals.add(rule_start)
		num_bodies = 0
		for body in rule_obj.bodies:
			if not (len(body) == 1 and '"' in body[0]):
				num_bodies += 1
			for sym in body:
				if '"' in sym:
					terminals.add(sym)
				else:
					nonterminals.add(sym)
		if num_bodies == 0:
			rule_count += 1
		else:
			rule_count += num_bodies

	print('Rules:', rule_count - 1)
	print('Terms:', len(terminals))
	print('NTrms:', len(nonterminals) - 1)
	print('---')

def print_stats(file_name):
	f = open(file_name, 'r')
	gram_str = get_grammar_str(f)
	rules = split_rules(gram_str)
	rules = [create_rule_obj(rule) for rule in rules]
	start_rule, rules = rules[0], rules[1:]
	start_nt = start_rule.bodies[0][0]
	grammar = Grammar(start_nt)
	for rule in rules:
		grammar.add_rule(rule)
	print(file_name)
	compute_stats(grammar)

for file_name in sys.argv[1:]:
	print_stats(file_name)

