import functools
import itertools
import random
import time
from typing import Tuple, List, Set
import sys

import numpy as np

from grammar import Grammar
from parse_tree import ParseNode
REPLACE_CONST = '[[:REPLACEME]]'
MAX_SAMPLES = 10

"""
Utilities to sample strings that are in the grammar induced when two nodes in a parse tree are merged. 
"""

def nt_in_tree(tree: ParseNode, nt: str):
    """
    >>> tree_1 = ParseNode('t0', False, [ParseNode('t3', False, [ParseNode('3', True, [])])])
    >>> tree_2 = ParseNode('t0', False, [ParseNode('t1', False, [ParseNode('(', True, [])]), tree_1, ParseNode('t2', False, [ParseNode(')', True, [])])])
    >>> tree_3 = ParseNode('t0', False, [tree_1, ParseNode('t4', False, [ParseNode('*', True, [])]), tree_1])
    >>> nt_in_tree(tree_2, 't1')
    True
    >>> nt_in_tree(tree_1, 't1')
    False
    """
    if tree.payload == nt:
        return True
    return any([nt_in_tree(c, nt) for c in tree.children])

def get_overlaps(larger: List[str], smaller: List[str]):
    """
    ASSUMES: `smaller` is not explicitly contained in `larger`.

    Returns a list of overlaps between the front/back of `larger`
    and the front/back of `smaller`. Each overlap list is a list
    of tuples of (l, s), where l is an index in `larger` and s
    is an index in `smaller` s.t. larger[l] == smaller[s]

    >>> get_overlaps(["a", "b", "c", "d"], ["c", "d", "e"])
    [[(2, 0), (3, 1)]]
    >>> get_overlaps(["a", "b", "c", "d"], ["e", "d", "e"])
    []
    >>> get_overlaps(["a", "b", "c", "d"], ["c", "a", "b"])
    [[(0, 1), (1, 2)]]
    >>> get_overlaps(["a", "b", "c", "a"], ["c", "a", "b"])
    [[(2, 0), (3, 1)], [(0, 1), (1, 2)]]
    >>> get_overlaps(["a", "b", "c", "c"], ["c", "a", "b"])
    [[(3, 0)], [(0, 1), (1, 2)]]
    >>> get_overlaps(["a", "b", "c", "c"], ["c", "d"])
    [[(3, 0)]]
    >>> get_overlaps(["a", "b", "c"], ["d", "a"])
    [[(0, 1)]]
    """
    smaller_idx_1 = 0
    match_1_idxs = []
    for i in range(len(larger)):
        if larger[i] == smaller[smaller_idx_1]:
            match_1_idxs.append((i, smaller_idx_1))
            smaller_idx_1 += 1
        else:
            match_1_idxs = []
            smaller_idx_1 = 0
            if larger[i] == smaller[smaller_idx_1]:
                match_1_idxs.append((i, smaller_idx_1))
                smaller_idx_1 += 1

    smaller_idx_2 = len(smaller) - 1
    match_2_idxs = []
    for i in reversed(range(len(larger))):
        if larger[i] == smaller[smaller_idx_2]:
            match_2_idxs.insert(0, (i, smaller_idx_2))
            smaller_idx_2 -= 1
        else:
            smaller_idx_2 = len(smaller) - 1
            match_2_idxs = []
            if larger[i] == smaller[smaller_idx_2]:
                match_2_idxs.insert(0, (i, smaller_idx_2))
                smaller_idx_2 -= 1
    ret = []
    if match_1_idxs:
        ret.append(match_1_idxs)
    if match_2_idxs:
        ret.append(match_2_idxs)

    return ret

@functools.lru_cache(maxsize=None)
def fixup_terminal(payload):
    if len(payload) >= 3 and payload.startswith('"') and payload.endswith('"'):
        payload = payload[1:-1]
    return payload

def muh_product(lst):
    """
    Because numpy product is really slow for some reason.
    """
    prod = 1
    for e in lst:
        prod *= e
    return prod

