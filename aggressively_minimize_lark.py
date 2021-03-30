from collections import defaultdict
from typing import Set, Dict, List

from sample_lark import GenericRule, GenericRuleCreator, get_rule_map, GrammarStats
import sys

def aggressively_minimize(generic_rules: Set[GenericRule]):

    """
    Modifies the rule list to replace any occ of old_nt with the (single or list of tokens)
    List[str]
    """
    def replace_nt(g: Dict[str, List[GenericRule]], old_nt: str, replacement: List[str]):
        is_epsilon_replacement = (replacement == [])
        # Remove old_nt
        g.pop(old_nt)
        for rule_lst in g.values():
            for rule in rule_lst:
                orig_exp_len = len(rule.expansion)
                for i in reversed(range(len(rule.expansion))):
                    if rule.expansion[i] == old_nt:
                        rule.expansion.pop(i)
                        if is_epsilon_replacement and orig_exp_len > 1:
                            # don't add anything back
                            pass
                        else:
                            for elem in reversed(replacement):
                                rule.expansion.insert(i, elem)

    def get_rule_set(my_start: str, rules: List[GenericRule]):
        rule_set = set()
        start_const = "__MYSELF__"
        for rule in rules:
            expansion = rule.expansion[:]
            for i in range(len(expansion)):
                if expansion[i] == my_start:
                    expansion[i] = start_const
            rule_set.add(tuple(expansion))
        sorted_rules = tuple(sorted(rule_set))
        return sorted_rules


    rule_map = get_rule_map(generic_rules)

    old_num_rules = len([rule for start in rule_map for rule in rule_map[start]])
    it = 0
    while True:
        it += 1

        """
        (1) If there is any nonterminal that is defined by a single rule
        with a single token, delete the key from the grammar and
        replace all references to that key with the token instead.
        """
        nts = set([key for key in rule_map.keys() if key.islower()])
        for nt in nts:
            if nt == 'start':
                continue
            if len(rule_map[nt]) == 1:
                expansion = rule_map[nt][0].expansion
                if len(expansion) == 1 or len(expansion) == 0:
                    replacement = expansion
                    replace_nt(rule_map, nt, replacement)
        new_num_rules = len([rule for start in rule_map for rule in rule_map[start]])

        """
        (2) If there are multiple keys with the same rule set, choose one,
    delete the rest, and update the references to other keys with
    the chosen one.
        """
        nts = set([key for key in rule_map.keys() if key.islower()])
        rule_set_equiv_map = defaultdict(list)

        for nt in nts:
            if nt == 'start':
                continue
            rule_set = get_rule_set(nt, rule_map[nt])
            rule_set_equiv_map[rule_set].append(nt)
        for rule_set, rule_starts in rule_set_equiv_map.items():
            if len(rule_starts) > 1:
                replacer = rule_starts[0]
                replacees = rule_starts[1:]
                for replacee in replacees:
                    replace_nt(rule_map, replacee, [replacer])


        """
        Remove duplicate rule bodies
        """
        nts = set([key for key in rule_map.keys() if key.islower()])
        for nt in nts:
            if nt == 'start':
                continue
            rule_bodies = set()
            new_rules = []
            for rule in rule_map[nt]:
                body = tuple(rule.expansion)
                if body not in rule_bodies:
                    rule_bodies.add(body)
                    new_rules.append(rule)
            rule_map[nt] = new_rules


        """
        (5) If there is any key that is referred to on a single rule on a
            single token, and the key is defined by just one rule, delete
            the key from the grammar and replace the reference to the
            key with the rule.
        """
        all_nts = set(rule_map.keys())
        nt_refs = defaultdict(int)
        for nt in all_nts:
            for rule in rule_map[nt]:
                for elem in rule.expansion:
                    if elem in all_nts:
                        nt_refs[elem] += 1

        nts = set([key for key in rule_map.keys() if key.islower()])
        for nt in nts:
            if len(rule_map[nt]) == 1 and nt_refs[nt] == 1:
                # defined by just one rule and referred to at only one location
                replace_nt(rule_map, nt, rule_map[nt][0].expansion)


        if new_num_rules == old_num_rules:
            break
        else:
            old_num_rules = new_num_rules
    return rule_map


