from typing import List
import re

def lark_file_to_antlr_test(filename: str):
    import os
    gram_name = "g_" + os.path.splitext(os.path.basename(filename))[0]
    lines = open(filename).readlines()
    lines = [line.rstrip() for line in lines]
    antlr_lines = lark_to_antlr(gram_name, lines)
    for line in antlr_lines:
        print(line)


def lark_to_antlr(gram_name: str, gram_contents: List[str]) -> List[str]:
    """
    Converts the contents of a grammar written for Lark into ANTLR4 format.
    ASSUMES: gram_contents has been stripped of newlines.
    """
    antlr_lines = [f"grammar {gram_name};"]

    start_rule = re.compile("^start\s*:.*")
    other_rule = re.compile("^[a-zA-Z]+\s*:.*")
    rule_cont = re.compile("^\s*\|.*")
    blank_line = re.compile("^\s*$")
    comment_line = re.compile("^\s*//.*")
    import_line = re.compile("^\s*%.*")

    idx = len(antlr_lines)
    last_rule_line = -1
    last_rule_was_start = False
    last_start_line = -1
    for line in gram_contents:
        line = line.replace("\"", "'")
        start_m = start_rule.search(line)
        other_m = other_rule.search(line)
        cont_m = rule_cont.search(line)
        blank_m = blank_line.search(line)
        comment_m = comment_line.search(line)
        import_m = import_line.search(line)
        if start_m is not None:
            if last_rule_line > 0:
                antlr_lines[last_rule_line] += ";"
            antlr_lines.append(line)
            last_rule_was_start = True
            last_start_line = idx
        elif other_m is not None:
            if last_rule_was_start:
                antlr_lines[last_start_line] += " EOF;"
                last_rule_was_start = False
            elif last_rule_line > 0:
                antlr_lines[last_rule_line] += ";"
                pass
            antlr_lines.append(line)
            last_rule_line = idx
        elif cont_m is not None:
            if last_rule_was_start:
                last_start_line = idx
            else:
                last_rule_line = idx
            antlr_lines.append(line)
        elif blank_m is not None:
            antlr_lines.append(line)
        elif comment_m is not None:
            pass
        elif import_m is not None:
            pass
        else:
            raise NotImplementedError(f"I don't know how to process the line: {line}")
        idx += 1

    if last_rule_line == idx -1:
        antlr_lines[last_rule_line] += ";"
    if last_start_line == idx -1:
        antlr_lines[last_start_line] += " EOF;"

    return antlr_lines


