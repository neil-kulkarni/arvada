from collections import defaultdict
from typing import List, Tuple, Set, Dict, Optional, Union

from bubble import Bubble
from oracle import ParseException
from parse_tree import ParseNode, ParseTreeList, build_grammar, START
from grammar import *
from union import UnionFind
from replacement_utils import get_strings_with_replacement, get_strings_with_replacement_in_rule, \
    lvl_n_derivable

MAX_SAMPLES_PER_COALESCE = 50
MAX_GROUP_LEN = 10

def check_recall(oracle, grammar: Grammar):
    positives = grammar.sample_positives(10, 10)
    for pos in positives:
        try:
            oracle.parse(pos)
        except:
            return False
    return True


def allocate_tid():
    """
    Returns a new, unqiue nonterminal name.
    """
    global next_tid
    nt_name = 't%d' % (next_tid)
    next_tid += 1
    return nt_name


# Globally unique nonterminal number
next_tid = 1


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
    return trees, classes


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


def group(trees, max_group_size) -> List[Bubble]:
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

    def add_groups_for_tree(tree: ParseNode, bubbles: Dict[str, Bubble], left_context="START", right_context ="END"):
        """
        Add all groups possible groupings derived from the parse tree `tree` to `groups`.
        """
        children_lst = tree.children

        for i in range(len(children_lst)):
            for j in range(i + 1, min(len(children_lst) + 1, i + max_group_size + 1)):
                tree_sublist = children_lst[i:j]
                tree_substr = ''.join([t.payload for t in tree_sublist])
                if i == 0 and j == len(children_lst):
                    # TODO: add direct parent to bubble
                    full_bubbles[tree_substr] += 1

                lhs_context = [ParseNode(left_context, True, [])] + children_lst[:i]
                rhs_context = children_lst[j:] + [ParseNode(right_context, True, [])]

                if not tree_substr in bubbles:
                    bubble = Bubble(allocate_tid(), tree_sublist)
                    bubble.add_context(lhs_context, rhs_context)
                    bubbles[tree_substr] = bubble
                else:
                    bubble: Bubble = bubbles[tree_substr]
                    bubble.add_occurrence()
                    bubble.add_context(lhs_context, rhs_context)

        # Recurse down in the other layers
        for i, child in enumerate(tree.children):
            lhs = left_context if i == 0 else 'DUMMY'
            rhs = right_context if i == len(tree.children) else 'DUMMY'
            if not child.is_terminal:
                add_groups_for_tree(child, bubbles, lhs, rhs)

    # Compute a set of all possible groupings
    bubbles = {}
    for tree in trees:
        add_groups_for_tree(tree, bubbles)

    # Remove sequences if they're the full list of children of a rule and don't appear anywhere else
    for bubble_str in full_bubbles:
        if bubbles[bubble_str].occ_count == full_bubbles[bubble_str]:
            bubbles.pop(bubble_str)

    bubbles = score_and_sort_bubbles(bubbles)

    # Return the set of repeated groupings as an iterable
    return bubbles