#@functools.lru_cache()
def lvl_n_derivable(trees, target_nt, n, max_samples=1000):
    """
    Get the strings that are level-n derivable from the nonterminal `target_nt` in `trees`.
    - Level-0 derivable: strings that are directly derivable from `target_nt` (i.e. that
      literally occur in `trees`
    - Level-n derivable: product of Level-(n-1) derivable strings for each child of `target_nt`

    tree_1:
       t0
       |
       t3
       |
       3

    tree_2:
          t0
        / |  \
      t1  t0  t2
      |   |   |
      (   t3  )
          |
          3

    tree_3:
          t0
        / |  \
      t0  t4  t0
      |   |   |
      t3   *  t3
      |       |
      3       3


    >>> tree_1 = ParseNode('t0', False, [ParseNode('t3', False, [ParseNode('3', True, [])])])
    >>> tree_2 = ParseNode('t0', False, [ParseNode('t1', False, [ParseNode('(', True, [])]), tree_1, ParseNode('t2', False, [ParseNode(')', True, [])])])
    >>> tree_3 = ParseNode('t0', False, [tree_1, ParseNode('t4', False, [ParseNode('*', True, [])]), tree_1])
    >>> trees = [tree_1, tree_2, tree_3]
    >>> lvl_n_derivable(trees, 't0', 0)
    ['3', '(3)', '3*3']
    >>> lvl_n_derivable(trees, 't0', 1)
    ['3', '(3)', '((3))', '(3*3)', '3*3', '3*(3)', '3*3*3', '(3)*3', '(3)*(3)', '(3)*3*3', '3*3*(3)', '3*3*3*3']
    >>> len(lvl_n_derivable(trees, 't0', 2, 10))
    10
    >>> lvl_n_derivable([tree_1, tree_2], 't0', 2)
    ['3', '(3)', '((3))', '(((3)))']
    """
    ret_strs = set()
    for tree in trees:
        def get_str(pn: ParseNode):
            if pn.is_terminal:
                return fixup_terminal(pn.payload)
            else:
                return ''.join([get_str(c) for c in pn.children])
        def process_tree(tree: ParseNode):
             if tree.payload == target_nt:
                if n == 0 or tree.is_terminal:
                    ret_strs.add(get_str(tree))
                else:
                    child_strs = [lvl_n_derivable(trees, c.payload, n-1, max_samples) for c in tree.children]
                    ret_strs.update(sample_from_product_ext(child_strs, max_samples))
             else:
                 for c in tree.children:
                    process_tree(c)
        process_tree(tree)
    if len(ret_strs) > max_samples:
        return random.sample(list(ret_strs), max_samples)
    return list(ret_strs)

def sample_from_product_ext(strings_per_child, num_samples):
    lens_per_child = [len(spc) for spc in strings_per_child]
    prod_size = muh_product(lens_per_child)
    if prod_size < num_samples:
        return [''.join(p) for p in itertools.product(*strings_per_child)]
    else:
        return sample_from_product(strings_per_child, num_samples, lens_per_child, prod_size)


