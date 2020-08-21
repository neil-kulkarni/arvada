import re
from collections import defaultdict
from typing import List, Tuple, Set, Dict, Optional

from oracle import ParseException
from parse_tree import ParseNode
from grammar import *
from graph import Graph
from input import clean_terminal
from union import UnionFind
import numpy as np
from replacement_utils import get_strings_with_replacement, get_strings_with_replacement_in_rule

MAX_SAMPLES_PER_COALESCE = 50
MAX_GROUP_LEN = 7


class Bubble:
    def __init__(self, new_nt: str, bubbled_elems: List[str]):
        self.new_nt = new_nt
        self.bubbled_elems = bubbled_elems
        self.direct_parents = []
        self.occ_count = 1

    def add_direct_parent(self, parent):
        self.direct_parents.append(parent)

    def add_occurrence(self):
        self.occ_count += 1

    def add_context(self, context_lhs, context_rhs):
        # TODO
        pass

    def __str__(self):
        return f"Bubble({self.new_nt}->{self.bubbled_elems}, occs={self.occ_count})"

    def __repr__(self):
        return self.__str__()
    # def get_new_nt(self):
    #     return self.new_nt
    #
    # def get_bubble_elems(self):
    #     return self.bubbled_elems


def allocate_tid():
    """
    Returns a new, unqiue nonterminal name.
    """
    global next_tid
    nt_name = 't%d' % (next_tid)
    next_tid += 1
    return nt_name


# Globally unique nonterminal number
next_tid = 0
START = allocate_tid()  # The start nonterminal is t0


def build_start_grammar(oracle, leaves):
    """
    ORACLE is a Lark parser for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    CONFIG is the required configuration options for GrammarGenerator classes.

    DATA is a map containing both the positive and negative examples used to
    train the stochastic search.

    LEAVES is a list of positive examples, each expressed as a list of tokens
    (ParseNode objects).

    Returns a set of starting grammar generators whose corresponding grammars
    each match at least one input example.
    """
    print('Building the starting trees...'.ljust(50), end='\r')
    trees, classes = build_trees(oracle, leaves)
    print('Building initial grammar...'.ljust(50), end='\r')
    grammar = build_grammar(trees)
    print('Coalescing nonterminals...'.ljust(50), end='\r')
    grammar, new_trees, coalesce_caused = coalesce(oracle, trees, grammar)
    grammar, new_trees, partial_coalesces = coalesce_partial(oracle, new_trees, grammar)
    print('Minimizing initial grammar...'.ljust(50), end='\r')
    grammar = minimize(grammar)
    return grammar


def derive_classes(oracle, leaves):
    """
    Given a list of positive examples in LEAVES, uses a replacement algorithm
    to determine which tokens belong to the same character classes. Each character
    class is given a new nonterminal, which will be the disjunction of each of
    the characters in the class in every grammar. Characters that do not belong
    to any classes are still given a unique nonterminal. Returns the new tree
    that is created by bubbling up each of the terminals to their
    corresponding class. Also returns a map of nonterminal to the character
    class that it defines.

    ORACLE is a Lark parser for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    CONFIG is the required configuration options for GrammarGenerator classes.

    LEAVES is a list of positive examples, each expressed as a list of tokens
    (ParseNode objects).
    """

    def replaces(replacer, replacee):
        """
        For every string in which REPLACEE appears, replace it with REPLACER,
        and check if the resulting string is still valid.

        Return True if this is the always the case.

        Relies on the fact that LEAVES is unchanged from the time when it was
        inputted into derive_classes.
        """
        replaced_leaves = [
            [ParseNode(replacer if leaf.payload == replacee else leaf.payload, leaf.is_terminal, leaf.children) for leaf
             in tree] for tree in leaves]
        replaced_examples = [''.join([pn.payload for pn in tree]) for tree in replaced_leaves]
        for example in replaced_examples:
            try:
                oracle.parse(example)
            except Exception as e:
                return False
        return True

    # Define helpful data structures
    # terminals = list(config['TERMINALS'])
    # terminals.remove('') # Remove epsilon terminal
    # terminals = [t.replace('"', '') for t in terminals]
    terminals = list(set([leaf.payload for leaf_lst in leaves for leaf in leaf_lst]))
    print(terminals)
    uf = UnionFind(terminals)

    # Check to make sure initial guide examples compile
    if not replaces('', ''):
        print('ERROR: Guide examples do not compile!')
        exit(1)

    for i in range(len(terminals)):
        for j in range(i + 1, len(terminals)):
            # Iterate through each unique pair of terminals
            print(('Terminal replacement (%d, %d, %d)...' % (i + 1, j + 1, len(terminals))).ljust(50), end='\r')
            first, second = terminals[i], terminals[j]
            # If the terminals can replace each other in every context, they
            # must belong to the same character class
            if not uf.is_connected(first, second) and replaces(first, second) and replaces(second, first):
                uf.connect(first, second)

    # Define a mapping and a reverse mapping between a character class and
    # the newly generated nonterminal for that class
    get_class, classes = {}, {}
    for cc in uf.classes().values():
        class_nt = allocate_tid()
        classes[class_nt] = cc
        for terminal in cc:
            get_class[terminal] = class_nt

    trees = [ParseNode(START, False, [ParseNode(get_class[leaf.payload], False, [leaf]) for leaf in leaf_lst]
                       )
             for leaf_lst in leaves]

    # Update each of the terminals in leaves to instead be a new nonterminal
    # ParseNode pointing to the original terminal. Return the resulting parse
    # trees as well as a mapping of nonterminal to its character class.
    return trees, classes  # [ParseNode(START, False, [tree])
    # for tree in trees], classes


