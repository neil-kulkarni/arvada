# Lark Examples

This directory contains the grammars for the first 8 (``perfect'') benchmarks from the evaluation of Arvada in:
> Neil Kulkarni*, Caroline Lemieux*, and Koushik Sen. 2021. Learning Highly Recursive Grammars. In Proceedings of the 36th ACM/IEEE International Conference on Automated Software Engineering (ASE'21).

The grammars in this directory are written in [lark](https://github.com/lark-parser/lark) format, and an interactive parsing session can be started by running
```
$ python3 -i test_lark.py <grammar_name>
```
for instance, one can observe what inputs are accepted by the first-order-logic grammar fol.py:
```
$ python3 -i test_lark.py fol.py
>>> parser('Forall(?x) ?x = ?y')
```

The oracles for these grammars used in the evaluation are derived from conversions of these lark grammars into ANTLR4 format; refer to our evaluation artifact for those oracles:
```
$ docker pull carolemieux/arvada-artifact:latest
```  

## Description of grammars

While the choice of benchmark grammars was inspired by prior work [1] [2] [3], we could not always get the exact grammars used in prior work, or they could not be turned into parsers by either lark or ANTLR4 (due to the presence of left-recursion). 

- arith: a simple grammar of parenthesized arithmetic operations. 
- fol: the use of a first-order-logic grammar was inspired by Reinam [2], but the version used here is adapted from an ANTLR4 grammar. 
- json: inspired by the Mimid paper [3], this grammar is a simplified version of the json grammar described by [json.org](https://www.json.org/json-en.html). It is simplified in that it does not contain escapable or special characters. 
- lisp: this grammar was derived from the lisp expression grammar found on the [internet](https://web.archive.org/web/20200927090549/https://iamwilhelm.github.io/bnf-examples/lisp). It is quite permissive and simple. Orignally we tried to get the Lisp benchmark used in Reinam [2], but this was only available in non-human-readable binary format.
- mathexpr: used in the Mimid paper [3], this version grammar comes from a [mathmatical expressions parser](https://github.com/louisfisch/mathematical-expressions-parser) written in Python. It has been re-written to remove left-recursion so it can be compiled by ANTLR. 
- turtle: this is a small DSL taken from examples for the [lark parser](https://github.com/lark-parser/lark/blob/master/examples/turtle_dsl.py). 
- while: this is an entirely handwritten toy grammar, inspired by the `while` grammars discussed in many introductory programming languages classes.
- xml: this covers a subset of XML, allowing only for a limited number of tags, but arbitrary attributes and text within nodes. Orignally we tried to get the XML benchmark used in Reinam [2], but this was only available in non-human-readable binary format.

[1] O. Bastani, R. Sharma, A. Aiken, and P. Liang, “Synthesizing Program Input Grammars,” in Proceedings of the 38th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2017,(New York, NY, USA), p. 95–110, Association for Computing Machinery, 2017.
[2] Z. Wu, E. Johnson, W. Yang, O. Bastani, D. Song, J. Peng, and T. Xie, “REINAM: Reinforcement Learning for Input-Grammar Inference,” in Proceedings of the 2019 27th ACM Joint Meeting on European Software Engineering Conference and Symposium on the Foundations of Software Engineering, ESEC/FSE 2019, (New York, NY, USA), p. 488–498, Association for Computing Machinery, 2019
[3]  R. Gopinath, B. Mathis, and A. Zeller, “Mining Input Grammars from Dynamic Control Flow,” in Proceedings of the 2019 28th ACM Joint Meeting on European Software Engineering Conference and Symposium on the Foundations of Software Engineering, ESEC/FSE 2020, (New York, NY, USA), pp. 1–12, Association for Computing Machinery, 2020.