def score_and_sort_bubbles(bubbles: Dict[str, Bubble]) -> List[Union[Bubble, Tuple[Bubble, Bubble]]]:
    """
    Given a set of bubbles, returns a sorted list of (tuples of) bubbles, sorted by a score on how
    likely the bubble(s) is to increase the size of the grammar.
    Single bubble --> likely coalesces with existing nonterminal
    Double bubble --> likely coalesces with each other
    """
    bubble_lst = list(sorted(list(bubbles.values()), key=lambda x: len(x.bubbled_elems), reverse=True))
    bubble_pairs = []
    for i in range(len(bubble_lst)):
        for j in range(i + 1, len(bubble_lst)):
            first_bubble: Bubble = bubble_lst[i]
            second_bubble: Bubble = bubble_lst[j]
            # Pairs of existing terminals we don't care about
            if len(first_bubble.bubbled_elems) == len(second_bubble.bubbled_elems) == 1:
                continue
            # Skip overlapping/conflicting pairs
            first_prevents_second, second_prevents_first = first_bubble.application_breaks_other(second_bubble)
            if first_prevents_second and second_prevents_first:
                continue

            # Score both for similarity of context and occurrence of the bubbles
            similarity = first_bubble.context_similarity(second_bubble)
            if len(first_bubble.bubbled_elems) == 1:
                commonness = sum([v for v in second_bubble.contexts.values()]) / 2
            elif len(second_bubble.bubbled_elems) == 1:
                commonness = sum([v for v in first_bubble.contexts.values()])
            else:
                commonness = sum([v for v in first_bubble.contexts.values()]) / 2 + sum(
                    [v for v in second_bubble.contexts.values()]) / 2

            # If they're partially overlapping, we may need a particular application order.
            if first_prevents_second:
                # need to invert the order of these, so we try all bubbles...
                bubble_pairs.append(((similarity, commonness), (second_bubble, first_bubble)))
            else:
                # either they don't conflict, or we can still do second after we apply first
                bubble_pairs.append(((similarity, commonness), (first_bubble, second_bubble)))

    bubbles = {}
    # Sort primarily by similarity, secondarily by commonness
    for score, pair in list(sorted(bubble_pairs, key=lambda x: x[0], reverse=True)):
        # Turn bubbles that are paired w/ a nonterm into single bubbles
        if len(pair[0].bubbled_elems) == 1:
            # This if statement probably never happens...
            if pair[1] not in bubbles:
                bubbles[pair[1]] = score
        elif len(pair[1].bubbled_elems) == 1:
            if pair[0] not in bubbles:
                bubbles[pair[0]] = score
        else:
            bubbles[pair] = score

    bubbles = list(bubbles.keys())
    if len(bubbles) > 100:
        bubbles = bubbles[:100]
    random.shuffle(bubbles)
    return bubbles


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

    def score(trees: List[ParseNode], new_bubble: Optional[Bubble]) \
            -> Tuple[int, List[ParseNode]]:
        """[
        TREES is a list of Parse Trees.

        Converts TREES into a grammar and returns its positive score, and the new
        set of trees corresponding to the coalescing.
        Does not mutate LAYERS in this process.
        """
        # Convert LAYERS into a grammar
        grammar = build_grammar(trees)

        grammar, new_trees, coalesce_caused = coalesce(oracle, trees, grammar, new_bubble)
        if coalesce_caused and isinstance(new_bubble, tuple):
            print(new_bubble)
            # if (new_bubble[0].new_nt, new_bubble[1].new_nt) not in {('t961', 't4698'), ('t4978', 't8506')}:
            #     if not check_recall(oracle, grammar):
            #         print(f"Introduced imprescision at {new_bubble}")
        if not coalesce_caused and not isinstance(new_bubble, tuple):
            grammar, new_trees, partial_coalesces = coalesce_partial(oracle, trees, grammar, new_bubble)
            if partial_coalesces:
                print("\n(partial)")
                coalesce_caused = True

        # grammar = minimize(grammar)
        new_size = grammar.size()
        if coalesce_caused:
            return 1, new_trees
        else:
            return 0, trees

    # Run the character class algorithm to create the first layer of tree
    # best_trees, classes = derive_classes(oracle, leaves)
    best_trees = build_naive_parse_trees(leaves)
    grammar = build_grammar(best_trees)
    print("Beginning coalescing...")
    grammar, best_trees, _ = coalesce(oracle, best_trees, grammar)
    grammar, best_trees, _ = coalesce_partial(oracle, best_trees, grammar)

    max_example_size = max([len(leaf_lst) for leaf_lst in leaves])

    # Main algorithm loop
    for group_size in range(3, MAX_GROUP_LEN):
        count = 1
        updated = True
        while updated:
            all_groupings = group(best_trees, group_size)
            updated, nlg = False, len(all_groupings)
            for i, grouping in enumerate(all_groupings):
                if i == 1000:
                    break
                print(('[Group len %d] Bubbling iteration %d (%d/%d)...' % (group_size, count, i + 1, nlg)).ljust(50), end='\r')
                ### Perform the bubble
                if isinstance(grouping, Bubble):
                    new_trees = apply(grouping, best_trees)
                    new_score, new_trees = score(new_trees, grouping)
                    grouping_str = f"Successful grouping (single): {grouping.bubbled_elems}"
                else:
                    bubble_one = grouping[0]
                    bubble_two = grouping[1]
                    new_trees = apply(bubble_one, best_trees)
                    new_trees = apply(bubble_two, new_trees)
                    new_score, new_trees = score(new_trees, grouping)
                    grouping_str = f"Successful grouping (double): {bubble_one.bubbled_elems}, {bubble_two.bubbled_elems}"
                ### Score
                if new_score > 0:
                    print()
                    print(grouping_str)
                    best_trees = new_trees
                    updated = True
                    break

            count = count + 1
        if group_size > max_example_size:
            break

    return best_trees, {}


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

    def partially_coalescable(replaceable_everywhere: str, replaceable_in_some_rules: str, trees: ParseTreeList) -> Dict[
        Tuple[str, Tuple[str]], List[int]]:
        """
        `replaceable_everywhere` and `replaceable_in_some_rules` are both nonterminals

        If `replaceable_in_some_rules` can replace `replaceable_everywhere` at every
        occurrence of `replaceable_everywhere`, returns the rules (expansions) in which
        `replaceable_in_some_rules` can be replaced by `replaceable_everywhere`
        """
        language_expanded = False
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

        if not trees.represented_by_derived_grammar(everywhere_by_some_candidates):
            language_expanded = True
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

            if trees.represented_by_derived_grammar(candidate_strs):
                replacing_positions[(rule[0], tuple(rule[1]))].append(posn)
                continue

            try:
                for candidate in candidate_strs:
                    oracle.parse(candidate)
                replacing_positions[(rule[0], tuple(rule[1]))].append(posn)
                language_expanded = True
            except ParseException as e:
                continue

        if not language_expanded:
            return []
        return replacing_positions

    def get_updated_grammar(old_grammar, partial_replacement_locs: Dict[Tuple[str, Tuple[str]], List[int]],
                            full_replacement_nt: str, nt_to_partially_replace: str, new_nt: str):
        """
        Creates a copy of `old_grammar` so that the locations in `partial_replacement_locs` are replaced by `new_nt`, and all
        occurrences of `full_relacement_nt` are replaced by `new_nt`
        """
        # Keep track of whether nt to partially replace still occurs on some rhss
        partially_replace_on_rhs = False
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
                    elif body[idx] == nt_to_partially_replace:
                        partially_replace_on_rhs = True
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
        if not partially_replace_on_rhs:
            grammar.rules.pop(nt_to_partially_replace)
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

    def get_updated_trees(trees: ParseTreeList, rules_to_replace: Dict[Tuple[str, Tuple[str]], List[int]],
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
    trees = ParseTreeList(trees, grammar)
    for nt_to_fully_replace in fully_replaceable:
        for nt_to_partially_replace in partially_replaceable:
            while nt_to_fully_replace in fully_replaced and nt_to_fully_replace != START:
                nt_to_fully_replace = fully_replaced[nt_to_fully_replace]
            while nt_to_partially_replace in fully_replaced and nt_to_partially_replace != START:
                nt_to_partially_replace = fully_replaced[nt_to_partially_replace]
            if nt_to_fully_replace == nt_to_partially_replace:
                continue
            if nt_to_partially_replace == 't9' and nt_to_fully_replace == 't0':
                pass
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
                inner_trees = get_updated_trees(trees, replacement_positions, nt_to_fully_replace, new_nt)
                trees = ParseTreeList(inner_trees, grammar)
                fully_replaced[nt_to_fully_replace] = new_nt
                replacement_happened = True

    trees = trees.inner_list
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



    def replacement_valid(replacer_derivable_strings, replacee, trees : ParseTreeList) -> Tuple[bool, Set[str]]:
        """
        Returns true if every string derivable from `replacee` in `trees` can be replaced
        by every string in `replacer_derivable_strings`
        """

        # Get the set of positive examples with strings derivable from replacer
        # replaced with strings derivable from replacee
        replaced_strings = set()
        for tree in trees:
            replaced_strings.update(get_strings_with_replacement(tree, replacee, replacer_derivable_strings))

        if len(replaced_strings) == 0:
            # TODO: See the failing doctest in bubble.py
            import pickle
            pickle.dump(coalesce_target, open('overlap-bug.pkl', "wb"))
            print(f"Oopsie with {coalesce_target}.\nPretty sure this is an overlap bug that I know of.... so let's just skip it")
            return False, set()
        #assert (replaced_strings)

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
                return False, set()
        return True, set(replaced_strings)

    def replacement_valid_and_expanding(nt1, nt2, trees: ParseTreeList):
        """
        Returns true if nt1 and nt2 can be merged in the grammar while expanding the set of inputs accepted
        by the grammar, and not admitting any invalid inputs.
        """
        nt1_derivable_strings = set()
        nt2_derivable_strings = set()

        if isinstance(coalesce_target, tuple):
            nt1_derivable_strings.update(lvl_n_derivable(trees, nt1, 1))
            nt2_derivable_strings.update(lvl_n_derivable(trees, nt2, 1))
        else:
            nt1_derivable_strings.update(lvl_n_derivable(trees, nt1, 0))
            nt2_derivable_strings.update(lvl_n_derivable(trees, nt2, 0))


        # First check if the replacement is expanding
        if nt1_derivable_strings == nt2_derivable_strings:
            return False

        nt1_valid, nt1_check_strings = replacement_valid(nt1_derivable_strings, nt2, trees)
        if not nt1_valid:
            return False
        nt2_valid, nt2_check_strings = replacement_valid(nt2_derivable_strings, nt1, trees)
        if not nt2_valid:
            return False

        base_strings = trees.represented_strings()

        if nt1_check_strings.issubset(base_strings) and nt2_check_strings.issubset(base_strings):
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
    if isinstance(coalesce_target, Bubble):
        first = coalesce_target.new_nt
        for second in nonterminals:
            if first == second:
                continue
            pairs.append((first, second))
    elif isinstance(coalesce_target, tuple):
        pair = (coalesce_target[0].new_nt, coalesce_target[1].new_nt)
        pairs.append(pair)
    else:
        for i in range(len(nonterminals)):
            for j in range(i + 1, len(nonterminals)):
                first, second = nonterminals[i], nonterminals[j]
                pairs.append((first, second))

    coalesce_caused = False
    coalesced_into = {}
    checked = set()
    tree_list = ParseTreeList(trees, grammar)
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
        if replacement_valid_and_expanding(first, second, tree_list):
            if first == START or second == START:
                class_nt = START
            else:
                class_nt = allocate_tid()
            classes = {class_nt: [first, second]}
            get_class = {first: class_nt, second: class_nt}
            coalesced_into[first] = class_nt
            coalesced_into[second] = class_nt
            grammar = get_updated_grammar(classes, get_class, grammar)
            new_inner_trees = get_updated_trees(get_class, tree_list.inner_list)
            tree_list = ParseTreeList(new_inner_trees, grammar)
            coalesce_caused = True

    trees = tree_list.inner_list
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