def build_naive_parse_trees(leaves: List[List[ParseNode]]):
    """
    Builds naive parse trees for each leaf in `leaves`, assigning each unique
    character to its own nonterminal, and uniting them all under the START
    nonterminal.
    """
    terminals = list(set([leaf.payload for leaf_lst in leaves for leaf in leaf_lst]))
    get_class = {t: allocate_tid() for t in terminals}
    trees = [ParseNode(START, False, [ParseNode(get_class[leaf.payload], False, [leaf]) for leaf in leaf_lst])
             for leaf_lst in leaves]
    return trees


def group(trees) -> List[Bubble]:
    """
    TREES is a set of ParseTrees.

    Returns the set of all possible groupings of nonterminals in TREES,
    where each grouping is a data structure holding information about a
    grouing of contiguous nonterminals in TREES.

    A grouping is a two-element tuple data structure that represents a contiguous
    sequence of nonterminals that appears someplace in TREES. The first element
    is a string representation of this sequence. The second element is itself
    a two-element tuple that contains a list representation of the sequence, as
    well as the fresh nonterminal assigned to the grouping.
    """

    # Helper tracking if a subsequence is only seen as the "full" child of another nonterminal,
    # I.e. t2 t3 t4 in t1 -> t2 t3 t4, but not in t1 -> t2 t2 t3 t4
    full_bubbles = defaultdict(int)

    def add_groups_for_tree(tree: ParseNode, groups: Dict[str, Bubble]):
        """
        Add all groups possible groupings derived from the parse tree `tree` to `groups`.
        """
        children_lst = tree.children
        for i in range(len(children_lst)):
            for j in range(i + 2, min(len(children_lst) + 1, i + MAX_GROUP_LEN)):
                tree_sublist = children_lst[i:j]
                tree_substr = ''.join([t.payload for t in tree_sublist])
                if i == 0 and j == len(children_lst):
                    # TODO: add direct parent to bubble
                    full_bubbles[tree_substr] += 1
                if not tree_substr in groups:
                    groups[tree_substr] = Bubble(allocate_tid(), tree_sublist)
                else:
                    bubble: Bubble = groups[tree_substr]
                    bubble.add_occurrence()

        # Recurse down in the other layers
        for child in tree.children:
            if not child.is_terminal:
                add_groups_for_tree(child, groups)

    # Compute a set of all possible groupings
    groups = {}
    for tree in trees:
        add_groups_for_tree(tree, groups)

    # Remove sequences if they're the full list of children of a rule and don't appear anywhere else
    for bubble in full_bubbles:
        if groups[bubble].occ_count == full_bubbles[bubble]:
            groups.pop(bubble)

    # Return the set of repeated groupings as an iterable
    groups = list(groups.values())
    # random.shuffle(groups)
    groups = sorted(groups, key=lambda bubble: (bubble.occ_count, len(bubble.bubbled_elems)), reverse=True)
    return groups


