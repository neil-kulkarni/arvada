import random
import sys
from typing import List

from grammar import Grammar, Rule
from oracle import ExternalOracle, ParseException
from parse_tree import ParseNode, fixup_terminal

import string

from replacement_utils import get_strings_with_replacement, nt_in_tree

"""
I'm sorry this code is so so so ugly. 

What this does is try to generalize tokens to larger classes. The steps are

1. single digit -> all digits -> all integers -> all digit sequences -> alphanumeric
2. lowercase letter -> all lowercase (sequences) -> all letters (sequences) -> alphanumeric (sequences)
similarly for lowercase and all letters.

There must be a way to reduce code duplication here. I'm not even sure the expansion
to a single token is ever used.... anywhoo, sorry. 
"""

digit_type = 0
uppercase_type = 1
lowercase_type = 2
letter_type = 3
whitespace_type = 4

MAX_SAMPLES = 10

whitsepace_map = []

def rules_to_add(rule_start):
    if rule_start == "":
        print("WARNING: Calling rules_to_add with the empty string",file= sys.stderr)
        exit(1)
    if rule_start == "tdigit":
        r = Rule(rule_start)
        for i in range(10):
            r.add_body([f'"{i}"'])
        return [r]
    if rule_start == "tdigits":
        r = Rule(rule_start)
        r.add_body(['tdigit'])
        r.add_body(["tdigit", "tdigits" ])
        return [r, rules_to_add("tdigit")[0]]
    if rule_start == "tinteger":
        r = Rule(rule_start)
        r.add_body(['tdigit'])
        r.add_body(["tnzdigit", "tdigits" ])
        nz = Rule("tnzdigit")
        for i in range(1, 10):
            nz.add_body([f'"{i}"'])
        return [r, nz] + rules_to_add("tdigits")
    if rule_start == "talphanum":
        r = Rule(rule_start)
        for c in string.ascii_letters + string.digits:
            r.add_body(([f'"{c}"']))
        return [r]
    if rule_start == "tletter":
        r = Rule(rule_start)
        for c in string.ascii_letters:
            r.add_body(([f'"{c}"']))
        return [r]
    if rule_start == "tlower":
        r = Rule(rule_start)
        for c in string.ascii_lowercase:
            r.add_body(([f'"{c}"']))
        return [r]
    if rule_start == "tupper":
        r = Rule(rule_start)
        for c in string.ascii_uppercase:
            r.add_body(([f'"{c}"']))
        return [r]
    if rule_start == "tuppers":
        r = Rule(rule_start)
        r.add_body(['tupper'])
        r.add_body((['tupper', 'tuppers']))
        return [r] + rules_to_add('tupper')
    if rule_start == "tlowers":
        r = Rule(rule_start)
        r.add_body(['tlower'])
        r.add_body((['tlower', 'tlowers']))
        return [r] + rules_to_add('tlower')
    if rule_start == "tletters":
        r = Rule(rule_start)
        r.add_body(['tletter'])
        r.add_body((['tletter', 'tletters']))
        return [r] + rules_to_add('tletter')
    if rule_start == "talphanums":
        r = Rule(rule_start)
        r.add_body(['talphanum'])
        r.add_body((['talphanum', 'talphanums']))
        return [r] + rules_to_add('talphanum')
    if rule_start.startswith("twhitespaces"):
        idx = int(rule_start[12:])
        single = f"twhitespace{idx}"
        r = Rule(rule_start)
        r.add_body([single])
        r.add_body(([single, rule_start]))
        return [r] + rules_to_add(single)
    if rule_start.startswith("twhitespace"):
        idx = int(rule_start[11:])
        r = Rule(rule_start)
        for charset, charset_idx in whitsepace_map:
            if charset_idx == idx:
                for c in charset:
                    r.add_body(([f'"{c}"']))
                return [r]
        else:
            print("I didn't find the right rules to add for whitespace!!!!")
            exit(1)

    return []


