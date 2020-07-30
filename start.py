import re
from collections import defaultdict

from parse_tree import ParseNode
from grammar import *
from graph import Graph
from input import clean_terminal
from union import UnionFind
import numpy as np

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
START = allocate_tid() # The start nonterminal is t0

def build_start_grammar(oracle, config, leaves):
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
    trees, classes = build_trees(oracle, config, leaves)
    print('Building initial grammar...'.ljust(50), end='\r')
    grammar = build_grammar(config, trees)
    print('Coalescing nonterminals...'.ljust(50), end='\r')
    grammar, coalesce_caused = coalesce(oracle, config, trees, grammar)
    print('Minimizing initial grammar...'.ljust(50), end='\r')
    grammar = minimize(config, grammar)
    return grammar

def derive_classes(oracle, config, leaves):
    """
    Given a list of positive examples in LEAVES, uses a replacement algorithm
    to determine which tokens belong to the same character classes. Each character
    class is given a new nonterminal, which will be the disjunction of each of
    the characters in the class in every grammar. Characters that do not belong
    to any classes are still given a unique nonterminal. Returns the new layer
    in the tree that is created by bubbling up each of the terminals to their
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
        replaced_leaves = [[ParseNode(replacer if leaf.payload == replacee else leaf.payload, leaf.is_terminal, leaf.children) for leaf in tree] for tree in leaves]
        replaced_examples = [''.join([pn.payload for pn in tree]) for tree in replaced_leaves]
        for example in replaced_examples:
            try: oracle.parse(example)
            except: return False
        return True

    # Define helpful data structures
    terminals = list(config['TERMINALS'])
    terminals.remove('') # Remove epsilon terminal
    terminals = [t.replace('"', '') for t in terminals]
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

    # Update each of the terminals in leaves to instead be a new nonterminal
    # ParseNode pointing to the original terminal. Return the updated list
    # as well as a mapping of nonterminal to the character class it defines.
    return [[ParseNode(get_class[leaf.payload], False, [leaf]) for leaf in tree] for tree in leaves], classes

def group(layers):
    """
    LAYERS is a set of top-layers of half-built Parse Trees. Each of the
    intermediate ParseTrees are represented as a list of nodes at the top-most layer.

    Returns the set of all possible groupings of nonterminals in LAYERS,
    where each grouping is a data structure holding information about a
    gropuing of contiguous nonterminals in LAYERS.

    A grouping is a two-element tuple data structure that represents a contiguous
    sequence of nonterminals that appears someplace in LAYERS. The first element
    is a string representation of this sequence. The second element is itself
    a two-element tuple that contains a list representation of the sequence, as
    well as the fresh nonterminal assigned to the grouping.
    """
    # Compute a set of all possible groupings
    groups = {}
    for tree_lst in layers:
        for i in range(len(tree_lst)):
            for j in range(i + 2, len(tree_lst) + 1):
                tree_sublist = tree_lst[i:j]
                tree_substr = ''.join([t.payload for t in tree_sublist])
                if not tree_substr in groups:
                    groups[tree_substr] = (tree_sublist, allocate_tid(), 1)
                else:
                    tree_sublist, tid, count = groups[tree_substr]
                    groups[tree_substr] = (tree_sublist, tid, count + 1)

    # Return the set of repeated groupings as an iterable
    groups = {k:v for k, v in groups.items() if v[2] > 1}
    return list(groups.items())

def apply(grouping, layers):
    """
    GROUPING is a two-element tuple data structure that represents a contiguous
    sequence of nonterminals that appears someplace in LAYERS. The first element
    is a string representation of this sequence. The second element is itself
    a two-element tuple that contains a list representation of the sequence, as
    well as the fresh nonterminal assigned to the grouping.

    LAYERS is a set of top-layers of half-built Parse Trees. Each of the
    intermediate ParseTrees are represented as a list of nodes at the top-most layer.

    Applies a GROUPING data structure to LAYERS by bubbling up the grouping
    to create a new top layer. Does not mutate LAYERS.
    """
    def matches(group_lst, layer):
        """
        GROUP_LST is a contiguous subarray of ParseNodes that are grouped together.
        This method requires that len(GRP_LST) > 0.

        LAYER is the top layer of one half-built ParseTree, implemented as a
        list of ParseNodes.

        Returns the index at which GROUP_LST appears in LAYER, and returns -1 if
        the GROUP_LST does not appear in the LAYER. Does not mutate LAYER.
        """
        ng, nl = len(group_lst), len(layer)
        for i in range(nl):
            layer_ind = i # Index into layer
            group_ind = 0 # Index into group
            while group_ind < ng and layer_ind < nl and layer[layer_ind].payload == group_lst[group_ind].payload:
                layer_ind += 1
                group_ind += 1
            if group_ind == ng: return i
        return -1

    def apply_single(layer):
        """
        LAYER is the top layer of one half-built ParseTree, implemented as a
        list of ParseNodes.

        Applies the GROUPING data structure to a single tree. Applies that
        GROUPING to LAYER as many times as possible. Does not mutate LAYER.

        Returns the new layer. If no updates can be made, do nothing.
        """
        group_str, (group_lst, id, _) = grouping
        new_layer, ng = layer[:], len(group_lst)

        ind = matches(group_lst, new_layer)
        while ind != -1:
            parent = ParseNode(id, False, new_layer[ind : ind + ng])
            new_layer[ind : ind + ng] = [parent]
            ind = matches(group_lst, new_layer)

        return new_layer

    return [apply_single(layer) for layer in layers]

def build_trees(oracle, config, leaves):
    """
    ORACLE is a Lark parser for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    CONFIG is the required configuration options for GrammarGenerator classes.

    DATA is a map containing both the positive and negative examples used to
    train the stochastic search.

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
    def score(layers):
        """
        LAYERS is a set of top-layers of half-built Parse Trees. Each of the
        intermediate ParseTrees are represented as a list of nodes at the top-most layer.

        Assumes LAYERS is a half-formed parse tree that defines a valid grammar.
        Converts LAYERS into a grammar and returns its positive score.
        Does not mutate LAYERS in this process.
        """
        # Convert LAYERS into a grammar and generator
        trees = [ParseNode(START, False, tree_lst[:]) for tree_lst in layers]
        grammar = build_grammar(config, trees)
        grammar, coalesce_caused = coalesce(oracle, config, trees, grammar)
        if coalesce_caused:
            return 1
        else:
            return 0

    # Run the character class algorithm to create the first layer of tree
    layers, classes = derive_classes(oracle, config, leaves)
    best_score, best_layers, updated, count = score(layers), layers, True, 1

    # Main algorithm loop
    while updated:
        layer_group = group(layers)
        updated, nlg = False, len(layer_group)
        for i, grouping in enumerate(layer_group):
            print(('Bubbling iteration (%d, %d, %d)...' % (count, i + 1, nlg)).ljust(50), end='\r')
            new_layers = apply(grouping, layers)
            new_score = score(new_layers)
            if new_score > 0:
                best_layers = new_layers
                updated = True
                break
        layers, count = best_layers, count + 1

    return [ParseNode(START, False, tree_lst[:]) for tree_lst in layers], classes

