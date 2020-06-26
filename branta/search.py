import copy

from branta.oracle import Oracle
from branta.util import strict_subsequences, find_subsequence, new_nonterminal, replace_all
from grammar import Grammar, Rule
from typing import List, Tuple, Set
import sys
from lark import Lark
import random

default_config = {'TERMINALS': 100, 'NONTERMINALS': 100}
POPULATION_SIZE = 20

class Scorer:
    """
    Helper class to score a grammar.
    """
    def __init__(self, positives: List[str], negatives: List[str]):
        self.positives = positives
        self.negatives = negatives

    def score(self, grammar: Grammar):
        """
        Score a grammar based on the number of positive and negative examples it matches. Impose a floor so that this is
        not 0 with no progress if one of the scores is zero
        """
        def parses(grammar, input):
            parser: Lark = grammar.parser()
            try:
                parser.parse(input)
                return True
            except:
                return False

        num_positives_matched = sum([1 for pos in self.positives if parses(grammar, pos)])
        positive_score = max([num_positives_matched / len(self.positives), 0.5/len(self.positives)])
        num_negatives_matched = sum([1 for neg in self.negatives if parses(grammar, neg)])
        negative_score = max([1 - (num_negatives_matched / len(self.negatives)), 0.5/len(self.negatives)])
        return positive_score * negative_score

def score_is_good(score: float):
    """
    Whether or not the score is good enough to stop searching.
    """
    return score >= 1

def init_grammar(guides: List[str]) -> Grammar:
    """
    Makes a naive grammar consisting of leaves for each character from the guides. And the disjunction of all the guides.
    """
    init_grammar = Grammar('t0')
    all_chars = set(['"' + c + '"' for guide in guides for c in guide])
    char_map = {}
    for i, char in enumerate(all_chars):
        idx = i + 1
        init_grammar.add_rule(Rule(f't{idx}').add_body([char]))
        char_map[char] = f't{idx}'

    init_rule = Rule('t0')
    for guide in guides:
        body = []
        for char in guide:
            term = '"' + char + '"'
            body.append(char_map[term])
        init_rule.add_body(body)

    init_grammar.add_rule(init_rule)

    return init_grammar





def mutate_bubble(grammar: Grammar) -> Grammar:
    """
    Bubble up some subsequence of nonterminals
    """

    mutant = grammar.copy()
    sequences : Set[Tuple[str]] = set()
    for rule in mutant.rules.values():
        for body in rule.bodies:
            sequences.update(strict_subsequences(body))
    replace_seq = random.choice(list(sequences))
    replace_name = new_nonterminal(mutant.rules.keys())

    for rule in mutant.rules.values():
        rule.bodies = [replace_all(body, replace_seq, replace_name) for body in rule.bodies]
        rule.cache_valid = False

    mutant.add_rule(Rule(replace_name).add_body(list(replace_seq)))
    return mutant

def mutate_coalesce(grammar: Grammar) -> Grammar:
    """
    Coalesce some elements together.
    """

    mutant = grammar.copy()
    nonterminals = list(mutant.rules.keys())
    terminals = [elem for rule in mutant.rules.values() for body in rule.bodies for elem in body if elem not in nonterminals]
    nonterminals.remove('start')
    print(nonterminals)
    print(terminals)

    all = nonterminals
    coalesce_num = random.choice(range(2,min(6, len(all))))
    to_coalesce = random.sample(all, coalesce_num)

    replacer_id = new_nonterminal(nonterminals)
    for rule in mutant.rules.values():
        # Replace all the things in "to_coalesce" with what we're coalescing
        rule.bodies = [[replacer_id if e in to_coalesce else e for e in body] for body in rule.bodies]
        rule.cache_valid = False

    replacer_rules = []
    for coalescee in to_coalesce:
        if coalescee in mutant.rules:
            rule = mutant.rules.pop(coalescee)
            replacer_rules.extend(rule.bodies)
    replacer = Rule(replacer_id)
    replacer.bodies = replacer_rules
    mutant.add_rule(replacer)

    return mutant

