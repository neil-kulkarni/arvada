import copy
from collections import defaultdict, Counter

from branta.oracle import Oracle
from branta.util import strict_subsequences, find_subsequence, new_nonterminal, replace_all
from grammar import Grammar, Rule
from typing import List, Tuple, Set, Dict
import sys
from lark import Lark
import random
import curses

random.seed(0)

class Scorer:
    """
    Helper class to score a grammar.
    """
    def __init__(self, positives: List[str], negatives: List[str]):
        self.positives = positives
        self.negatives = negatives

    def score(self, grammar: Grammar, progress = None):
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

        num_positives_matched = 0
        j = 1
        for pos in self.positives:
            if parses(grammar, pos):
                num_positives_matched += 1
            if progress is not None:
                progress(j,0)
            j += 1

        positive_score = max([num_positives_matched / len(self.positives), 0.5/len(self.positives)])
        num_negatives_matched = 0
        k = 1
        for neg in self.negatives:
            if parses(grammar, pos):
                num_negatives_matched += 1
            if progress is not None:
                progress(j,k)
            k += 1
        negative_score = max([1 - (num_negatives_matched / len(self.negatives)), 0.5/len(self.negatives)])
        return positive_score * negative_score

class Searcher:
    default_config = {'TERMINALS': 100, 'NONTERMINALS': 100}
    POPULATION_SIZE = 20

    def __init__(self, stdscr):
        self.cur_parent = 0
        self.window = stdscr
        self.population = []
        self.action = "Initializing"
        self.cur_grammar : Grammar= None

    def log_debug(self, *args):
        if self.window is None:
            print(*args)

    def write_current_grammar(self):
        f = open(".cur_grammar", "w")
        f.write(self.cur_grammar.__str__())
        f.close()

    def print_status(self):
        if self.window is not None:
            self.window.clear()
            self.window.addstr(0,0, f"Current population size: {len(self.population)}")
            self.window.addstr(1,0, f"Current parent under mutation: {self.cur_parent}")
            self.window.addstr(2,0, f"Current best score: {self.population[-1][2]}")
            self.window.addstr(3,0, "Current action:")
            self.window.addstr(4,4, self.action)
            self.window.refresh()

    def progress(self, num_positives_parsed, num_negatives_parsed):
        self.action = f"Scoring...\n   {num_positives_parsed} positives done\n   {num_negatives_parsed} negatives done"
        self.print_status()

    def score_is_good(self, score: float):
        """
        Whether or not the score is good enough to stop searching.
        """
        return score >= 1

    def init_grammar(self, guides: List[str]) -> Grammar:
        """
        Makes a naive grammar consisting of leaves for each character from the guides. And the disjunction of all the guides.
        """
        init_grammar = Grammar('t0')
        all_chars = set(['"' + c + '"' for guide in guides for c in guide])
        char_map = {}
        for i, char in enumerate(all_chars):
            idx = i + 1
            #init_grammar.add_rule(Rule(f't{idx}').add_body([char]))
            char_map[char] = f't{idx}'

        init_rule = Rule('t0')
        for guide in guides:
            body = []
            for char in guide:
                term = '"' + char + '"'
                body.append(term)
            init_rule.add_body(body)

        init_grammar.add_rule(init_rule)

        return init_grammar

    def mutate_bubble(self, grammar: Grammar) -> Grammar:
        """
        Bubble up some subsequence of nonterminals/terminals
        """

        self.log_debug("===BUBBLE===")
        mutant = Grammar(grammar.rules['start'].bodies[0][0])
        sequences : Set[Tuple[str]] = set()
        for rule in grammar.rules.values():
            for body in rule.bodies:
                sequences.update(strict_subsequences(body))
        if len(sequences) == 0:
            for rule in grammar.rules.values():
                rule_bodies = rule.bodies
                new_rule = Rule(rule.start)
                for body in rule_bodies:
                    new_rule.add_body(body[:])
                mutant.add_rule(new_rule)
            return mutant

        replace_seq = random.choice(list(sequences))
        replace_name = new_nonterminal(grammar.rules.keys())

        for rule in grammar.rules.values():
            rule_bodies = [replace_all(body[:], replace_seq, replace_name) for body in rule.bodies]
            new_rule = Rule(rule.start)
            for body in rule_bodies:
                new_rule.add_body(body)
            mutant.add_rule(new_rule)

        mutant.add_rule(Rule(replace_name).add_body(list(replace_seq)))
        self.log_debug(f"Bubbled up {replace_name}->{replace_seq}")
        self.log_debug("keys before: ", list(grammar.rules.keys()))
        self.log_debug("keys after: ", list(mutant.rules.keys()))
        return mutant

    def mutate_coalesce(self, grammar: Grammar) -> Grammar:
        """
        Coalesce some elements together.
        """

        self.log_debug("===COALESCE===")
        mutant = Grammar(grammar.rules['start'].bodies[0][0])

        nonterminals = list(grammar.rules.keys())
        terminals = list(set([elem for rule in grammar.rules.values() for body in rule.bodies for elem in body if elem not in nonterminals]))
        nonterminals.remove('start')

        all = nonterminals + terminals
        coalesce_num = random.choice(range(2, min(6, len(all))))
        to_coalesce = random.sample(all, coalesce_num)

        replacer_id = new_nonterminal(nonterminals)
        for rule in grammar.rules.values():
            # Replace all the things in "to_coalesce" with what we're coalescing
            rule_bodies = [[replacer_id if e in to_coalesce else e for e in body] for body in rule.bodies]
            new_rule = Rule(rule.start)
            for body in rule_bodies:
                new_rule.add_body(body)
            mutant.add_rule(new_rule)

        replacer_rules = []
        for coalescee in to_coalesce:
            if coalescee in grammar.rules:
                rule = grammar.rules[coalescee]
                for body in rule.bodies:
                    replacer_rules.append(body[:])
            else:
                # otherwise it's a terminal
                replacer_rules.append([coalescee])

        replacer = Rule(replacer_id)
        replacer.bodies = replacer_rules
        mutant.add_rule(replacer)
        self.log_debug(f"Coalesced up {to_coalesce}->{replacer_id}")
        self.log_debug(mutant)

        return mutant

    def mutate_alternate(self, grammar: Grammar) -> Grammar:
        """
        Allow some elements to alternate.
        """
        mutant = Grammar(grammar.rules['start'].bodies[0][0])
        self.log_debug("===ALTERNATE===")
        self.log_debug(list(grammar.rules.keys()))

        nonterminals = list(grammar.rules.keys())
        terminals = [elem for rule in grammar.rules.values() for body in rule.bodies for elem in body if elem not in nonterminals]
        nonterminals.remove('start')
        alternates = terminals + nonterminals

        total_num_rules = len([body for nonterm in nonterminals for body in grammar.rules[nonterm].bodies])
        weights = [len(grammar.rules[nonterm].bodies)/ total_num_rules for nonterm in nonterminals]

        rule_key = random.choices(nonterminals, weights, k=1)[0]
        body_idx = random.choice(range(len(grammar.rules[rule_key].bodies)))
        alternate_idx = random.choice(range(len(grammar.rules[rule_key].bodies[body_idx])))

        alternates.remove(grammar.rules[rule_key].bodies[body_idx][alternate_idx])
        alternate = random.choice(alternates)

        for rule in grammar.rules.values():
            new_rule = Rule(rule.start)
            for body in rule.bodies:
                new_rule.add_body(body)
            if rule.start == rule_key:
                new_body = grammar.rules[rule_key].bodies[body_idx][:]
                new_body[alternate_idx] = alternate
                new_rule.add_body(new_body)
            mutant.add_rule(new_rule)

        self.log_debug("keys before: ", nonterminals)
        self.log_debug("keys after: ", list(mutant.rules.keys()))

        self.log_debug(f"Alternated at {rule_key}->{mutant.rules[rule_key].bodies[body_idx][alternate_idx]}|{alternate}")
        return mutant

    def mutate_repeat(self, grammar: Grammar) -> Grammar:
        """
        Allow some element to repeat
        """
        mutant = Grammar(grammar.rules['start'].bodies[0][0])
        self.log_debug("===REPEAT===")

        nonterminals = list(grammar.rules.keys())
        nonterminals.remove('start')

        total_num_rules = len([body for nonterm in nonterminals for body in grammar.rules[nonterm].bodies])
        weights = [len(grammar.rules[nonterm].bodies)/ total_num_rules for nonterm in nonterminals]

        rule_key = random.choices(nonterminals, weights, k=1)[0]
        body_idx = random.choice(range(len(grammar.rules[rule_key].bodies)))
        repeat_idx = random.choice(range(len(grammar.rules[rule_key].bodies[body_idx])))

        repeat_elem = grammar.rules[rule_key].bodies[body_idx][repeat_idx]
        repeater_name = new_nonterminal(nonterminals)

        self.log_debug(f"In rule {rule_key} -> {grammar.rules[rule_key].bodies[body_idx]} repeating {repeat_elem} into {repeater_name}")
        for rule in grammar.rules.values():
            new_rule = Rule(rule.start)
            if rule.start == rule_key:
                for i in range(len(rule.bodies)):
                    if i == body_idx:
                        bod = rule.bodies[i]
                        new_rule.add_body(bod[:repeat_idx] + [repeater_name] + bod[repeat_idx+1:])
                    else:
                        new_rule.add_body(rule.bodies[i][:])
            else:
                for body in rule.bodies:
                    new_rule.add_body(body[:])
            mutant.add_rule(new_rule)

        mutant.add_rule(Rule(repeater_name).add_body([repeat_elem]).add_body([repeat_elem, repeater_name]))

        return mutant

    def minimize(self, grammar: Grammar) -> None:
        """
        'Minimize' a grammar. Taken straight out of mimid paper.
        This is a mutative function.
        """
        self.action = "Minimizing"
        orig_size : int = self.grammar_size(grammar)
        def remove_single_keys(grammar: Grammar):
            rule_starts_to_remove: List[str] = []
            for rule_start, rule in grammar.rules.items():
                if rule_start == "start":
                    continue
                if (len(rule.bodies) == 1):
                    if len(rule.bodies[0]) == 1:
                        rule_starts_to_remove.append(rule_start)

            for replacee in rule_starts_to_remove:
                replacer = grammar.rules[replacee].bodies[0]
                for rule_start, rule in grammar.rules.items():
                    rule.bodies = [[replacer if e == replacee else e for e in body] for body in rule.bodies]
                    rule.cache_valid = False
                    rule.cached_str = ""
                grammar.rules.pop(replacee)
            grammar.cached_str_valid = False
            grammar.cached_parser_valid = False

        def remove_redundant_nonterminals(grammar: Grammar):
            rules_map : Dict[Tuple[Tuple[str]], List[str]]= defaultdict(list)
            for rule in grammar.rules.values():
                if rule.start == "start":
                    continue
                sorted_bodies : List[Tuple[str]] = [tuple(body) for body in rule.bodies]
                self.log_debug(sorted_bodies)
                sorted_bodies.sort()
                tuple_bodies : Tuple[Tuple[str]] = tuple(sorted_bodies)
                rules_map[tuple_bodies].append(rule.start)
            for mergeables in rules_map.values():
                if len(mergeables) > 1:
                    replacer = mergeables[0]
                    replacees = mergeables[1:]
                    for replacee in replacees:
                        for rule_start, rule in grammar.rules.items():
                            rule.bodies = [[replacer if e == replacee else e for e in body] for body in rule.bodies]
                            rule.cache_valid = False
                            rule.cached_str = ""
                        grammar.rules.pop(replacee)
            grammar.cached_str_valid = False
            grammar.cached_parser_valid = False

        def remove_straight_recursion(grammar: Grammar):
            remove_rules = []
            for rule_start, rule in grammar.rules.items():
                to_remove : List[int] = []
                if rule_start == "start":
                    continue
                for body_idx, body in enumerate(rule.bodies):
                    if len(body) == 1 and body[0] == rule_start:
                        to_remove.append(body_idx)
                for idx in reversed(to_remove):
                    rule.bodies.pop(idx)
                assert(len(rule.bodies) > 0)
                rule.cache_valid = False
                rule.cached_str = ""


            grammar.cached_str_valid = False
            grammar.cached_parser_valid = False

        def remove_single_references(grammar: Grammar):
            single_refs = {}
            counter = Counter([e for rule in grammar.rules.values() for body in rule.bodies for e in body])
            for elem in counter:
                if elem in grammar.rules:
                    if counter[elem] == 1:
                        if len(grammar.rules[elem].bodies) == 1:
                            single_refs[elem] = grammar.rules[elem].bodies[0]

            for rule in grammar.rules.values():
                new_bodies = []
                for body in rule.bodies:
                    new_body = []
                    for e in body:
                        if e in single_refs:
                            new_body.extend(single_refs[e])
                        else:
                            new_body.append(e)
                    new_bodies.append(new_body)
                rule.bodies = new_bodies
                rule.cache_valid = False
                rule.cached_str = ""

            for ref in single_refs:
                grammar.rules.pop(ref)

            grammar.cached_str_valid = False
            grammar.cached_parser_valid = False

        remove_single_keys(grammar)
        remove_redundant_nonterminals(grammar)
        remove_straight_recursion(grammar)
        remove_single_references(grammar)
        new_size : int = self.grammar_size(grammar)
        while (new_size < orig_size):
            orig_size = new_size
            remove_single_keys(grammar)
            remove_redundant_nonterminals(grammar)
            remove_straight_recursion(grammar)
            remove_single_references(grammar)
            new_size: int = self.grammar_size(grammar)

    def grammar_size(self, grammar: Grammar) -> int:
        return sum([1 for rule in grammar.rules.values() for body in rule.bodies])

    def search(self, oracle: Oracle, guides: List[str], positives: List[str], negatives: List[str]) -> Grammar:
        """
        Generic search for a grammar that matches the input space of the oracle as much as possible
        """
        #print("=====\nBeginning search with guides:\n", guides)
        initial_grammar = self.init_grammar(guides)
       # print(initial_grammar)
        #print("====================================")
        cur_gram_id = 0
        scorer = Scorer(positives, negatives)
        minimum_score = scorer.score(initial_grammar)
        self.population = [(initial_grammar, cur_gram_id, minimum_score)]

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
            mutant = parent_grammar
            self.action = "Mutating"
            for i in range(num_mutations):
                parent_grammar.cached_str_valid = False
                # print("At topmost of iteration: ", mutant.rules.keys())
                mutate_func = random.choice([self.mutate_bubble, self.mutate_coalesce])#, self.mutate_alternate, self.mutate_repeat])
                mutant = mutate_func(mutant)
                self.log_debug("====== gram:\n", mutant, "\n============")

                for rule in mutant.rules.values():
                    rule.cache_valid = False
                mutant.cached_str_valid = False



                #print("score is ", scorer.score(mutant))

                # print("At bottom of iteration: ", mutant.rules.keys())

            self.cur_grammar = mutant
            self.write_current_grammar()
            self.action = "Scoring"
            #print("!!!!!done@!!!!!")
            self.minimize(mutant)
            mutant_score = scorer.score(mutant, self.progress)
            if mutant_score > minimum_score:
                add_to_population(mutant, mutant_score, cur_gram_id)

        def add_to_population(grammar: Grammar, score: float, grammar_id: int):
            """
            Assumes that `population` is sorted from least to most score
            """
            self.action = "Saving"
            nonlocal minimum_score
            assert(score > minimum_score)

            insert_idx = 0
            # TODO: assert that everything stays sorted
            for elem_grammar, elem_id, elem_score in self.population:
                # This ensures that older grammars will be popped off before new ones
                #print(elem_score)
                if elem_score > score:
                    break
                insert_idx += 1
            self.population.insert(insert_idx, (grammar, grammar_id, score))
            #print("[POP] is of size", len(population))

            while len(self.population) > self.POPULATION_SIZE:
                self.population.pop(0)
            #print("[POP] is of size", len(population))
            minimum_score = self.population[0][2]
            self.action = "Done Saving"

        #################### END HELPERS #######################

        for i in range(0, 100):
            current_parent, parent_id, score = choose_parent(self.population)
            self.cur_parent = parent_id
            fuzz_one(current_parent)
            self.print_status()
            #print(f"Current best score: {self.population[-1][2]}")

        #print(f"Current best score: {self.population[-1][2]}")