def try_strings(oracle: ExternalOracle, candidates: List[str]):

    for candidate in candidates:
        try:
            oracle.parse(candidate)
        except ParseException:
            return False
    return True


def generalize_whitespace_in_rule(oracle: ExternalOracle, grammar: Grammar, trees: List[ParseNode], rule_start: str, body_idxs: List[int]):

    existing_bodies = [fixup_terminal(body[0]) for idx, body in enumerate(grammar.rules[rule_start].bodies) if idx in body_idxs]

    ok_chars = set([c for body in existing_bodies for c in body])
    other_chars = set([c for c in string.whitespace if c not in ok_chars])

    for c in other_chars:
        c_ok = True
        for tree in [tree for tree in trees if nt_in_tree(tree, rule_start)]:
            candidates = get_strings_with_replacement(tree, rule_start, c)
            if not try_strings(oracle, candidates):
                c_ok = False
                break
        if c_ok:
            ok_chars.add(c)

    longer_whitespaces = []

    for i in range(MAX_SAMPLES):
        leng = random.randint(2, 10)
        ws_str = random.sample(ok_chars, leng)
        longer_whitespaces.append(ws_str)


    for tree in [tree for tree in trees if nt_in_tree(tree, rule_start)]:
        candidates = get_strings_with_replacement(tree, rule_start, longer_whitespaces)
        if not try_strings(oracle, candidates):
            expand_ok = False
            break

    if len(ok_chars) == 1 and not expand_ok:
        return [], ""

    charset_idx = len(whitsepace_map)
    for charset, idx in whitsepace_map:
        if charset == ok_chars:
            charset_idx = idx
            break

    if expand_ok:
        replace_str = f'twhitespaces{charset_idx}'
    else:
        replace_str = f'twhitespace{charset_idx}'

    return body_idxs, replace_str


def generalize_digits_in_rule(oracle: ExternalOracle, grammar: Grammar, trees: List[ParseNode], rule_start: str, body_idxs: List[int]):

    existing_bodies = [fixup_terminal(body[0]) for idx, body in enumerate(grammar.rules[rule_start].bodies) if idx in body_idxs]

    if all(len(body) == 1 for body in existing_bodies):
        single_digit_candidates = [s for s in string.digits if s not in existing_bodies]
    else:
        single_digit_candidates = []

    integer_candidates = []
    digits_candidates = []
    for i in range(MAX_SAMPLES):
        first_dig = random.choice("123456789")
        leng = random.randint(1, 10)
        other_digs  = random.sample(string.digits, leng)
        integer_candidates.append(first_dig + ''.join(other_digs))
        digits_candidates.append('0' + ''.join(other_digs))

    digit_ok = True if single_digit_candidates else False
    ints_ok = True
    digits_ok = True

    for tree in [tree for tree in trees if nt_in_tree(tree, rule_start)]:
        if digit_ok:
            candidates = get_strings_with_replacement(tree, rule_start, single_digit_candidates)
            if not try_strings(oracle, candidates):
                digit_ok = False
                ints_ok = False
                digits_ok = False
                break
        if ints_ok:
            candidates = get_strings_with_replacement(tree, rule_start, integer_candidates)
            if not try_strings(oracle, candidates):
                ints_ok = False
                digits_ok = False
        if digits_ok:
            candidates = get_strings_with_replacement(tree, rule_start, digits_candidates)
            if not try_strings(oracle, candidates):
                digits_ok = False

    replace_str = ''
    if digits_ok:
        replace_str = 'tdigits'
    elif ints_ok:
        replace_str = 'tinteger'
    elif digit_ok:
        replace_str = 'tdigit'
    if replace_str == "":
        return [], ""
    else:
        return body_idxs, replace_str


