from typing import Optional

from parse_tree import ParseNode
from generator import *
from graph import Graph
from union import UnionFind
from score import Scorer
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

def build_start_grammar(oracle, config, data, leaves):
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
    trees, classes = build_trees(oracle, config, data, leaves)
    print('Building initial grammar...'.ljust(50), end='\r')
    grammar = build_grammar(config, trees)
    print('Coalescing nonterminals...'.ljust(50), end='\r')
    grammar = coalesce(oracle, config, trees, grammar)
    print('Minimizing initial grammar...'.ljust(50), end='\r')
    grammar = minimize(config, grammar)
    print('Converting into final grammar...'.ljust(50), end='\r')
    gen = convert(config, grammar)
    print('Adding alternation...'.ljust(50), end='\r')
    gen = add_alternation(config, data, gen, classes)
    print('Adding repetition...'.ljust(50), end='\r')
    gen = add_repetition(config, data, gen, classes)
    return gen

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
                    groups[tree_substr] = (tree_sublist, allocate_tid())

    # Return the set of groupings as an iterable
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
        group_str, (group_lst, id) = grouping
        new_layer, ng = layer[:], len(group_lst)

        ind = matches(group_lst, new_layer)
        while ind != -1:
            parent = ParseNode(id, False, new_layer[ind : ind + ng])
            new_layer[ind : ind + ng] = [parent]
            ind = matches(group_lst, new_layer)

        return new_layer

    return [apply_single(layer) for layer in layers]

def build_trees(oracle, config, data, leaves):
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
    def score(layers, nonterm : Optional[str] = None):
        """
        LAYERS is a set of top-layers of half-built Parse Trees. Each of the
        intermediate ParseTrees are represented as a list of nodes at the top-most layer.

        `nonterm` is the nonterminal that was just introduced to the parse trees.

        Assumes LAYERS is a half-formed parse tree that defines a valid grammar.
        Converts LAYERS into a grammar and returns its positive score.
        Does not mutate LAYERS in this process.
        """
        # Conver LAYERS into a grammar and generator
        trees = [ParseNode(START, False, tree_lst[:]) for tree_lst in layers]
        grammar = build_grammar(config, trees)
        grammar = coalesce(oracle, config, trees, grammar, nonterm)
        grammar = minimize(config, grammar)
        gen = convert(config, grammar)
        grammar = gen.generate_grammar()
        # Return the score of this grammar
        scorer = Scorer(config, data, grammar, gen)
        scorer.score(grammar, gen)
        return scorer.score_map['pos'][0]

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
            new_score = score(new_layers, grouping[1][1])
            if new_score > best_score:
                best_score = new_score
                best_layers = new_layers
                updated = True
        layers, count = best_layers, count + 1
    print(f"Best score is: {best_score}\n\n")
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
        rule_body = [SymbolNode(config, child.payload, child.is_terminal) for child in parse_node.children]
        rule = RuleNode(config, parse_node.payload, rule_body)
        rule_str = ''.join([sn.choice for sn in rule.children])
        if rule.lhs not in rule_map: rule_map[rule.lhs] = set()
        if rule_str not in rule_map[rule.lhs]:
            grammar_node.children.append(rule)
            rule_map[rule.lhs].add(rule_str)

        # Recurse on the children of this ParseNode so the rule they define
        # are also added to the grammar.
        for child in parse_node.children:
            build_rules(grammar_node, child, rule_map)

    # Construct the initial grammar node without children, then fill them.
    # Return the corresponding GrammarNode
    grammar_node, rule_map = GrammarNode(config, START, []), {}
    for tree in trees:
        build_rules(grammar_node, tree, rule_map)
    return grammar_node

