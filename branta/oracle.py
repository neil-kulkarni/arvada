from grammar import Grammar
import subprocess
import tempfile

class Oracle:
    """
    Abstract Oracle class, used to check whether an input is in the language
    described by the oracle.
    """
    def check(self, input: str) -> bool:
        raise NotImplementedError("Calling check with an abstract oracle!")

class GrammarOracle(Oracle):
    """
    An oracle backed by a `Grammar` object.
    """

    def __init__(self, grammar: Grammar):
        self.grammar = grammar

    def check(self, input: str) -> bool:
        return self.grammar.parser.parse(input)

class SubprocessOracle(Oracle):
    """
    An oracle backed by an external subprocess.
    """

    def __init__(self, command: str):
        """
        Initialize the oracle, assuming `command` is a string representing a
        command that takes a filename as input.
        """
        self.command = command

    def check(self, input: str) -> bool:
        """
        Assumes the oracle returns a non-zero exit status for errors, which is
        maybe too restrictive
        """
        temp = tempfile.NamedTemporaryFile() # Named temporary will be deleted once this obj is out of scope
        temp_name = temp.name
        results = subprocess.run([self.command, temp_name], capture_output=True)
        return results.returncode == 0

