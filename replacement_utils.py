from parse_tree import ParseNode

def fixup_terminal(payload):
    if len(payload) >= 3 and payload.startswith('"') and payload.endswith('"'):
        payload = payload[1:-1]
    return payload


def get_all_replacement_strings(tree: ParseNode, nt_to_replace: str):
    """
    Get all the possible replacement strings
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
        replacement_strings.append('[[:REPLACEME]]')

    strings_per_child = [get_all_replacement_strings(c, nt_to_replace) for c in tree.children]
    string_prefixes = ['']
    for strings_for_child in strings_per_child:
        string_prefixes =[prefix + string_for_child for prefix in string_prefixes for string_for_child in strings_for_child]
    replacement_strings.extend(string_prefixes)

    return list(set(replacement_strings))


if __name__ == "__main__":
    import doctest
    doctest.testmod()