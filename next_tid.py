
# Globally unique nonterminal number
next_tid = 1


def allocate_tid():
    """
    Returns a new, unique nonterminal name.
    """
    global next_tid
    nt_name = 't%d' % (next_tid)
    next_tid += 1
    return nt_name