def build_grammar(config, trees):
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

def coalesce(oracle, config, trees, grammar : Grammar):
    """
    ORACLE is a Lark parser for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    CONFIG is the required configuration options for GrammarGenerator classes.

    TREES is a list of fully constructed parse trees.

    GRAMMAR is a GrammarNode that is the disjunction of the TREES.

    This method coalesces nonterminals that are equivalent to each other.
    Equivalence is determined by replacement.

    RETURNS: the grammar after coalescing, and whether any nonterminals were
    actually coalesced with each other (found equivalent).
    """
    def replaced_string(tree, replacer_string, replacee_nt):
        """
        Returns the string generated by the leaves of the parse tree TREE, with
        the exception that any string derived from the REPLACEE_NT is replaced
        by the string REPLACER_STRING.
        """
        if tree.is_terminal:
            return tree.payload
        elif tree.payload == replacee_nt:
            return replacer_string
        else:
            return ''.join([replaced_string(c, replacer_string, replacee_nt) for c in tree.children])

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

    def replaces(replacer, replacee):
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
        for replacer_string in replacer_derivable_strings:
            for tree in trees:
                replaced_strings.add(replaced_string(tree, replacer_string, replacee))

        # Return True if all the replaced_strings are valid
        for s in replaced_strings:
            try: oracle.parse(s)
            except: return False
        return True

    def epsilon_replaces(replacee):
        """
        For every string derived from REPLACEE, replace it with epsilon,
         and check if the resulting string is still valid.

        Return True if this is the always the case.

        Relies on the fact that TREES is unchanged from the time when it was
        inputted into coalesce.
        """
        # Get the set of positive examples with strings derivable replacee
        # replaced with epsilon
        replaced_strings = set()
        for tree in trees:
            replaced_strings.add(replaced_string(tree, '', replacee))

        # Return True if all the replaced_strings are valid
        for s in replaced_strings:
            try:
                oracle.parse(s)
            except:
                return False
        return True

    def nt_derivable(nt):
        """
        Returns a set of references to Rule Bodies containing a single nonterminal,
        of type NT, that are derivable directly from the start nonterminal in GRAMMAR.

        A nonterminal is directly derivable from the start nonterminal if it can
        be derived by a series of replacement rules from the start nonterminal,
        where none of those replacement rules contain any terminals.
        """
        X = [] # The set of nonterminal SymbolNodes directly derivable from START
        F = [] # The search fringe of SymbolNodes

        def is_nonterm(term):
            return re.match("t[0-9]+", term) is not None

        # Initialize X and F to those nonterminals directly derivable from t0
        # with a derivability depth of one
        for rule in [rule_node for rule_node in grammar.rules.values() if rule_node.start == START]:
            for body in rule.bodies:
                if len(body) == 1 and is_nonterm(body[0]):
                    X.append(body)
                    F.append(body)

        # Continue searching in a BFS-like style until there is nothing left
        while len(F) > 0:
            nt_node = F.pop()
            for rule in [rule_node for rule_node in grammar.rules.values() if rule_node.start == nt_node[0]]:
                # Since each nonterminal expands to a finite and positive length
                # string, it suffices to check that the rule is just one nonterminal
                for body in rule.bodies:
                    if len(body) == 1 and is_nonterm(body[0]):
                        X.append(body)
                        F.append(body)

        # Filter the final set of SymbolNode references by NT and return
        output = []
        for body in X:
            if body[0] == nt:
                output.append(body)
        return output

    # Define helpful data structures
    nonterminals = set(grammar.rules.keys())
    nonterminals.remove("start")
    nonterminals = list(nonterminals)
    uf = UnionFind(nonterminals)

    coalesce_caused = False
    for i in range(len(nonterminals)):
        for j in range(i + 1, len(nonterminals)):
            # Iterate through each unique pair of nonterminals
            first, second = nonterminals[i], nonterminals[j]

            # If the nonterminals can replace each other in every context, they
            # must belong to the same character class
            if not uf.is_connected(first, second) and replaces(first, second) and replaces(second, first):
                coalesce_caused = True
                uf.connect(first, second)

    # Define a mapping and a reverse mapping between a set of equivalent
    # nonterminals and the newly generated nonterminal for that class
    classes, get_class = {}, {}
    for leader, nts in uf.classes().items():
        if len(nts) > 1:
            class_nt = allocate_tid()
            classes[class_nt] = nts
        for nt in nts:
            if len(nts) == 1:
                get_class[nt] = nt
            else:
                get_class[nt] = class_nt

    # Traverse through the grammar, and update each nonterminal to point to
    # its class nonterminal
    for nonterm in grammar.rules:
        if nonterm == "start":
            continue
        for body in grammar.rules[nonterm].bodies:
            for i in range(len(body)):
                # The keys of the rules determine the set of nonterminals
                if body[i] in grammar.rules.keys():
                    body[i] = get_class[body[i]]

    # Add the alternation rules for each class into the grammar
    for class_nt, nts in classes.items():
        for nt in nts:
            rule = Rule(class_nt)
            rule.add_body([nt])
            grammar.add_rule(rule)

    # In this case, t0 was assigned to a class. We must ensure that under this
    # scheme, t0 is not derivable from itself, which causes infinite recursion
    if get_class[START] != START:
        # Derive the rules for the conservative_class_nt and new_class_nt
        conservative_class_nt = get_class[START]
        new_class_nt = allocate_tid()

        # Find all the conservative_class_nts that are directly derivable from
        # start, and leave them alone. Update all the rest of the
        # conservative_class_nts to point to new_class_nt
        # We accomplish this by first pointing all the conservative_class_nts
        # to new_class_nt, then searching for all new_class_nts that are directly
        # derivable from START, and replacing those back with conservative_class_nt
        for rule_node in grammar.rules.values():
            for body in rule_node.bodies:
                for i in range(len(body)):
                    if body[i] == conservative_class_nt:
                        body[i] = new_class_nt

        for rule_body in nt_derivable(new_class_nt):
            rule_body[0] = conservative_class_nt

        # Update the final rules for the conservative and new class nonterminals
        # Remove rules of the form conservative_class_nt -> START
        conservative_rule : Rule = grammar.rules[conservative_class_nt]
        to_pop = []
        for i in range(len(conservative_rule.bodies)):
            body = conservative_rule.bodies[i]
            if len(body) == 1 and body[0] == START:
                to_pop.append(i)

        for i in reversed(to_pop):
            conservative_rule.bodies.pop(i)

        new_class_rule : Rule = Rule(new_class_nt)
        new_class_rule.add_body([conservative_class_nt])
        new_class_rule.add_body([START])
        grammar.add_rule(new_class_rule)

    return grammar, coalesce_caused

def minimize(config, grammar):
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
        assert(START not in map)
        for rule in grammar.rules.values():
            for body in rule.bodies:
                to_fix = [elem in map for elem in body]
                # Reverse to ensure that we don't mess up the indices
                while any(to_fix):
                    ind = to_fix.index(True)
                    nt = body[ind]
                    body[ind:ind+1] = map[nt]
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
    X, updated = {}, True # updated determines the stopping condition

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
    Y = {k:grammar.rules[k].bodies[0] for k in used_once if len(grammar.rules[k].bodies) == 1}
    grammar = update(grammar, Y)
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
