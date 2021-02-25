# Lark Examples

A bunch of examples written in the lark grammar format. Ideas pulled from various other papers which I have listed here as much as possible. 


## Ours:
- while: a simple while grammar
- arith: a calculator language that doesn't permit leading zeroes
- turtle: LOGO-like DSL for python's turtle, as in [Lark](https://github.com/lark-parser/lark/blob/master/examples/turtle_dsl.py)
- html: a subset of html

## From mimid (Andreas Zeller work)

- calc: basic calculator, no whitespace allowed, permissive on the zeroes
- mathexpr: inspired from [this repo](https://github.com/louisfisch/mathematical-expressions-parser/blob/master/eval.py)
- netrc: inspired from the spec [here](https://www.ibm.com/support/knowledgecenter/en/ssw_aix_72/filesreference/netrc.html), minus `macdef`, because frankly, that's boring and requires me specifying too many characters(it's just `macdef [your code here] NEWLINE`). Also, it's order-dependent when it shouldn't be right now, (e.g. should be able to intersperse `login` and `password`)
- json_full: as defined [here](https://www.json.org/json-en.html). 
- json: simplified version without escapable characters/special characters

## From GLADE/REINAM
- url
- fol
- csv
- grep
- ip
- xml: example with 5 allowed tags (ours, recreated as per descriptions)
- lisp: inspired by [this one](https://iamwilhelm.github.io/bnf-examples/lisp)