def apply(grouping: Bubble, trees: List[ParseNode]):
    """
    GROUPING is a two-element tuple data structure that represents a contiguous
    sequence of nonterminals that appears someplace in LAYERS. The first element
    is a string representation of this sequence. The second element is itself
    a two-element tuple that contains a list representation of the sequence, as
    well as the fresh nonterminal assigned to the grouping.

    TREES is a set of parse trees

    Returns a new list of trees consisting of applying the bubbling up the grouping
    in GROUPING for each tree in TREES
    """

    def matches(group_lst, layer):
        """
        GROUP_LST is a contiguous subarray of ParseNodes that are grouped together.
        This method requires that len(GRP_LST) > 0.

        LAYER another a list of ParseNodes.

        Returns the index at which GROUP_LST appears in LAYER, and returns -1 if
        the GROUP_LST does not appear in the LAYER. Does not mutate LAYER.
        """
        ng, nl = len(group_lst), len(layer)
        for i in range(nl):
            layer_ind = i  # Index into layer
            group_ind = 0  # Index into group
            while group_ind < ng and layer_ind < nl and layer[layer_ind].payload == group_lst[group_ind].payload:
                layer_ind += 1
                group_ind += 1
            if group_ind == ng: return i
        return -1

    def apply_single(tree: ParseNode):
        """
        TREE is a parse tree.

        Applies the GROUPING data structure to a single tree. Applies that
        GROUPING to LAYER as many times as possible. Does not mutate TREE.

        Returns the new layer. If no updates can be made, do nothing.
        """
        group_lst, id = grouping.bubbled_elems, grouping.new_nt
        new_tree, ng = tree.copy(), len(group_lst)

        # Do replacments in all the children first
        for index in range(len(new_tree.children)):
            # (self, payload, is_terminal, children)
            old_node = new_tree.children[index]
            new_tree.children[index] = apply_single(old_node)

        ind = matches(group_lst, new_tree.children)
        while ind != -1:
            parent = ParseNode(id, False, new_tree.children[ind: ind + ng])
            new_tree.children[ind: ind + ng] = [parent]
            ind = matches(group_lst, new_tree.children)

        return new_tree

    return [apply_single(tree) for tree in trees]


def build_trees(oracle, leaves):
    """
    ORACLE is an oracle for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    LEAVES should be a list of lists (one list for each input example), where
    each sublist contains the tokens that built that example, as ParseNodes.

    Iteratively builds parse trees by greedily choosing a substring to "bubble"
    up that passes replacement tests at each point in the algorithm, until no
    further bubble ups can be made.

    Returns a list of finished ParseNode references. Also returns the character
    classes for use in future stages of the algorithm.

    Algorithm:
        1. Over all top-level substrings:
            a. bubble up the substring
            b. perform replacement if possible
        2. If a replacement was possible, repeat (1)
    """

    def score(trees: List[ParseNode], new_bubble: Optional[Bubble] = None) \
            -> Tuple[int, float, List[ParseNode]]:
        """[
        TREES is a list of Parse Trees.

        Converts TREES into a grammar and returns its positive score, and the new
        set of trees corresponding to the coalescing.
        Does not mutate LAYERS in this process.
        """
        # Convert LAYERS into a grammar
        grammar = build_grammar(trees)

        grammar, new_trees, coalesce_caused = coalesce(oracle, trees, grammar, new_bubble)
        if not coalesce_caused:
            grammar, new_trees, partial_coalesces = coalesce_partial(oracle, trees, grammar, new_bubble)
            if partial_coalesces:
                print("\n(partial)")
                coalesce_caused = True

        # grammar = minimize(grammar)
        new_size = grammar.size()
        if coalesce_caused:
            return 1, new_size, new_trees
        else:
            return 0, new_size, trees

    # Run the character class algorithm to create the first layer of tree
    # best_trees, classes = derive_classes(oracle, leaves)
    best_trees = build_naive_parse_trees(leaves)
    print("Scoring...")
    best_score, best_size, best_trees = score(best_trees)
    updated = True
    count = 1

    # Main algorithm loop
    while updated:
        all_groupings = group(best_trees)
        updated, nlg = False, len(all_groupings)
        for i, grouping in enumerate(all_groupings):
            print(('Bubbling iteration (%d, %d, %d)...' % (count, i + 1, nlg)).ljust(50), end='\r')
            new_trees = apply(grouping, best_trees)
            new_score, size, new_trees = score(new_trees, grouping)
            if new_score > 0:
                print(f"Successful grouping (coalesce): {grouping.new_nt} -> {grouping.bubbled_elems}")
                best_trees = new_trees
                best_size = min(best_size, size)
                updated = True
                break
        # if not updated:
        #     for i, grouping in enumerate(all_groupings):
        #         new_trees = apply(grouping, best_trees)
        #         for j, grouping_2 in
            # elif size < best_size:
            #     print(f"Successful grouping (size, {best_size} vs. {size}): {grouping.new_nt} -> {grouping.bubbled_elems}")
            #     best_trees = new_trees
            #     best_size = size
            #     updated = True
            #     break
        layers, count = best_trees, count + 1

    return best_trees, {}


