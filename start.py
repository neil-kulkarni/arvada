from parse_tree import ParseNode
from generator import *
from graph import Graph
from union import UnionFind
from score import Scorer

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
    trees, classes = build_trees(oracle, config, leaves)
    print('Building initial grammar...'.ljust(50), end='\r')
    grammar = build_grammar(config, trees)
    print('Coalescing nonterminals...'.ljust(50), end='\r')
    grammar = coalesce(oracle, config, trees, grammar)
    print('Minimizing and converting...'.ljust(50), end='\r')
    grammar = minimize(config, grammar)
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

def group(trees):
    """
    TREES is composed of half-built ParseTrees. Each of the intermediate
    ParseTrees are represented as a list of nodes at the top-most layer.

    Given a list of TREES, computes and returns a map of the most common
    payloads in the ParseNodes. These payloads can be either terminals or
    nonterminals, both are treated the same. Each returned map entry is given a
    unique identifier ti for some i > 1, reserving i = 0 for the start node.

    Trivial groups are filtered out, including groups that only appear once,
    groups that only consist of one token, and groups that are substrings of
    other groups.

    Returns the group first sorted by frequency so that most frequently occuring
    substrings come first, then sorted by length, so that longer substrings are
    preferred, like in the maximal-munch rule.
    """
    def is_substr(counts, candidate):
        """
        Checks whether candidate is a substring of any string key in the count
        dictionary, and returns True if so.
        """
        for key_str in counts:
            if candidate != key_str and candidate in key_str:
                return True
        return False

    # Compute a map of substrings to their frequency of occurence over all trees
    counts = {}
    for tree_lst in trees:
        for i in range(len(tree_lst)):
            for j in range(i + 1, len(tree_lst) + 1):
                tree_sublist = tree_lst[i:j]
                tree_substr = ''.join([t.payload for t in tree_sublist])
                if tree_substr in counts:
                    count, sublist, id = counts[tree_substr]
                    counts[tree_substr] = (count + 1, sublist, id)
                else:
                    counts[tree_substr] = (1, tree_sublist, allocate_tid())

    # Filter out tokens that only appear once and nonterminals that are composed
    # of only a single token. Filter out keys that are substrings of other keys.
    counts = {k:v for k, v in counts.items() if v[0] > 1 and len(v[1]) > 1}
    counts = {k:v for k, v in counts.items() if not is_substr(counts, k)}

    # Sort first by frequency, then by key-length
    counts = counts.items()
    counts = sorted(counts, key=lambda elem: len(elem[1][1]), reverse=True)
    counts = sorted(counts, key=lambda elem: elem[1][0], reverse=True)
    return counts

def apply(grouping, trees):
    """
    The GROUPING of the TREES is an implicit map of a list of tokens to the
    frequency at which the list occurs in the top layer of TREES, with most
    frequent token appearing first.

    TREES is composed of half-built ParseTrees. Each of the intermediate
    ParseTrees are represented as a list of nodes at the top-most layer. This
    algorithm applies GROUPING to the topmost layer of each tree to progress
    in building the tree. This algorithm should be repeatedly called until
    the tree is fully built.

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
    def matches(grouping, layer):
        """
        LAYER is the top layer of one half-built ParseTree.

        The GROUPING of the TREES is an implicit map of a list of tokens to the
        frequency at which the list occurs in the top layer of TREES, with most
        frequent token appearing first. Requires len(grouping) > 0.

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

    def apply_single(group_lst, tree_lst):
        """
        Applies the grouping GROUP_LST to a single tree. For each grouping,
        processed in order, applies that grouping to TREE_LST as many times
        as possible.

        Returns the updated TREE_LST. If no groupings can be found, do nothing.
        """
        if len(group_lst) == 0:
            return tree_lst

        for group_str, tup in grouping:
            count, group_lst, id = tup
            ng = len(group_lst)
            ind = matches(group_lst, tree_lst)
            while ind != -1:
                parent = ParseNode(id, False, tree_lst[ind : ind + ng])
                tree_lst[ind : ind + ng] = [parent]
                ind = matches(group_lst, tree_lst)

        return tree_lst

    return [apply_single(grouping, tree) for tree in trees]

