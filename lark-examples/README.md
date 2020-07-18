# Lark Examples

A bunch of examples written in the lark grammar format. Ideas pulled from various other papers which I have listed here as much as possible. 


## From mimid (Andreas Zeller work)

- calc: basic calculator, no whitespace allowed, permissive on the zeroes
- mathexpr: inspired from [this repo](https://github.com/louisfisch/mathematical-expressions-parser/blob/master/eval.py)
- netrc: inspired from the spec [here](https://www.ibm.com/support/knowledgecenter/en/ssw_aix_72/filesreference/netrc.html), minus `macdef`, because frankly, that's boring and requires me specifying too many characters(it's just `macdef [your code here] NEWLINE`). Also, it's order-dependent when it shouldn't be right now, (e.g. should be able to intersperse `login` and `password`)
- json: as defined [here](https://www.json.org/json-en.html). Again, I haven't enumerated all possible characters, so idk. 