def build_grammar(trees):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    TREES is a list of fully constructed parse trees. This method builds a
    GrammarNode that is the disjunction of the parse trees, and returns it.
    """

    def build_rules(grammar_node, parse_node, rule_map):
        """
        Adds the rules defined in PARSE_NODE and all of its subtrees to the
        GRAMMAR_NODE via recursion. RULE_MAP is used to keep track of duplicate
        rules, so they are not added multiple times to the grammar.
        """
        # Terminals and nodes with no children do not define rules
        if parse_node.is_terminal or len(parse_node.children) == 0:
            return

        # The current ParseNode defines a rule. Add this rule to the grammar.
        #        t0
        #       / | \
        #     t1  a  b
        #    / |
        #    ...
        # E.g. the ParseNode t0 defines the rule t0 -> t1 a b
        rule_body = [clean_terminal(child.payload) if child.is_terminal
                     else child.payload
                     for child in parse_node.children]
        rule = Rule(parse_node.payload)
        rule.add_body(rule_body)
        rule_str = ''.join([elem for elem in rule_body])
        if rule.start not in rule_map: rule_map[rule.start] = set()
        if rule_str not in rule_map[rule.start]:
            grammar_node.add_rule(rule)
            rule_map[rule.start].add(rule_str)

        # Recurse on the children of this ParseNode so the rule they define
        # are also added to the grammar.
        for child in parse_node.children:
            build_rules(grammar_node, child, rule_map)

    # Construct the initial grammar node without children, then fill them.
    grammar, rule_map = Grammar(START), {}
    for tree in trees:
        build_rules(grammar, tree, rule_map)
    return grammar


def coalesce_partial(oracle: Lark, trees: List[ParseNode], grammar: Grammar,
                     coalesce_target: Bubble = None):
    """
    Performs partial coalesces on the grammar. That is, for pairs of nonterminals (nt1, nt2), checks whether:
       if nt1 can be replaced by nt2 everywhere, are there any occurrences of nt2 where nt1 can replace nt2.

    ASSUMES: coalesce(oracle, trees, grammar, coalesce_target) has been called previously. In this case, we will never
    be in the situation where (nt1, nt2) can partially coalesce and (nt2, nt1) can partially coalesce:

    """


    def get_all_derivable_strings(tree: ParseNode, replacer_nt: str) -> Set[str]:
        """
        Returns all those strings derivable from REPLACER_NT in TREE.
        """

        def derived_string(tree: ParseNode):
            """
            Returns the string derived from the leaves of this tree.
            """
            if tree.is_terminal:
                return tree.payload
            return ''.join([derived_string(c) for c in tree.children])

        if tree.is_terminal:
            return set()
        elif tree.payload == replacer_nt:
            return {derived_string(tree)}
        else:
            derivable = set()
            for child in tree.children:
                derivable.update(get_all_derivable_strings(child, replacer_nt))
            return derivable

    def partially_coalescable(replaceable_everywhere: str, replaceable_in_some_rules: str, trees) -> Dict[
        Tuple[str, Tuple[str]], List[int]]:
        """
        `replaceable_everywhere` and `replaceable_in_some_rules` are both nonterminals

        If `replaceable_in_some_rules` can replace `replaceable_everywhere` at every
        occurrence of `replaceable_everywhere`, returns the rules (expansions) in which
        `replaceable_in_some_rules` can be replaced by `replaceable_everywhere`
        """

        # Get all the expansions where `replaceable_in_some_rules` appears
        partial_replacement_locs: List[Tuple[Tuple[str, List[str]], int]] = []
        for rule_start, rule in grammar.rules.items():
            for body in rule.bodies:
                replacement_indices = [idx for idx, val in enumerate(body) if val == replaceable_in_some_rules]
                for idx in replacement_indices:
                    partial_replacement_locs.append(((rule_start, body), idx))

        # Get the set of strings derivable from `replaceable_everywhere`
        everywhere_derivable_strings = set()
        for tree in trees:
            everywhere_derivable_strings.update(get_all_derivable_strings(tree, replaceable_everywhere))

        # Get the set of strings derivable from `replaceable_in_some_rules`
        in_some_derivable_strings = set()
        for tree in trees:
            in_some_derivable_strings.update(get_all_derivable_strings(tree, replaceable_in_some_rules))

        # Check whether `replaceable_everywhere` is replaceable by `replaceable_in_some_rules` everywhere.
        everywhere_by_some_candidates = []
        for tree in trees:
            everywhere_by_some_candidates.extend(
                get_strings_with_replacement(tree, replaceable_everywhere, in_some_derivable_strings))

        if len(everywhere_by_some_candidates) > MAX_SAMPLES_PER_COALESCE:
            everywhere_by_some_candidates = random.sample(everywhere_by_some_candidates, MAX_SAMPLES_PER_COALESCE)
        else:
            random.shuffle(everywhere_by_some_candidates)

        try:
            for replaced_str in everywhere_by_some_candidates:
                oracle.parse(replaced_str)
        except Exception as e:
            return []

        assert (len(everywhere_derivable_strings) > 0)

        # Now check whether there are any rules where `replaeable_in_some_rules` is replaceable by
        # `replaceable_everywhere`
        replacing_positions: Dict[Tuple[str, Tuple[str]], List[int]] = defaultdict(list)
        for replacement_loc in partial_replacement_locs:
            rule, posn = replacement_loc
            candidate_strs = []
            for tree in trees:
                candidate_strs.extend(
                    get_strings_with_replacement_in_rule(tree, rule, posn, everywhere_derivable_strings))
            if len(candidate_strs) > MAX_SAMPLES_PER_COALESCE:
                candidate_strs = random.sample(candidate_strs, MAX_SAMPLES_PER_COALESCE)
            else:
                random.shuffle(candidate_strs)

            try:
                for candidate in candidate_strs:
                    oracle.parse(candidate)
                replacing_positions[(rule[0], tuple(rule[1]))].append(posn)
            except ParseException as e:
                continue

        return replacing_positions

    def get_updated_grammar(old_grammar, partial_replacement_locs: Dict[Tuple[str, Tuple[str]], List[int]],
                            full_replacement_nt: str, nt_to_partially_replace: str, new_nt: str):
        """
        Creates a copy of `old_grammar` so that the locations in `partial_replacement_locs` are replaced by `new_nt`, and all
        occurrences of `full_relacement_nt` are replaced by `new_nt`
        """
        grammar = old_grammar.copy()
        alt_rule = Rule(new_nt)
        for (rule_start, body), posns in partial_replacement_locs.items():
            rule_to_update = grammar.rules[rule_start]
            body_posn = rule_to_update.bodies.index(list(body))
            for posn in posns:
                rule_to_update.bodies[body_posn][posn] = new_nt
        for rule in grammar.rules.values():
            for body in rule.bodies:
                for idx in range(len(body)):
                    if body[idx] == full_replacement_nt:
                        body[idx] = new_nt
        # Now fixup rules to remove any duplicate productions that may have been added during replacement.
        for rule in grammar.rules.values():
            unique_bodies = []
            for body in rule.bodies:
                if body not in unique_bodies:
                    unique_bodies.append(body)
            rule.bodies = unique_bodies
        alt_rule_bodies = grammar.rules[full_replacement_nt].bodies
        alt_rule_bodies.extend(grammar.rules[nt_to_partially_replace].bodies)
        grammar.rules.pop(full_replacement_nt)
        alt_rule.bodies = alt_rule_bodies
        grammar.add_rule(alt_rule)
        return grammar

    def update_tree(new_tree: ParseNode, partial_replacement_locs: Dict[Tuple[str, Tuple[str]], List[int]],
                    full_replacement_nt: str, new_nt: str):
        """
        Updates `new_tree` s.t. the locations in `partial_replacement_locs` are replaced by `new_nt`, and all
        occurrences of `full_relacement_nt` are replaced by `new_nt`.
        """
        if new_tree.is_terminal:
            return new_tree
        my_body = tuple([child.payload for child in new_tree.children])
        for c in new_tree.children:
            update_tree(c, partial_replacement_locs, full_replacement_nt, new_nt)
        if (new_tree.payload, my_body) in partial_replacement_locs:
            posns = partial_replacement_locs[(new_tree.payload, my_body)]
            for posn in posns:
                prev_child = new_tree.children[posn]
                prev_child.payload = new_nt
        if new_tree.payload == full_replacement_nt:
            new_tree.payload = new_nt

    def get_updated_trees(trees: List[ParseNode], rules_to_replace: Dict[Tuple[str, Tuple[str]], List[int]],
                          replacer_orig: str, replacer: str):
        rest = []
        for tree in trees:
            new_tree = tree.copy()
            update_tree(new_tree, rules_to_replace, replacer_orig, replacer)
            rest.append(new_tree)
        return rest

    #################### END HELPERS ########################

    nonterminals = set(grammar.rules.keys())
    nonterminals.remove("start")
    nonterminals = list(nonterminals)

    if coalesce_target is not None:
        fully_replaceable = [coalesce_target.new_nt]
    else:
        fully_replaceable = nonterminals

    partially_replaceable = [nonterm for nonterm in nonterminals
                             if len(grammar.rules[nonterm].bodies) == 1 and len(grammar.rules[nonterm].bodies[0]) == 1
                             and grammar.rules[nonterm].bodies[0][0] not in nonterminals]

    # The main work of the function.
    replacement_happened = False
    fully_replaced = {}
    for nt_to_fully_replace in fully_replaceable:
        for nt_to_partially_replace in partially_replaceable:
            while nt_to_fully_replace in fully_replaced and nt_to_fully_replace != START:
                nt_to_fully_replace = fully_replaced[nt_to_fully_replace]
            while nt_to_partially_replace in fully_replaced and nt_to_partially_replace != START:
                nt_to_partially_replace = fully_replaced[nt_to_partially_replace]
            if nt_to_fully_replace == nt_to_partially_replace:
                continue
            replacement_positions = partially_coalescable(nt_to_fully_replace, nt_to_partially_replace, trees)
            if len(replacement_positions) > 0:
                print(f"we found that {nt_to_partially_replace} could replace {nt_to_fully_replace} everywhere, "
                      f"and {nt_to_fully_replace} could replace {nt_to_partially_replace} at : {replacement_positions}")

                if nt_to_fully_replace == START:
                    new_nt = START
                else:
                    new_nt = allocate_tid()
                grammar = get_updated_grammar(grammar, replacement_positions, nt_to_fully_replace,
                                              nt_to_partially_replace, new_nt)
                trees = get_updated_trees(trees, replacement_positions, nt_to_fully_replace, new_nt)
                fully_replaced[nt_to_fully_replace] = new_nt
                replacement_happened = True

    return grammar, trees, replacement_happened


def coalesce(oracle: Lark, trees: List[ParseNode], grammar: Grammar,
             coalesce_target: Bubble = None):
    """
    ORACLE is a Lark parser for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    TREES is a list of fully constructed parse trees.

    GRAMMAR is a GrammarNode that is the disjunction of the TREES.

    COALESCE_TARGET is the nonterminal we should be checking coalescing against,
    else due a quadratic check of all nonterminals against each other.

    This method coalesces nonterminals that are equivalent to each other.
    Equivalence is determined by replacement.

    RETURNS: the grammar after coalescing, the parse trees after coalescing,
    and whether any nonterminals were actually coalesced with each other
    (found equivalent).
    """

    def replacer_strings(tree, replacer_nt, derivable):
        """
        Adds to the set DERIVABLE all those strings derivable from the
        REPLACER_NT in TREE.
        """

        def node_string(tree):
            """
            Returns the string derived from the leaves of this tree.
            """
            if tree.is_terminal:
                return tree.payload
            return ''.join([node_string(c) for c in tree.children])

        if tree.is_terminal:
            return derivable
        elif tree.payload == replacer_nt:
            derivable.add(node_string(tree))
        else:
            for child in tree.children:
                replacer_strings(child, replacer_nt, derivable)

    def replaces(replacer, replacee, trees):
        """
        For every string derived from REPLACEE, replace it with all possible
        strings derived from REPLACER, and check if the resulting string is still valid.

        Return True if this is the always the case.

        Relies on the fact that TREES is unchanged from the time when it was
        inputted into coalesce.
        """
        # Get the set of strings derivable from replacer
        replacer_derivable_strings = set()
        for tree in trees:
            replacer_strings(tree, replacer, replacer_derivable_strings)

        # Get the set of positive examples with strings derivable from replacer
        # replaced with strings derivable from replacee
        replaced_strings = set()
        for tree in trees:
            replaced_strings.update(get_strings_with_replacement(tree, replacee, replacer_derivable_strings))

        replaced_strings = list(replaced_strings)
        if len(replaced_strings) > MAX_SAMPLES_PER_COALESCE:
            replaced_strings = random.sample(replaced_strings, MAX_SAMPLES_PER_COALESCE)
        else:
            random.shuffle(replaced_strings)



        # Return True if all the replaced_strings are valid
        for s in replaced_strings:
            try:
                oracle.parse(s)
            except:
                return False
        return True

    def get_updated_trees(get_class: Dict[str, str], trees):

        def replace_coalesced_nonterminals(node: ParseNode):
            """
                Rewrites node so that coalesced nonterminals point to their
                class nonterminal. For non-coalesced nonterminals, get_class
                just gives the original nonterminal
                """
            if node.is_terminal:
                return
            else:
                node.payload = get_class.get(node.payload, node.payload)
                for child in node.children:
                    replace_coalesced_nonterminals(child)

        def fix_double_indirection(node: ParseNode):
            """
                Fix parse trees that have an expansion of the for tx->tx (only one child)
                since we've removed such double indirection while merging nonterminals
                """
            if node.is_terminal:
                return

            while len(node.children) == 1 and node.children[0].payload == node.payload:
                # Won't go on forever because eventually length of children will be not 1,
                # or the children's payload will not be the same as the top node (e.g. if
                # the child is a terminal)
                node.children = node.children[0].children

            for child in node.children:
                fix_double_indirection(child)

        new_trees = []
        for tree in trees:
            new_tree = tree.copy()
            replace_coalesced_nonterminals(new_tree)
            fix_double_indirection(new_tree)
            new_trees.append(new_tree)
        return new_trees

    def get_updated_grammar(classes: Dict[str, List[str]], get_class: Dict[str, str], grammar):
        # Traverse through the grammar, and update each nonterminal to point to
        # its class nonterminal
        new_grammar = grammar.copy()
        for nonterm in new_grammar.rules:
            if nonterm == "start":
                continue
            for body in new_grammar.rules[nonterm].bodies:
                for i in range(len(body)):
                    # The keys of the rules determine the set of nonterminals
                    if body[i] in get_class:
                        body[i] = get_class[body[i]]
        # Add the alternation rules for each class into the grammar
        for class_nt, nts in classes.items():
            rule = Rule(class_nt)
            for nt in nts:
                old_rule = new_grammar.rules.pop(nt)
                for body in old_rule.bodies:
                    # Remove infinite recursions
                    if body == [class_nt]:
                        continue
                    rule.add_body(body)
            new_grammar.add_rule(rule)
        return new_grammar

    # Define helpful data structures
    nonterminals = set(grammar.rules.keys())
    nonterminals.remove("start")
    nonterminals = list(nonterminals)
    uf = UnionFind(nonterminals)

    # Get all unique pairs of nonterminals
    pairs = []
    if coalesce_target is not None:
        first = coalesce_target.new_nt
        for second in nonterminals:
            if first == second:
                continue
            pairs.append((first, second))
    else:
        for i in range(len(nonterminals)):
            for j in range(i + 1, len(nonterminals)):
                first, second = nonterminals[i], nonterminals[j]
                pairs.append((first, second))

    coalesce_caused = False
    coalesced_into = {}
    checked = set()
    for pair in pairs:
        first, second = pair
        ### update the pair for the new grammar
        while first in coalesced_into and first != START:
            first = coalesced_into[first]
        while second in coalesced_into and second != START:
            second = coalesced_into[second]
        ### and check that it's still valid
        if first == second:
            continue
        if (first, second) in checked:
            continue
        else:
            checked.add((first, second))
        ###
        # If the nonterminals can replace each other in every context, they are replaceable
        if replaces(first, second, trees) and replaces(second, first, trees):
            if first == START or second == START:
                class_nt = START
            else:
                class_nt = allocate_tid()
            classes = {class_nt: [first, second]}
            get_class = {first: class_nt, second: class_nt}
            coalesced_into[first] = class_nt
            coalesced_into[second] = class_nt
            grammar = get_updated_grammar(classes, get_class, grammar)
            trees = get_updated_trees(get_class, trees)
            coalesce_caused = True

    return grammar, trees, coalesce_caused


def minimize(grammar):
    """
    Mutative method that deletes repeated rules from GRAMMAR and removes
    unnecessary layers of indirection.

    CONFIG is the required configuration options for GrammarGenerator classes.
    """

    def remove_repeated_rules(grammar: Grammar):
        """
        Mutative method that removes all repeated rule bodies in GRAMMAR.
        """
        for rule in grammar.rules.values():
            remove_idxs = []
            bodies_so_far = set()
            for i, body in enumerate(rule.bodies):
                body_str = ''.join(body)
                if body_str in bodies_so_far:
                    remove_idxs.append(i)
                else:
                    bodies_so_far.add(body_str)
            for idx in reversed(remove_idxs):
                rule.bodies.pop(idx)

    def update(grammar: Grammar, map):
        """
        Given a MAP with nonterminals as keys and list of strings as values,
        replaces every occurance of a nonterminal in MAP with its corresponding
        list of symbols in the GRAMMAR. Then, the rules defining
        the keys nonterminals in MAP in the grammar are removed.

        The START nonterminal must not appear in MAP, because its rule cannot
        be deleted.
        """
        assert (START not in map)
        for rule in grammar.rules.values():
            for body in rule.bodies:
                to_fix = [elem in map for elem in body]
                # Reverse to ensure that we don't mess up the indices
                while any(to_fix):
                    ind = to_fix.index(True)
                    nt = body[ind]
                    body[ind:ind + 1] = map[nt]
                    to_fix = [elem in map for elem in body]
        remove_lhs = [lhs for lhs in grammar.rules.keys() if lhs in map]
        for lhs in remove_lhs:
            grammar.rules.pop(lhs)
        grammar.cached_parser_valid = False
        grammar.cached_str_valid = False
        return grammar

    # Remove all the repeated rules from the grammar
    remove_repeated_rules(grammar)

    # Finds the set of nonterminals that expand directly to a single terminal
    # Let the keys of X be the set of these nonterminals, and the corresponding
    # values be the the SymbolNodes derivable from those nonterminals
    X, updated = {}, True  # updated determines the stopping condition

    while updated:
        updated = False
        for rule_start in grammar.rules:
            rule = grammar.rules[rule_start]
            bodies = rule.bodies
            if len(bodies) == 1 and len(bodies[0]) == 1 and (bodies[0][0] not in grammar.rules or bodies[0][0] in X):
                body = bodies[0]
                if rule.start not in X and rule.start != START:
                    X[rule.start] = [X[elem][0] if elem in X else elem for elem in body]
                    updated = True

    # Update the grammar so that keys in X are replaced by values
    grammar = update(grammar, X)

    # Finds the set of nonterminals that expand to a single string and that are
    # only used once in the grammar. Let the keys of Y be the set of these
    # nonterminals, and the corresponding values be the SymbolNodes derivable
    # from those nonterminals
    counts = defaultdict(int)
    for rule_node in grammar.rules.values():
        for rule_body in rule_node.bodies:
            for symbol in rule_body:
                if symbol in grammar.rules:
                    n = symbol
                    counts[n] += 1

    # Update the grammar so that keys in X are replaced by values
    used_once = [k for k in counts if counts[k] == 1 and k != START]
    Y = {k: grammar.rules[k].bodies[0] for k in used_once if len(grammar.rules[k].bodies) == 1}
    grammar = update(grammar, Y)

    remove_repeated_rules(grammar)

    return grammar

# Example:
# from input import parse_input
# from parse_tree import ParseTree
# file_name = 'examples/arithmetic/arithmetic.json'
# CONFIG, ORACLE_GEN, ORACLE = parse_input(file_name)
# POS_EXAMPLES, MAX_TREE_DEPTH = CONFIG['POS_EXAMPLES'], CONFIG['MAX_TREE_DEPTH']
# oracle_parse_tree = ParseTree(ORACLE_GEN)
# positive_examples, positive_nodes = oracle_parse_tree.sample_strings(POS_EXAMPLES, MAX_TREE_DEPTH)
# positive_examples = ['int', '( int )', 'int + int', 'int * int']
# positive_nodes = [[ParseNode(tok, True, []) for tok in s.split()] for s in positive_examples]
#
# gen = build_start_grammar(ORACLE.parser(), CONFIG, positive_nodes)
# print(gen.generate_grammar())