def sample_from_product(strings_per_child, num_samples, lens_per_child, prod_size):
    """
    Uniformly sample n strings from the product of strings_per_child.
    An approcimate test is below.
    >>> a = ['a', 'b', 'c']
    >>> b = ['d', 'e', 'f', 'g']
    >>> c = ['h', 'i']
    >>> all_string_occs = {''.join(p): 0 for p in itertools.product(a,b,c)}
    >>> for i in range(10000):
    ...      samples = sample_from_product([a, b, c ], 12, [3,4,2], 24)
    ...      for sample in samples:
    ...          all_string_occs[sample] += 1
    >>> print([ 0.48 < occ/10000 < 0.52 for occ in all_string_occs.values()])
    [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]
    """
    # fancy math to get efficient sampling.
    # Consider lens_per_child = [3, 4, 2]
    # to map idx to a sample, do (idx % (len(a)*len(b)*len(c)) // (len(b)*len(c)), (idx % (len(b)*len(c))) // len(c), idx % len(c))
    if prod_size > sys.maxsize: prod_size = sys.maxsize//2
    ret_strings = []
    indices = random.sample(range(prod_size), num_samples)
    to_divide = [1 for i in range(len(strings_per_child))]
    for i in reversed(range(len(to_divide) - 1)):
        to_divide[i] = to_divide[i + 1] * lens_per_child[i + 1]
    to_modulo = [prod_size] + to_divide[:-1]
    for idx in indices:
        index_per_child = [(idx % to_modulo[i]) // to_divide[i] for i in range(len(strings_per_child))]
        children_choice = [strings_per_child[i][child_index] for i, child_index in enumerate(index_per_child)]
        ret_strings.append(''.join(children_choice))
    return ret_strings

@functools.lru_cache()
def get_all_replacement_strings(tree: ParseNode, nt_to_replace: str):
    """
    Get all the possible strings derived from `tree` where all possible combinations
    (including the combination of len 0) of instances of `nt_to_replace` are replaced
    by REPLACE_CONST.
    >>> left_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])]), ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> right_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> left_l2 = [ParseNode('t2', False, left_l3)]
    >>> right_l2 = [ParseNode('t2', False, right_l3)]
    >>> big_tree = ParseNode('t0', False, \
                     [ParseNode('t0', False, left_l2), \
                      ParseNode('t4', False, [ParseNode('"*"', True, [])]), \
                      ParseNode('t0', False, right_l2)] \
                     )
    >>> no_occ_tree = ParseNode('t4', False, [ParseNode('"*"', True, [])])
    >>> get_all_replacement_strings(no_occ_tree, 't2')
    ['*']
    >>> one_occ_tree = right_l2[0]
    >>> sorted(get_all_replacement_strings(one_occ_tree,  't2'))
    ['4', '[[:REPLACEME]]']
    >>> three_occ_tree = left_l2[0]
    >>> sorted(get_all_replacement_strings(three_occ_tree, 't2'))
    ['44', '4[[:REPLACEME]]', '[[:REPLACEME]]', '[[:REPLACEME]]4', '[[:REPLACEME]][[:REPLACEME]]']
    >>> sorted(get_all_replacement_strings(big_tree,  't2'))
    ['44*4', '44*[[:REPLACEME]]', '4[[:REPLACEME]]*4', '4[[:REPLACEME]]*[[:REPLACEME]]', '[[:REPLACEME]]*4', '[[:REPLACEME]]*[[:REPLACEME]]', '[[:REPLACEME]]4*4', '[[:REPLACEME]]4*[[:REPLACEME]]', '[[:REPLACEME]][[:REPLACEME]]*4', '[[:REPLACEME]][[:REPLACEME]]*[[:REPLACEME]]']
    """
    replacement_strings = []
    if tree.is_terminal:
        return [fixup_terminal(tree.payload)]

    if tree.payload == nt_to_replace:
        replacement_strings.append(REPLACE_CONST)

    strings_per_child = [get_all_replacement_strings(c, nt_to_replace) for c in tree.children]
    lens_per_child = [len(spc) for spc in strings_per_child]
    prod_size = muh_product(lens_per_child)
    if prod_size > MAX_SAMPLES:
        replacement_strings.extend(sample_from_product(strings_per_child, MAX_SAMPLES, lens_per_child, prod_size))
    else:
        replacement_strings.extend([''.join(p) for p in itertools.product(*strings_per_child)])

    return list(set(replacement_strings))


#@functools.lru_cache()
def get_all_rule_replacement_strs(tree: ParseNode, replacee_rule: Tuple[str, List[str]], replacee_posn: int):
    """
    Get all the possible strings derived from `tree` where all possible combinations
    (including the combination of len 0) of instances of the nonterminal at position
    `replacee_posn` in `replacee_rule` are replaced by REPLACE_CONST.
    >>> left_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])]), ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> right_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> left_l2 = [ParseNode('t2', False, left_l3)]
    >>> right_l2 = [ParseNode('t2', False, right_l3)]
    >>> big_tree = ParseNode('t0', False, \
                     [ParseNode('t0', False, left_l2), \
                      ParseNode('t4', False, [ParseNode('"*"', True, [])]), \
                      ParseNode('t0', False, right_l2)] \
                     )
    >>> no_occ_tree = ParseNode('t4', False, [ParseNode('"*"', True, [])])
    >>> replacee_rule = ('t0', ['t2'])
    >>> replacee_posn = 0
    >>> get_all_rule_replacement_strs(no_occ_tree, replacee_rule, replacee_posn)
    ['*']
    >>> one_child_one_occ = ParseNode('t0', False, right_l2)
    >>> sorted(get_all_rule_replacement_strs(one_child_one_occ, replacee_rule, replacee_posn))
    ['4', '[[:REPLACEME]]']
    >>> two_children_one_occ = ParseNode('t0', False, left_l2)
    >>> sorted(get_all_rule_replacement_strs(two_children_one_occ, replacee_rule, replacee_posn))
    ['44', '[[:REPLACEME]]']
    >>> sorted(get_all_rule_replacement_strs(big_tree,replacee_rule, replacee_posn))
    ['44*4', '44*[[:REPLACEME]]', '[[:REPLACEME]]*4', '[[:REPLACEME]]*[[:REPLACEME]]']
    """
    start = replacee_rule[0]
    body = [fixup_terminal(elem) for elem in replacee_rule[1]]
    if tree.is_terminal:
        return [fixup_terminal(tree.payload)]
    strings_per_child = [get_all_rule_replacement_strs(c, replacee_rule, replacee_posn) for c in tree.children]
    if tree.payload == start:
        tree_body = [fixup_terminal(c.payload) for c in tree.children]
        if tree_body == body:
            strings_per_child[replacee_posn].append(REPLACE_CONST)

    lens_per_child = [len(spc) for spc in strings_per_child]
    prod_size = muh_product(lens_per_child)
    if prod_size > MAX_SAMPLES:
        ret_list = sample_from_product(strings_per_child, MAX_SAMPLES, lens_per_child, prod_size)
    else:
        ret_list = [''.join(p) for p in itertools.product(*strings_per_child)]

    return list(set(ret_list))

def get_strings_with_replacement(tree: ParseNode, nt_to_replace: str, replacement_strs: Set[str]):
    """
    Get all the possible strings derived from `tree` where all possible combinations
    (not including the empty combo) of instances of `nt_to_replace` are replaced
    with one of the replacement strings in `replacement_strs`. Does not combine different
    strings from `replacement_strs` in the same instance.
    >>> global MAX_SAMPLES; MAX_SAMPLES = 100
    >>> left_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])]), ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> right_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> left_l2 = [ParseNode('t2', False, left_l3)]
    >>> right_l2 = [ParseNode('t2', False, right_l3)]
    >>> big_tree = ParseNode('t0', False, \
                     [ParseNode('t0', False, left_l2), \
                      ParseNode('t4', False, [ParseNode('"*"', True, [])]), \
                      ParseNode('t0', False, right_l2)] \
                     )
    >>> sorted(get_strings_with_replacement(big_tree, 't2', {"3", "2"}))
    ['2*2', '2*4', '22*2', '22*4', '24*2', '24*4', '3*3', '3*4', '33*3', '33*4', '34*3', '34*4', '42*2', '42*4', '43*3', '43*4', '44*2', '44*3']
    """
    placeholder_strings = get_all_replacement_strings(tree, nt_to_replace)
    placeholder_strings = [s for s in placeholder_strings if REPLACE_CONST in s]

    ret_strings = []
    for replacement_str in replacement_strs:
        ret_strings.extend([ps.replace(REPLACE_CONST, replacement_str) for ps in placeholder_strings])

    if len(ret_strings) > MAX_SAMPLES:
        random.shuffle(ret_strings)
        ret_strings = ret_strings[:MAX_SAMPLES]

    return ret_strings


def get_strings_with_replacement_in_rule(tree: ParseNode, replacee_rule: Tuple[str, List[str]], replacee_posn: int, replacement_strs: Set[str]):
    """
    Get all the possible strings derived from `tree` where all possible combinations
    (not including the empty combo) of instances of the nonterminal at position
    `replacee_posn` in `replacee_rule` are replaced with one of the replacement strings
    in `replacement_strs`. Does not combine differentstrings from `replacement_strs`
    in the same instance.
    >>> left_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])]), ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> right_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> left_l2 = [ParseNode('t2', False, left_l3)]
    >>> right_l2 = [ParseNode('t2', False, right_l3)]
    >>> big_tree = ParseNode('t0', False, \
                     [ParseNode('t0', False, left_l2), \
                      ParseNode('t4', False, [ParseNode('"*"', True, [])]), \
                      ParseNode('t0', False, right_l2)] \
                     )
    >>> sorted(get_strings_with_replacement_in_rule(big_tree, ('t0', ['t2']), 0, {"3", "2"}))
    ['2*2', '2*4', '3*3', '3*4', '44*2', '44*3']
    """
    placeholder_strings = get_all_rule_replacement_strs(tree, replacee_rule, replacee_posn)
    placeholder_strings = [s for s in placeholder_strings if REPLACE_CONST in s]

    ret_strings = []
    for replacement_str in replacement_strs:
        ret_strings.extend([ps.replace(REPLACE_CONST, replacement_str) for ps in placeholder_strings])

    if len(ret_strings) > MAX_SAMPLES:
        random.shuffle(ret_strings)
        ret_strings = ret_strings[:MAX_SAMPLES]

    return ret_strings

if __name__ == "__main__":
    import doctest
    doctest.testmod()
