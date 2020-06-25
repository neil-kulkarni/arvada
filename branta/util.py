import re
from typing import List, Set, Tuple

def strict_subsequences(body: List[str]) -> Set[Tuple[str]]:
    """
    Return strict subsequences of body. Exclude those of length 1.
    >>> strict_subsequences(["a", "b", "c"])
    {('a', 'b'), ('b', 'c')}
    >>> strict_subsequences(["a", "b"])
    set()
    >>> strict_subsequences(["a", "b", "c", "d"])
    {('a', 'b'), ('a', 'b', 'c'), ('b', 'c'), ('b', 'c', 'd'), ('c', 'd')}
    >>> strict_subsequences(["a", "b", "a", "b"])
    {('a', 'b'), ('a', 'b', 'a'), ('b', 'a'), ('b', 'a', 'b')}
    """
    subseqs = set(tuple())
    for startpos in range(0, len(body) - 1):
        for endpos in range(startpos + 2, min(len(body) + 1, startpos + len(body))):
            assert (len(body[startpos:endpos]) > 1)
            subseqs.add(tuple(body[startpos:endpos]))
    return subseqs


def find_subsequence(seq: List[str], subseq: List[str]) -> int:
    """
    Returns the position of subseq in seq, or -1 if it does not appear
    >>> find_subsequence(["a", "b", "c"], ["a", "b"])
    0
    >>> find_subsequence(["a", "b", "c"], ["b", "b"])
    -1
    >>> find_subsequence(["a", "b", "c"], ["b", "c"])
    1
    >>> find_subsequence(["a", "b", "a", "b"], ["a", "b"])
    0
    >>> find_subsequence(["t0", "a", "b"], ["a", "b"])
    1
    >>> find_subsequence(["a", "b", "c", "d"], ["b", "c", "d"])
    1
    """
    if len(subseq) > len(seq):
        return -1
    match_idx = 0
    match_start = -1
    for seq_idx in range(0, len(seq)):
        if len(subseq) > (len(seq) - match_start):
            return -1
        if seq[seq_idx] == subseq[match_idx]:
            if match_idx == 0:
                match_start = seq_idx
            elif match_idx == len(subseq) - 1:
                # We matched all the characters
                return match_start
            match_idx += 1
        else:
            match_start = -1
            match_idx = 0
    return match_start


def new_nonterminal(nonterminals: List[str]):
    """
    Return a fresh nonterminal t{idx} that is not equal to any element of nonterminals
    >>> new_nonterminal(["t0", "t1", "t2", "t4"])
    't5'
    >>> new_nonterminal(["t0", "t1", "t2"])
    't3'
    >>> new_nonterminal(["start", "t0", "t1", "t2"])
    't3'
    """
    term_re = re.compile("t([0-9]+)")
    max_id = -1
    for nonterminal in nonterminals:
        match = term_re.match(nonterminal)
        if (match):
            nonterm_id = int(match.group(1))
            max_id = max(max_id, nonterm_id)

    return f't{max_id + 1}'

def replace_all(body: List[str], replace_seq: List[str], replace_name: str):
    """
    Returns a copy of `body` with all ocurrences of `replace_seq` replaced with "replace_name"
    >>> replace_all(["a", "b", "c", "d"], ["b", "c", "d"], "t0")
    ['a', 't0']
    >>> replace_all(["a", "b", "a", "b"], ["a", "b"], "t1")
    ['t1', 't1']
    >>> replace_all(["a", "b", "c", "d"], ["a", "b"], "t0")
    ['t0', 'c', 'd']
    >>> replace_all(["a", "b", "c"], ["b", "b"], "t1")
    ['a', 'b', 'c']
    """
    replace_pos = find_subsequence(body, replace_seq)
    new_body = body[:]
    while (replace_pos != -1):
        new_body = new_body[:replace_pos] + [replace_name] + new_body[replace_pos + len(replace_seq):]
        replace_pos = find_subsequence(new_body, replace_seq)
    return new_body