def mutate_alternate(grammar: Grammar) -> Grammar:
    """
    Allow some elements to alternate.
    """
    mutant = grammar.copy()

    nonterminals = list(mutant.rules.keys())
    terminals = [elem for rule in mutant.rules.values() for body in rule.bodies for elem in body if elem not in nonterminals]
    nonterminals.remove('start')
    alternates = terminals + nonterminals

    total_num_rules = len([body for nonterm in nonterminals for body in mutant.rules[nonterm].bodies])
    weights = [len(mutant.rules[nonterm].bodies)/ total_num_rules for nonterm in nonterminals]
    print(weights)

    rule_key = random.choices(nonterminals, weights, k=1)[0]
    body_idx = random.choice(range(len(mutant.rules[rule_key].bodies)))
    alternate_idx = random.choice(range(len(mutant.rules[rule_key].bodies[body_idx])))

    alternates.remove(mutant.rules[rule_key].bodies[body_idx][alternate_idx])
    alternate = random.choice(alternates)

    new_body = mutant.rules[rule_key].bodies[body_idx][:]
    new_body[alternate_idx] = alternate
    mutant.rules[rule_key].add_body(new_body)

    return mutant

def mutate_repeat(grammar: Grammar) -> Grammar:
    """
    Allow some element to repeat
    """
    mutant = grammar.copy()


    nonterminals = list(mutant.rules.keys())
    nonterminals.remove('start')

    total_num_rules = len([body for nonterm in nonterminals for body in mutant.rules[nonterm].bodies])
    weights = [len(mutant.rules[nonterm].bodies)/ total_num_rules for nonterm in nonterminals]
    print(weights)

    rule_key = random.choices(nonterminals, weights, k=1)[0]
    body_idx = random.choice(range(len(mutant.rules[rule_key].bodies)))
    repeat_idx = random.choice(range(len(mutant.rules[rule_key].bodies[body_idx])))

    repeat_elem = mutant.rules[rule_key].bodies[body_idx][repeat_idx]
    repeater_name = new_nonterminal(nonterminals)
    mutant.rules[rule_key].bodies[body_idx][repeat_idx] = repeater_name
    mutant.rules[rule_key].cache_valid = False

    mutant.add_rule(Rule(repeater_name).add_body([repeat_elem]).add_body([repeat_elem, repeater_name]))

    print("Orig: ", grammar)
    print(f"Repeated at key {rule_key}")
    print("New: ", mutant)
    print("--------------")

    return grammar

def minimize(grammar: Grammar) -> None:
    pass

def search(oracle: Oracle, guides: List[str], positives: List[str], negatives: List[str]) -> Grammar:
    """
    Generic search for a grammar that matches the input space of the oracle as much as possible
    """
    print("=====\nBeginning search with guides:\n", guides)
    initial_grammar = init_grammar(guides)
    print(initial_grammar)
    print("====================================")
    cur_gram_id = 0
    scorer = Scorer(positives, negatives)
    minimum_score = scorer.score(initial_grammar)
    population : List[Tuple[Grammar, int, float]] = [(initial_grammar, cur_gram_id, minimum_score)]

    ################### BEGIN HELPERS ######################

    def choose_parent(population: List[Tuple[Grammar, int, float]]):
        """
        Defines heuristics for choosing which grammar to mutate
        """
        return random.choice(population)

    def fuzz_one(parent_grammar: Grammar):
        """
        Do the fuzzing stuff on the current grammar. Assume that this function produces mutants and possibly adds them
        to the population of grammrs
        """
        nonlocal cur_gram_id
        nonlocal minimum_score
        cur_gram_id += 1
        num_mutations = random.choice([1, 2, 4, 8, 16])
        # mutant = parent_grammar
        # for i in range(num_mutations):
        #     mutate_func = random.choice([mutate_bubble, mutate_coalesce, mutate_alternate, mutate_repeat])
        #     mutant = mutate_func(mutant)
        mutant = mutate_repeat(parent_grammar)
        mutant_score = scorer.score(mutant)
        if mutant_score > minimum_score:
            add_to_population(mutant, mutant_score, cur_gram_id)

    def add_to_population(grammar: Grammar, score: float, grammar_id: int):
        """
        Assumes that `population` is sorted from least to most score
        """
        nonlocal minimum_score
        nonlocal population
        assert(score > minimum_score)
        minimize(grammar)

        insert_idx = 0
        # TODO: assert that everything stays sorted
        for elem_grammar, elem_id, elem_score in population:
            # This ensures that older grammars will be popped off before new ones
            if elem_score > score:
                population.insert(insert_idx, (grammar, grammar_id, score))
                break
            insert_idx += 1

        while len(population) > POPULATION_SIZE:
            population.pop(0)

    #################### END HELPERS #######################

    while not score_is_good(minimum_score):
        current_parent, parent_id, score = choose_parent(population)
        fuzz_one(current_parent)
        break