def coalesce(oracle, config, trees, grammar, nonterm: Optional[str] = None):
    """
    ORACLE is a Lark parser for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    CONFIG is the required configuration options for GrammarGenerator classes.

    TREES is a list of fully constructed parse trees.

    GRAMMAR is a GrammarNode that is the disjunction of the TREES.

    NONTERM is a nonterminal to coalesce with.

    This method coalesces nonterminals that are equivalent to each other. If
    `nonterm` is provided, only consider nonterminals equivalent to `nonterm`.
    Equivalence is determined by replacement.
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

    def nt_derivable(nt):
        """
        Returns a set of references to SymbolNodes of type NT that are derivable
        directly from the start nonterminal in GRAMMAR.

        A nonterminal is directly derivable from the start nonterminal if it can
        be derived by a series of replacement rules from the start nonterminal,
        where none of those replacement rules contain any terminals.
        """
        X = set() # The set of nonterminal SymbolNodes directly derivable from START
        F = [] # The search fringe of SymbolNodes

        # Initialize X and F to those nonterminals directly derivable from t0
        # with a derivability depth of one
        for rule in [rule_node for rule_node in grammar.children if rule_node.lhs == START]:
            symbol = next(iter(rule.children))
            if len(rule.children) == 1 and not symbol.is_terminal:
                X.add(symbol)
                F.append(symbol)

        # Continue searching in a BFS-like style until there is nothing left
        while len(F) > 0:
            nt_node = F.pop()
            for rule in [rule_node for rule_node in grammar.children if rule_node.lhs == nt_node.choice]:
                # Since each nonterminal expands to a finite and positive length
                # string, it suffices to check that the rule is just one nonterminal
                symbol = next(iter(rule.children))
                if len(rule.children) == 1 and not symbol.is_terminal and symbol not in X:
                    X.add(symbol)
                    F.append(symbol)

        # Filter the final set of SymbolNode references by NT and return
        output = set()
        for symbol_node in X:
            if symbol_node.choice == nt:
                output.add(symbol_node)
        return output

    # Define helpful data structures
    nonterminals = list(set([rule.lhs for rule in grammar.children]))
    uf = UnionFind(nonterminals)

    if nonterm is not None:
        assert(nonterm in nonterminals, "Error: {nonterm} is not in the grammar's nonterminals. Cannot coalesce")

    for i in range(len(nonterminals)):
        if nonterm is None:
            for j in range(i + 1, len(nonterminals)):
                first, second = nonterminals[i], nonterminals[j]
                # If the nonterminals can replace each other in every context, they
                # must belong to the same character class
                if not uf.is_connected(first, second) and replaces(first, second) and replaces(second, first):
                    uf.connect(first, second)
        # If `nonterm` is given, only try the pairs that contain it.
        else:
            first, second = nonterminals[i], nonterm
            if first == second:
                continue
            if not uf.is_connected(first, second) and replaces(first, second) and replaces(second, first):
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
    for rule_node in grammar.children:
        for symbol_node in rule_node.children:
            if not symbol_node.is_terminal:
                symbol_node.choice = get_class[symbol_node.choice]

    # Add the alternation rules for each class into the grammar
    for class_nt, nts in classes.items():
        for nt in nts:
            rule = RuleNode(config, class_nt, [SymbolNode(config, nt, False)])
            grammar.children.append(rule)

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
        for rule_node in grammar.children:
            for symbol_node in rule_node.children:
                if symbol_node.choice == conservative_class_nt:
                    symbol_node.choice = new_class_nt

        for symbol_node in nt_derivable(new_class_nt):
            symbol_node.choice = conservative_class_nt

        # Update the final rules for the conservative and new class nonterminals
        grammar.children = [rule_node for rule_node in grammar.children if not (rule_node.lhs == conservative_class_nt and next(iter(rule_node.children)).choice == START)]
        grammar.children.append(RuleNode(config, new_class_nt, [SymbolNode(config, conservative_class_nt, False)]))
        grammar.children.append(RuleNode(config, new_class_nt, [SymbolNode(config, START, False)]))

    return grammar

def minimize(config, grammar):
    """
    Mutative method that deletes repeated rules from GRAMMAR and removes
    unnecessary layers of indirection.

    CONFIG is the required configuration options for GrammarGenerator classes.
    """
    def get_grammar_map(grammar_node):
        """
        Create a unique set of rules in GRAMMAR_NODE represented as a map
        """
        grammar_map = {}
        for rule in grammar_node.children:
            if rule.lhs not in grammar_map:
                grammar_map[rule.lhs] = ([], [])
            rule_str = ''.join([sn.choice for sn in rule.children])
            if rule_str not in grammar_map[rule.lhs][1]:
                rules, rule_strings = grammar_map[rule.lhs]
                rules.append(rule)
                rule_strings.append(rule_str)
        return grammar_map

    def update(grammar_node, map):
        """
        Given a MAP with nonterminals as keys and list of symbols as values,
        replaces every occurance of a nonterminal in MAP with its corresponding
        list of SymbolNodes in the the GRAMMAR_NODE. Then, the rules defining
        the keys in the grammar are removed.

        The START nonterminal must not appear in MAP, because its rule cannot
        be deleted.
        """
        for rule_node in grammar.children:
            to_fix = [sn.choice in map for sn in rule_node.children]
            while any(to_fix):
                ind = to_fix.index(True)
                nt = rule_node.children[ind]
                rule_node.children[ind:ind+1] = map[nt.choice]
                to_fix = [sn.choice in map for sn in rule_node.children]
        grammar_node.children = [rule for rule in grammar_node.children if rule.lhs not in map]
        return grammar_node

    # Remove all the repeated rules from the grammar
    grammar_map = get_grammar_map(grammar)
    new_grammar = GrammarNode(config, START, [])
    for rule_start in grammar_map:
        rules, _ = grammar_map[rule_start]
        for rule in rules:
            new_grammar.children.append(rule)
    grammar = new_grammar

    # Finds the set of nonterminals that expand directly to a single terminal
    # Let the keys of X be the set of these nonterminals, and the corresponding
    # values be the the SymbolNodes derivable from those nonterminals
    X, updated = {}, True # updated determines the stopping condition

    while updated:
        updated = False
        for rule_start in grammar_map:
            rules, _ = grammar_map[rule_start]
            if len(rules) == 1 and len(rules[0].children) == 1 and (rules[0].children[0].is_terminal or rules[0].children[0].choice in X):
                rule = next(iter(rules))
                if rule.lhs not in X and rule.lhs != START:
                    X[rule.lhs] = [X[sn.choice][0] if sn.choice in X else sn.choice for sn in rule.children]
                    updated = True

    # Update the set X so that the strings derivable from it are lists of
    # SymbolNodes instead of lists of strings
    for k in X: X[k] = [SymbolNode(config, s, True) for s in X[k]]

    # Update the grammar so that keys in X are replaced by values
    # Redefine the grammar map, since the grammar has likely changed
    grammar = update(grammar, X)
    grammar_map = get_grammar_map(grammar)

    # Finds the set of nonterminals that expand to a single string and that are
    # only used once in the grammar. Let the keys of Y be the set of these
    # nonterminals, and the corresponding values be the SymbolNodes derivable
    # from those nonterminals
    counts = {}
    for rule_node in grammar.children:
        for symbol_node in rule_node.children:
            if not symbol_node.is_terminal:
                n = symbol_node.choice
                counts[n] = counts.get(n, 0) + 1

    # Update the grammar so that keys in X are replaced by values
    used_once = [k for k in counts if counts[k] == 1 and k != START]
    Y = {k:grammar_map[k][0][0].children for k in used_once if len(grammar_map[k][0]) == 1}
    grammar = update(grammar, Y)
    return grammar

def convert(config, grammar):
    """
    Adds the finishing touches to the GRAMMAR, then returns the corresponding
    GrammarGenerator object.

    CONFIG is the required configuration options for GrammarGenerator classes.
    """
    # Wrap each terminal in the grammar in quotations
    for rule_node in grammar.children:
        for symbol_node in rule_node.children:
            if symbol_node.is_terminal and symbol_node.choice[0] != '"':
                symbol_node.choice = '"%s"' % (symbol_node.choice)

    # Return the GrammarGenerator
    return GrammarGenerator(config, grammar)

def add_alternation(config, data, gen, classes):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    DATA is a map containing both the positive and negative examples used to
    train the stochastic search.

    GEN is a GrammarGenerator object output of the previous stages of development.

    CLASSES is a map of nonterminal -> the character class that it defines.

    This function iterates through each of the symbols in the grammar, attempts
    to update the symbol by allowing alternation, and sees if that improves
    the grammar's positive score.
    """
    # Get the initial positive score of the original generator. Quit if >= 1.
    grammar = gen.generate_grammar()
    scorer = Scorer(config, data, grammar, gen)
    print('Alternation initial scoring...'.ljust(50), end='\r')
    scorer.score(grammar, gen)
    pos_score = scorer.score_map['pos'][0]
    if pos_score >= 1.0:
        return gen

    # Define the set of candidate replacements for any given symbol, as a list
    # of SymbolNodes. These are defined below
    class_terminals = set(['"%s"' % s for s in sum([v for v in classes.values() if len(v) > 1], [])])
    candidates = [SymbolNode(config, nt, False) for nt in gen.get_nonterminals()]
    candidates.extend([SymbolNode(config, t, True) for t in gen.get_terminals() if t not in class_terminals])
    candidates.extend([SymbolNode(config, '', True)]) # Epsilon is a valid candidate

    # Keep a map of created alternation rules, so we can ensure we don't duplicate rules
    alternation_rules = {}

    # Iterate through the grammar, attempting to add an alternation rule at
    # each symbol, representing the OR of the current symbol and any nonterminal
    # that appears in the grammar, any terminal that doesn't appear in a
    # character class, or epsilon. Also attempts to let each nonterminal also
    # go to epsilon.
    rule_nodes = list(gen.grammar_node.children)
    for i in range(len(rule_nodes)):
        rule_node = rule_nodes[i]
        if rule_node.lhs in classes:
            continue # Skip over character classes
        for j in range(len(rule_node.children)):
            # Create a copy of the grammar
            gen_cpy = gen.copy()
            sn_cpy = gen_cpy.grammar_node.children[i].children[j]

            # Add a minimial OR rule just containing the current symbol,
            # and update the symbol to point to that rule
            or_nt = allocate_tid()
            or_rule = RuleNode(config, or_nt, [sn_cpy.copy()])
            gen_cpy.grammar_node.children.append(or_rule)
            alternation_rules[or_nt] = [sn_cpy.choice]
            sn_cpy.choice = or_nt
            sn_cpy.is_terminal = False

            # Attempt to add each of the ORing canidates to the OR rule,
            # removing them if they do not help
            or_used = False
            for k in range(len(candidates)):
                candidate = candidates[k]
                new_or_rule = RuleNode(config, or_nt, [candidate])
                gen_cpy.grammar_node.children.append(new_or_rule)
                grammar_cpy = gen_cpy.generate_grammar()
                print(('Scoring alternation (%d/%d, %d/%d, %d/%d)...' % (i + 1, len(rule_nodes), j + 1, len(rule_node.children), k + 1, len(candidates))).ljust(50), end='\r')
                scorer.score(grammar_cpy, gen_cpy)
                new_pos_score = scorer.score_map['pos'][0]
                if new_pos_score > pos_score:
                    or_used = True
                    pos_score = new_pos_score
                    alternation_rules[or_nt].append(candidate.choice)
                else:
                    gen_cpy.grammar_node.children.pop()

            # If an alternation rule has been duplicated, use the old one
            if or_used:
                rest = {k:v for k, v in alternation_rules.items() if k != or_nt}
                equal_nts = [k for k in rest if rest[k] == alternation_rules[or_nt]]
                assert(len(equal_nts) <= 1)
                if len(equal_nts) == 1:
                    equal_nt = next(iter(equal_nts))
                    sn_cpy.choice = equal_nt
                    or_nt_rules = len(alternation_rules[or_nt])
                    gen_cpy.grammar_node.children = gen_cpy.grammar_node.children[:-or_nt_rules]
                    alternation_rules.pop(or_nt)
            else:
                alternation_rules.pop(or_nt)

            # Update the generator if this alternation helped
            if or_used:
                gen = gen_cpy
                updated = True
                if pos_score >= 1.0:
                    return gen

        # Attempt to add an epsilon rule for this rule start, removing it
        # if it does not help
        gen_cpy = gen.copy()
        eps_rule = RuleNode(config, rule_node.lhs, [SymbolNode(config, '', True)])
        gen_cpy.grammar_node.children.append(eps_rule)
        grammar_cpy = gen_cpy.generate_grammar()
        print(('Adding epsilon rule (%d/%d)...' % (i + 1, len(rule_nodes))).ljust(50), end='\r')
        scorer.score(grammar_cpy, gen_cpy)
        new_pos_score = scorer.score_map['pos'][0]
        if new_pos_score > pos_score:
            gen = gen_cpy
            pos_score = new_pos_score
            updated = True
            if pos_score >= 1.0:
                return gen

    # Return the final grammar
    return gen