def fixup_stars(rule_map: Dict[str, List[GenericRule]]):
    star_replacements = {}
    for nt in rule_map:
        if "_star_" in nt:
            expansions = [rule.expansion for rule in rule_map[nt]]
            assert(len(expansions) == 2)
            len_1_exp = [exp for exp in expansions if len(exp) == 1][0]
            len_2_exp = [exp for exp in expansions if len(exp) == 2][0]
            assert(len_2_exp[0] == nt)
            assert(len_2_exp[1] == len_1_exp[0])
            star_replacements[nt] = len_1_exp[0]

    for nt in rule_map:
        if "_star_" in nt:
            continue
        expansions = [rule.expansion for rule in rule_map[nt]]
        expansions_with_star = [exp for exp in expansions if len(exp) == 3 and "_star_" in exp[1]]
        final_expansions = set([tuple(exp) for exp in expansions])
        for exp in expansions_with_star:
            t_exp = tuple(exp)
            t_pair_exp = tuple([exp[0], exp[2]])
            if t_pair_exp not in final_expansions:
                print(final_expansions)
                print(t_exp)
                print(t_pair_exp)
            assert (t_pair_exp in final_expansions)
            final_expansions.remove(t_exp)
            final_expansions.remove(t_pair_exp)
            final_expansions.add((exp[0], ":!!!:" + star_replacements[exp[1]] + "*", exp[2]))
        print(nt, "-->", final_expansions)

def print_nicely(rule_map, grammar_lines):
    def fixup_nt(nt_name: str):
        if nt_name.startswith("__"):
            return nt_name[2:]
        else:
            return nt_name
    def fixup_term(term_contents: str):
        if not term_contents.startswith("(?:"):
            if term_contents.startswith(("\\\\")):
                return f'MANFIX({term_contents})'
            return '"' + term_contents + '"'
        else:
            cur_contents = term_contents
            ret_strings = []
            while cur_contents.startswith(("(?:")):
                last_or = cur_contents.rfind("|")
                alternate = cur_contents[last_or+1:-1]
                ret_strings.insert(0, fixup_term(alternate))
                cur_contents = cur_contents[3:last_or]
            ret_strings.insert(0, fixup_term(cur_contents))
            return '(' + ' | '.join(ret_strings) + ")"

    def fixup_expansion(expansion: List[str]):
        print_lst = []
        for elem in expansion:
            if elem not in rule_map:
                print_lst.append(fixup_term(elem))
            else:
                print_lst.append(fixup_nt(elem))
        return " ".join(print_lst)

    def print_class(nt):
        for line in grammar_lines:
            if line.startswith(nt):
                print(line.rstrip())
                break

    for nt in rule_map:
        if nt.startswith("CLASS"):
            print_class(nt)
        else:
            first = rule_map[nt][0]
            rest = rule_map[nt][1:]
            print(f"{fixup_nt(nt)}: {fixup_expansion(first.expansion)}")
            for rule in rest:
                print(f"| {fixup_expansion(rule.expansion)}")

def tag_unproductive(rule_map):
    nts = set([key for key in rule_map.keys() if key.islower()])
    all_rules = [rule for start in rule_map for rule in rule_map[start]]
    productive_rules = set()
    def nt_is_productive(nt):
        all_rules_with_nt = rule_map[nt]
        return any(rule in productive_rules for rule in all_rules_with_nt)

    cur_len = len(productive_rules)
    prev_len = -1
    while cur_len != prev_len:
        print(f"going in because: {cur_len} > {prev_len}")
        prev_len = cur_len
        for rule in all_rules:
            if rule in productive_rules:
                continue
            elif rule.start not in nts:
                productive_rules.add(rule)
            else:
                all_productive = True
                for elem in rule.expansion:
                    if elem in nts:
                        is_pro = nt_is_productive(elem)
                        if not is_pro:
                            all_productive = False
                            break
                if all_productive:
                    productive_rules.add(rule)
        cur_len = len(productive_rules)

    print(f"Num productive: {len(productive_rules)}, num total: {len(all_rules)}")
    # for rule in productive_rules:
    #     print(rule)
    # print(rule_map[])


def directly_derivable_relationships(rule_map: Dict[str, List[GenericRule]]):
    nullable = set()
    new_nullables = True
    while new_nullables:
        old_len = len(nullable)
        new_nullables = False
        for nt in rule_map.keys():
            if nt in nullable:
                continue
            for expansion in [rule.expansion for rule in rule_map[nt]]:
                if expansion == []:
                    nullable.add(nt)
                elif all(elem in nullable for elem in expansion):
                    nullable.add(nt)
        new_len = len(nullable)
        if new_len > old_len:
            new_nullables = True

    directly_derivable = defaultdict(set)
    updated_derivables = True
    while updated_derivables:
        old_len = sum([len(v) for v in directly_derivable.values()])
        for nt in [key for key in rule_map.keys() if key.islower()]:
            for expansion in [rule.expansion for rule in rule_map[nt]]:
                if len(expansion) == 1:
                    if expansion[0] in rule_map.keys() and expansion[0].islower():
                        directly_derivable[nt].add(expansion[0])
                        directly_derivable[nt].update(directly_derivable[expansion[0]])
                else:
                    for i in range(len(expansion)):
                        if all(elem in nullable for elem in expansion[:i] + expansion[i+1:]):
                            if expansion[i] in rule_map.keys() and expansion[i].islower():
                                directly_derivable[nt].add(expansion[i])
                                directly_derivable[nt].update(directly_derivable[expansion[i]])

        new_len = sum([len(v) for v in directly_derivable.values()])
        updated_derivables = new_len > old_len

    return directly_derivable, nullable

