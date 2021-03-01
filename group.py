import random
from collections import defaultdict
from typing import Union, List, Dict, Tuple

from bubble import Bubble
from next_tid import allocate_tid
from parse_tree import ParseNode

last_bubble_lst = None
last_bubble_pairs = None

def group(trees, max_group_size, last_applied_bubble = None) -> List[Bubble]:
    """
    TREES is a set of ParseNodes.

    Returns the set of all possible bubble of nonterminals in TREES,
    where each bubble is a data structure holding information about a
    grouping of contiguous nonterminals in TREES.
    """

    # Helper tracking if a subsequence is only seen as the "full" child of another nonterminal,
    # I.e. t2 t3 t4 in t1 -> t2 t3 t4, but not in t1 -> t2 t2 t3 t4
    full_bubbles = defaultdict(int)

    def add_groups_for_tree(tree: ParseNode, bubbles: Dict[str, Bubble], tree_idx, child_idxs, left_context="START", right_context ="END"):
        """
        Add all groups possible groupings derived from the parse tree `tree` to `groups`.
        """
        children_lst = tree.children
        # if not re.match("t([0-9]+)", tree.payload):
        #     print("skipping subtree:" tree)
        #     return

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
                    bubble.add_source(tree_idx, child_idxs, (i, j-1))
                else:
                    bubble: Bubble = bubbles[tree_substr]
                    bubble.add_occurrence()
                    bubble.add_context(lhs_context, rhs_context)
                    bubble.add_source(tree_idx, child_idxs, (i, j-1))

        # Recurse down in the other layers
        for i, child in enumerate(tree.children):
            lhs = left_context if i == 0 else 'DUMMY'
            rhs = right_context if i == len(tree.children) else 'DUMMY'
            if not child.is_terminal:
                add_groups_for_tree(child, bubbles, tree_idx, child_idxs + [i], lhs, rhs)

    # Compute a set of all possible groupings
    bubbles = {}
    for tree_num, tree in enumerate(trees):
        add_groups_for_tree(tree, bubbles, tree_num, [])

    # Remove sequences if they're the full list of children of a rule and don't appear anywhere else.
    # Prevents us from adding ridiculous layers of indirection.
    # TODO: I think this does prevent us from learning grammars that require indirection,
    # but everything I've tried still gets us in a situation where we eternally bubble
    # up the same sequence,
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
    bubbles = list(bubbles.items())
    if len(bubbles) > 100:
        bubbles = bubbles[:100]
    random.shuffle(bubbles)
    return bubbles