def add_repetition(config, data, gen, classes):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    DATA is a map containing both the positive and negative examples used to
    train the stochastic search.

    GEN is a GrammarGenerator object output of the previous stages of development.

    CLASSES is a map of nonterminal -> the character class that it defines.

    This function iterates through each of the symbols in the grammar, attempts
    to update the symbol by allowing repetition, and sees if that improves
    the grammar's positive score.
    """
    # Get the initial positive score of the original generator. Quit if >= 1.
    grammar = gen.generate_grammar()
    scorer = Scorer(config, data, grammar, gen)
    print('Repetition initial scoring...'.ljust(50), end='\r')
    scorer.score(grammar, gen)
    pos_score = scorer.score_map['pos'][0]
    if pos_score >= 1.0:
        return gen

    # Iterate through the grammar, attempting to add a '+' rule at each symbol
    k = len(gen.grammar_node.children)
    for i in range(k):
        l = len(gen.grammar_node.children[i].children)
        if gen.grammar_node.children[i].lhs in classes:
            continue # Skip over character classes
        for j in range(l):
            gen_cpy = gen.copy()
            sn_cpy = gen_cpy.grammar_node.children[i].children[j]
            sn_cpy.choice = '%s+' % (sn_cpy.choice)
            grammar_cpy = gen_cpy.generate_grammar()
            print(('Scoring repetition (%d/%d, %d/%d)...' % (i + 1, k, j + 1, l)).ljust(50), end='\r')
            scorer.score(grammar_cpy, gen_cpy)
            new_pos_score = scorer.score_map['pos'][0]
            if new_pos_score > pos_score:
                gen = gen_cpy
                pos_score = new_pos_score
                updated = True
                if pos_score >= 1.0:
                    return gen

    # Return the final grammar
    return gen

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