def generalize_letters_in_rule(oracle: ExternalOracle, grammar: Grammar, trees: List[ParseNode], rule_start: str, body_idxs: List[int], expansion_type):

    existing_bodies = [fixup_terminal(body[0]) for idx, body in enumerate(grammar.rules[rule_start].bodies) if idx in body_idxs]

    if expansion_type == lowercase_type:
        expansion_set = string.ascii_lowercase
    elif expansion_type == uppercase_type:
        expansion_set = string.ascii_uppercase
    else:
        expansion_set = string.ascii_letters


    if all(len(body) == 1 for body in existing_bodies):
        single_candidates = [s for s in expansion_set if s not in existing_bodies]
        if len(single_candidates) > MAX_SAMPLES:
            single_candidates = random.sample(single_candidates, MAX_SAMPLES - 1)
    else:
        single_candidates = []

    multi_candidates = [''.join(random.sample(expansion_set, random.randint(2, 10))) for _ in range(MAX_SAMPLES)]

    expand_1_ok = True if single_candidates else False
    expand_multi_ok = True

    for tree in [tree for tree in trees if nt_in_tree(tree, rule_start)]:
        if expand_1_ok:
            # we only get in here if we have
            candidates = get_strings_with_replacement(tree, rule_start, single_candidates)
            if not try_strings(oracle, candidates):
                expand_1_ok = False
                expand_multi_ok = False
                break
        if expand_multi_ok:
            candidates = get_strings_with_replacement(tree, rule_start, multi_candidates)
            if not try_strings(oracle, candidates):
                expand_multi_ok = False
                if not expand_1_ok: break

    if expand_multi_ok:
        if expansion_type == lowercase_type:
            return body_idxs, 'tlowers'
        elif expansion_type == uppercase_type:
            return body_idxs, 'tuppers'
        else:
            return body_idxs, 'tletters'
    elif expand_1_ok:
        if expansion_type == lowercase_type:
            return body_idxs, 'tlower'
        elif expansion_type == uppercase_type:
            return body_idxs, 'tupper'
        else:
            return body_idxs, 'tletter'
    else:
        return [], ""



def generalize_to_alphanum(oracle: ExternalOracle, grammar: Grammar, trees: List[ParseNode], rule_start: str, body_idxs: List[int]):

    existing_bodies = [fixup_terminal(body[0]) for idx, body in enumerate(grammar.rules[rule_start].bodies) if idx in body_idxs]

    expansion_set = string.ascii_letters  + string.digits

    if all(len(body) == 1 for body in existing_bodies):
        single_candidates = [s for s in expansion_set if s not in existing_bodies]
        if len(single_candidates) > MAX_SAMPLES:
            single_candidates = random.sample(single_candidates, MAX_SAMPLES - 1)
    else:
        single_candidates = []


    multi_candidates = [''.join(random.sample(expansion_set, random.randint(2, 10))) for _ in range(MAX_SAMPLES)]
    # JIC we're missing a number or lower case or upper case... :)
    multi_candidates.append("a1Te3t")


    expand_1_ok = True if single_candidates else False
    expand_multi_ok = True

    for tree in [tree for tree in trees if nt_in_tree(tree, rule_start)]:
        if expand_1_ok:
            # we only get in here if we have
            candidates = get_strings_with_replacement(tree, rule_start, single_candidates)
            if not try_strings(oracle, candidates):
                expand_1_ok = False
                expand_multi_ok = False
                break
        if expand_multi_ok:
            candidates = get_strings_with_replacement(tree, rule_start, multi_candidates)
            if not try_strings(oracle, candidates):
                expand_multi_ok = False
                if not expand_1_ok: break

    if expand_multi_ok:
        return body_idxs, 'talphanums'
    elif expand_1_ok:
        return body_idxs, 'talphanum'
    else:
        return [], ""


