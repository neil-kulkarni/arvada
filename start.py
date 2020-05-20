import re
from parse_tree import ParseNode
from generator import *

def build_start_grammars(config, leaves):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    LEAVES is a list of positive examples, each expressed as a list of tokens
    (ParseNode objects).

    Returns a set of starting grammar generators whose corresponding grammars
    each match at least one input example.
    """
    trees = build_trees(leaves)
    return [build_generator(config, tree) for tree in trees]

def group(trees):
    """
    TREES is composed of half-built ParseTrees. Each of the intermediate
    ParseTrees are represented as a list of nodes at the top-most layer.

    Given a list of TREES, computes and returns a map of the most common
    payloads in the ParseNodes. Each returned map entry is given a unique
    identifier ti for some i > 1, reserving i = 0 for the start node.

    Trivial groups are filtered out, including groups that only appear once or
    groups that only consist of one token.

    Returns the group first sorted by frequency so that most frequently occuring
    substrings come first, then sorted by length, so that longer substrings are
    preferred, like in the maximal-munch rule.
    """
    counts = {}
    next_id = 1 # Reserve t0 for the start nonterminal in each grammar
    for tree_lst in trees:
        for i in range(len(tree_lst)):
            for j in range(i + 1, len(tree_lst) + 1):
                tree_sublist = tree_lst[i:j]
                tree_substr = ''.join([t.payload for t in tree_sublist])
                if tree_substr in counts:
                    count, sublist, id = counts[tree_substr]
                    counts[tree_substr] = (count + 1, sublist, id)
                else:
                    counts[tree_substr] = (1, tree_sublist, 't%d' % next_id)
                    next_id += 1

    # Filter out tokens that only appear once
    counts = {k:v for k, v in counts.items() if v[0] > 1}
    # Filter out nonterminals composed of only one token
    counts = {k:v for k, v in counts.items() if len(v[1]) > 1}

    # Sort first by frequency, then by key-length
    counts = sorted(counts.items(), key=lambda elem: len(elem[0]), reverse=True)
    return sorted(counts, key=lambda elem: elem[1][0], reverse=True)

def matches(grouping, layer):
    """
    LAYER is the top layer of one half-built ParseTree.

    The GROUPING of the TREES is an implicit map of a list of tokens to the
    frequency at which the list occurs in the top layer of TREES, with most
    frequent token appearing first.

    Optional arguments of start and end can be passed in with the search.

    Returns the index at which grouping appears in layer, and returns -1 if
    the grouping does not appear in the layer.
    """
    ng, nl = len(grouping), len(layer)
    for i in range(nl):
        layer_ind = i # Index into layer
        group_ind = 0 # Index into group
        while group_ind < ng and layer_ind < nl and layer[layer_ind].payload == grouping[group_ind].payload:
            layer_ind += 1
            group_ind += 1
        if group_ind == ng: return i
    return -1

def apply(grouping, trees):
    """
    TREES is composed of half-built ParseTrees. Each of the intermediate
    ParseTrees are represented as a list of nodes at the top-most layer. This
    algorithm applies GROUPING to the topmost layer of each tree to progress
    in building the tree. This algorithm should be repeatedly called until
    each of the trees consists of a list of a single node, the root.

    The GROUPING of the TREES is an implicit map of a list of tokens to the
    frequency at which the list occurs in the top layer of TREES, with most
    frequent token appearing first.

    Algorithm: For each of the trees in TREES, greedily group the ParseNodes in
    accord with GROUPING so that the most frequently appearing tokens are grouped
    first. Perform only one iteration of this greedy grouping scheme, so that
    in order to completely build the tree, this method must be called many times.
    Grouped nodes become the children of new ParseNodes, which are inserted
    into the top layer list of the trees. The updated top layer lists are returned.

    In other words, this method, given the ith layer of the tree and the set of
    groupings for that layer, returns the i + 1st layer of the tree, for each
    of the input trees in TREES.
    """

    def apply_single(group_lst, tree_lst):
        """
        Applies the grouping to a single tree in the manner defined above.
        Only a single new ParseNode is created at one time.
        Returns the updated TREE_LST.

        If no groupings can be found, create a start node pointing to each
        of the remaining nodes in the parse tree.
        """
        if len(tree_lst) == 0:
            return tree_lst

        for group_str, tup in grouping:
            count, group_lst, id = tup
            ng = len(group_lst)
            ind = matches(group_lst, tree_lst)
            if ind != -1:
                parent = ParseNode(group_str, False, tree_lst[ind : ind + ng])
                parent.payload = id
                tree_lst[ind : ind + ng] = [parent]
                return tree_lst
        start = ParseNode('t0', False, tree_lst[:])
        start.payload = 't0'
        return [start]

    return [apply_single(grouping, tree) for tree in trees]

def build_trees(leaves):
    """
    LEAVES should be a list of lists (one list for each input example), where
    each sublist contains the tokens that built that example, as ParseNodes.

    Iteratively builds parse trees from each of the examples and returns a list
    of ParseNode references

    Algorithm:
        1. Initialization
            - S <- input examples
            - G <- group(S)
        2. while there is some unfinished tree:
            a. Build new ParseNodes from S
            b. S <- set of ParseNodes
        3. return the set of finished ParseNodes
    """
    def finished(layers):
        """
        Helper function that returns when each of the trees in layers is
        composed of just a single root (has a length of 1), indicating that
        the algorithm is finished building all the trees.
        """
        return all([len(layer) <= 1 for layer in layers])

    grouping = group(leaves)
    layers = leaves

    while not finished(layers):
        layers = apply(grouping, layers)

    return [layer[0] for layer in layers]

def build_generator(config, tree):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    TREE is a fully constructed parse tree. This method builds a GrammarGenerator
    based on the parse tree, and returns it.
    """
    def build_rules(grammar_node, parse_node):
        """
        Adds the rules defined in PARSE_NODE and all of its subtrees to the
        GRAMMAR_NODE via recursion.
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
        rule_body = [SymbolNode(config, child.payload, child.is_terminal) for child in parse_node.children]
        grammar_node.children.append(RuleNode(config, parse_node.payload, rule_body))

        # Recurse on the children of this ParseNode so the rule they define
        # are also added to the grammar.
        # Terminals and nodes without children are taken care of by the base case.
        for child in parse_node.children:
            build_rules(grammar_node, child)

    # Initial grammar node without children, then fill its children.
    # Return the corresponding GrammarGenerator
    grammar_node = GrammarNode(config, tree.payload, [])
    build_rules(grammar_node, tree)
    return GrammarGenerator(config, grammar_node)

# TODOs
# 1. Take as input a list of ParseNode lists (requires updating positive example generation)
#    e.g. leaves = [[ParseNode('abc', True, None), ParseNode('d', True, None), ParseNode('e', True, None), ParseNode('f', True, None), ParseNode('g', True, None)], [ParseNode('abc', True, None), ParseNode('d', True, None), ParseNode('e', True, None)]]