def fix_direct_derivability(nt, rule_map, directly_derivable: Dict[str, Set[str]], nullable: Set[str]):

    def is_direct_derivable_from_rule(nt: str, rule):
        expansion = rule.expansion
        derivable_posns = set()
        for i in range(len(expansion)):
            if all(elem in nullable for elem in expansion[:i] + expansion[i + 1:]):
                if nt in directly_derivable[expansion[i]]:
                    derivable_posns.add(i)
        return derivable_posns

    def expansions_minus_derivable_to(nt: str, nt_we_dont_want_derived: str, rule_map_so_far, queue):
        new_name = f"{nt}_minus_{nt_we_dont_want_derived}"
        if new_name in queue:
            return new_name, True
        else:
            queue.append(new_name)
        # Let's make new rules with nt replaced with nt_minus_nt_we_dont_want_derived
        my_rules = rule_map[nt]
        at_least_one_rule = False
        for rule in my_rules:
            positions_where_directly_derivable = is_direct_derivable_from_rule(nt_we_dont_want_derived, rule)
            if positions_where_directly_derivable:
                for posn in positions_where_directly_derivable:
                    derivable_elem = rule.expansion[posn]
                    if derivable_elem == nt_we_dont_want_derived:
                        # this is exactly what we want to get rid of
                        continue
                    else:
                        new_nt_name, there_was_something = expansions_minus_derivable_to(derivable_elem,
                                                                                         nt_we_dont_want_derived,
                                                                                         rule_map_so_far,
                                                                                         queue)
                        if there_was_something:
                            new_expansion = rule.expansion[:posn] + [new_nt_name] + rule.expansion[posn+1:]
                            at_least_one_rule = True
                            if new_name not in rule_map_so_far:
                                rule_map_so_far[new_name] = []
                            rule_map_so_far[new_name].append(GenericRule(new_name, new_expansion, False))
            else:
                # this rule is totally ok, so we can just add it back
                if new_name not in rule_map_so_far:
                    rule_map_so_far[new_name] = []
                rule_map_so_far[new_name].append(GenericRule(new_name, rule.expansion, rule.is_terminal))
                at_least_one_rule = True

        return new_name, at_least_one_rule

    print(f"Woops, {nt} is directly derivable from itself. Who is bad?")

    print(nullable)

    my_rules = rule_map[nt]
    for rule in my_rules:
        if is_direct_derivable_from_rule(nt, rule):
            print(f"BAD: {rule}")
    exit(1)

    new_rules = {}
    _, at_least_one_rule = expansions_minus_derivable_to(nt, nt, new_rules, [])
    if not at_least_one_rule:
        print("this means this nonterminal can only expand to itself in an infinite loop. You're in trouble+++")
        exit(1)
    rule_map.pop(nt)
    print(new_rules)
    for rule_start, rule_lst in new_rules.items():
        if rule_start == f"{nt}_minus_{nt}":
            rule_map[nt] = [GenericRule(nt, r.expansion, r.is_terminal) for r in rule_lst]
        else:
            rule_map[rule_start] = rule_lst


def fix_all_directly_derivable(rule_map):

    directly_derivable, nullable = directly_derivable_relationships(rule_map)

    for nt in rule_map.keys():
        derivables = directly_derivable[nt]
        if nt in derivables:
            fix_direct_derivability(nt, rule_map, directly_derivable, nullable)
            return True

    return False





def main(gram_file_name: str):
    grammar_contents = open(gram_file_name).read()
    import sys
    sys.setrecursionlimit(10000)
    generic_rules = GenericRuleCreator(grammar_contents).get_rules()
    smaller = aggressively_minimize(generic_rules)
    print_nicely(smaller, open(gram_file_name).readlines())
    while fix_all_directly_derivable(smaller):
        pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        main("tinyc-gram.lark")
    else:
        main(sys.argv[1])
