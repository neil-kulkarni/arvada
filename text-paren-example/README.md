The ground truth grammar in this example is the following:
```
S -> E
E -> p E p | E o E | n
```
Since this grammar consists solely of lowercase characters, Arvada will fail to learn it if run pretokenization. Add the --no-pretokenize flag to learn the ground truth grammar.

First, test that the oracle program runs without error on the training examples:
```
$ text-paren-example/parser.py text-paren-example/train_set/guide-0.ex
```
(you may have to `pip install lark-parser`). If it exits silently with return code 0, everything is ok!

Then, compare the results of
```
$ python3 search.py external --no-pretokenize text-paren-example/parser.py text-paren-example/train_set p-nopretok.log
$ python3 eval.py external text-paren-example/parser.py text-paren-example/test_set p-noprentok.log
```
and
```
$ python3 search.py external text-paren-example/parser.py text-paren-example/train_set p-pretok.log
$ python3 eval.py external text-paren-example/parser.py text-paren-example/test_set p-pretok.log
```
The `--no-pretokenize` case should generalize properly on some runs, while the other case should have zero recall. 
