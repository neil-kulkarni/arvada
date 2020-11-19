import sys

f = open('output.txt', 'r')
stats = f.read().split('---\n')
stats = stats[:-1]
stat_dict = {}
for stat in stats:
	lines = stat.split('\n')
	file_start = lines[0][:lines[0].find('.log') - 2]
	rules = int(lines[1][6:])
	terms = int(lines[2][6:])
	ntrms = int(lines[3][6:])
	if not file_start in stat_dict:
		stat_dict[file_start] = (rules, terms, ntrms)
	else:
		erules, eterms, entrms = stat_dict[file_start]
		stat_dict[file_start] = (erules + rules, eterms + terms, entrms + ntrms)

new_stat_dict = {}
for file_start, tup in stat_dict.items():
	new_stat_dict[file_start] = (float(tup[0])/10, float(tup[1])/10, float(tup[2])/10)

for file_start, tup in new_stat_dict.items():
	print(file_start)
	print('Rules:', int(tup[0]))
	print('Terms:', int(tup[1]))
	print('Ntrms:', int(tup[2]))
	print('---')