def build_trees(oracle, config, leaves):
    """
    ORACLE is a Lark parser for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    CONFIG is the required configuration options for GrammarGenerator classes.

    LEAVES should be a list of lists (one list for each input example), where
    each sublist contains the tokens that built that example, as ParseNodes.

    Iteratively builds parse trees from each of the examples and returns a list
    of ParseNode references. Also returns the character classes for use in future
    stages of the algorithm.

    Algorithm:
        1. Initialization
            - S <- preprocessed input examples
            - G <- group(S)
        2. while grouping G is not empty:
            a. Build new ParseNodes from S
            b. S <- set of ParseNodes
            c. G <- group(S)
        3. Add a start nonterminal to each ParseNode
        4. return the set of finished starts
    """
    layers, classes = derive_classes(oracle, config, leaves)
    grouping = group(layers)

    while len(grouping) > 0:
        layers = apply(grouping, layers)
        grouping = group(layers)

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

def coalesce(oracle, config, trees, grammar):
    """
    ORACLE is a Lark parser for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    CONFIG is the required configuration options for GrammarGenerator classes.

    TREES is a list of fully constructed parse trees.

    GRAMMAR is a GrammarNode that is the disjunction of the TREES.

    This method coalesces nonterminals that are equivalent to each other.
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

    for i in range(len(nonterminals)):
        for j in range(i + 1, len(nonterminals)):
            # Iterate through each unique pair of nonterminals
            print(('Nonterminal replacement (%d, %d, %d)...' % (i + 1, j + 1, len(nonterminals))).ljust(50), end='\r')
            first, second = nonterminals[i], nonterminals[j]

            # If the nonterminals can replace each other in every context, they
            # must belong to the same character class
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
    # Create a unique set of rules represented as a map
    grammar_map = {}
    for rule in grammar.children:
        if rule.lhs not in grammar_map:
            grammar_map[rule.lhs] = ([], [])
        rule_str = ''.join([sn.choice for sn in rule.children])
        if rule_str not in grammar_map[rule.lhs][1]:
            rules, rule_strings = grammar_map[rule.lhs]
            rules.append(rule)
            rule_strings.append(rule_str)

    # Turn the unique set of rules into a new GrammarNode object
    new_grammar = GrammarNode(config, START, [])
    for rule_start in grammar_map:
        rules, _ = grammar_map[rule_start]
        for rule in rules:
            new_grammar.children.append(rule)
    grammar = new_grammar

    # Finds the set of nonterminals that expand directly to a single terminal
    # Let the keys of X be the set of these nonterminals, and the corresponding
    # values be the the strings derivable from those nonterminals
    X, updated = {}, True # updated determines the stopping condition

    while updated:
        updated = False
        for rule_start in grammar_map:
            rules, _ = grammar_map[rule_start]
            if len(rules) == 1 and len(rules[0].children) == 1 and (rules[0].children[0].is_terminal or rules[0].children[0].choice in X):
                rule = next(iter(rules))
                if rule.lhs not in X:
                    X[rule.lhs] = [X[sn.choice][0] if sn.choice in X else sn.choice for sn in rule.children]
                    updated = True

    # Update the set X so that the strings derivable from it are lists of
    # SymbolNodes instead of lists of strings
    for k in X: X[k] = [SymbolNode(config, s, True) for s in X[k]]

    # Iterate through the grammar, and mutate any rules that use a nonterminal
    # in X to contain the set of terminals instead
    for rule_node in grammar.children:
        to_fix = [sn.choice in X for sn in rule_node.children]
        while any(to_fix):
            ind = to_fix.index(True)
            nt = rule_node.children[ind]
            rule_node.children[ind:ind+1] = X[nt.choice]
            to_fix = [sn.choice in X for sn in rule_node.children]

    # Now, remove all the rules that defined nonterminals in X
    grammar.children = [rule for rule in grammar.children if rule.lhs not in X or rule.lhs == START]
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