def expand_tokens(oracle : ExternalOracle, grammar : Grammar, trees: List[ParseNode]):
    """
    The idea is to expand the terminal tokens of the grammar as permited by "oracle".

    Currently only expands alphanumerics (not whitespace or punctuation)
    """
    rule_starts = set(grammar.rules.keys())
    def is_terminal(elem):
        return elem not in rule_starts

    original_rules = list(grammar.rules.items())
    for rule_start, rule in original_rules:
        idxs_to_replace = set()
        bodies_to_add = set()
        bodies = rule.bodies
        terminal_body_idxs = [idx for idx, body in enumerate(bodies) if len(body) == 1 and is_terminal(body[0])]
        if len(terminal_body_idxs) == 0:
            # Nothing <t>o expand here, folks
            continue
        idxs_by_type = classify_terminals_by_type(bodies, terminal_body_idxs)

        # Digit expansion...
        if idxs_by_type[digit_type]:
            digit_bodies_to_replace, replace_str = generalize_digits_in_rule(oracle, grammar, trees, rule_start, idxs_by_type[digit_type])
            if replace_str != "":
                if "digit" in replace_str:
                    t_r, r_str = generalize_to_alphanum(oracle, grammar, trees, rule_start, idxs_by_type[digit_type])
                    if r_str != "":
                        digit_bodies_to_replace = t_r
                        replace_str = r_str
                idxs_to_replace.update(digit_bodies_to_replace)
                bodies_to_add.add(replace_str)

        for l_type in [uppercase_type, lowercase_type, letter_type]:
            if idxs_by_type[l_type]:
                letter_bodies_to_replace, replace_str = generalize_letters_in_rule(oracle, grammar, trees, rule_start, idxs_by_type[l_type], l_type)
                if replace_str != "":
                    if l_type != letter_type:
                        lbt_r, r_str = generalize_letters_in_rule(oracle, grammar, trees, rule_start, idxs_by_type[l_type], letter_type)
                        if r_str != "":
                            letter_bodies_to_replace = lbt_r
                            replace_str = r_str
                            lbt_r, r_str = generalize_to_alphanum(oracle, grammar, trees, rule_start,
                                                                      idxs_by_type[l_type])
                            if r_str != "":
                                letter_bodies_to_replace = lbt_r
                                replace_str = r_str

                    idxs_to_replace.update(letter_bodies_to_replace)
                    bodies_to_add.add(replace_str)

            if idxs_by_type[whitespace_type]:
                whitespace_bodies_to_replace, replace_str = generalize_to_alphanum(oracle, grammar, trees, rule_start,
                                                                                 idxs_by_type[whitespace_type])
                if replace_str != "":
                    idxs_to_replace.update(whitespace_bodies_to_replace)
                    bodies_to_add.add(replace_str)

        for body_idx in sorted(idxs_to_replace, reverse = True):
            rule.bodies.pop(body_idx)
        for nt_name in bodies_to_add:
            rule.add_body([nt_name])
            rs_to_add = rules_to_add(nt_name)
            for r_to_add in rs_to_add:
                if r_to_add.start not in grammar.rules:
                    grammar.add_rule(r_to_add)

    return grammar


def classify_terminals_by_type(bodies, terminal_body_idxs):
    """
    Find the upper (generalizable) character class for all the terminal bodies in bodies
    """
    idxs_by_type = {digit_type: [], uppercase_type: [], lowercase_type: [], letter_type: [], whitespace_type: []}
    for idx in terminal_body_idxs:
        body = bodies[idx][0]
        body = fixup_terminal(body)
        if all(c in string.digits for c in body):
            idxs_by_type[digit_type].append(idx)
        elif all(c in string.whitespace for c in body):
            idxs_by_type[whitespace_type].append(idx)
        elif all(c in string.ascii_letters for c in body):
            if all(c in string.ascii_uppercase for c in body):
                idxs_by_type[uppercase_type].append(idx)
            elif all(c in string.ascii_lowercase for c in body):
                idxs_by_type[lowercase_type].append(idx)
            else:
                idxs_by_type[letter_type].append(idx)
    return idxs_by_type
