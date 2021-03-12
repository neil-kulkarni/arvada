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


        print(f"Hello at the start of iteration {it}")
        print(rule_map.get('__m0_star_70'))
        print([rule for rule in rule_map['m0'] if 'n977' in rule.expansion])

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






def main(gram_file_name: str):
    grammar_contents = open(gram_file_name).read()
    import sys
    sys.setrecursionlimit(10000)
    generic_rules = GenericRuleCreator(grammar_contents).get_rules()
    smaller = aggressively_minimize(generic_rules)
    #tag_unproductive(smaller)
    exit(1)
    print_nicely(smaller, open(gram_file_name).readlines())


if __name__ == '__main__':
    main("tinyc-gram.lark")