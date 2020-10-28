from lark import Lark
import tempfile
import subprocess
import os

"""
This file gives  classes to use as "Oracles" in the Arvada algorithm.
"""

class ParseException(Exception):
    pass

class ExternalOracle:
    """
    An ExternalOracle is a wrapper around an oracle that takes the form of a shell
    command accepting a file as input. We assume the oracle returns True if the
    exit code is 0 (no error). If the external oracle takes >3 seconds to execute,
    we conservatively assume the oracle returns True.
    """

    def __init__(self, command):
        """
        `command` is a string representing the oracle command, i.e. `command` = "readpng"
        in the oracle call:
            $ readpng <MY_FILE>
        """
        self.command = command
        self.cache_set = {}
        self.parse_calls = 0

    def _parse_internal(self, string):
        """
        Does the work of calling the subprocess.
        """
        FNULL = open(os.devnull, 'w')
        f = tempfile.NamedTemporaryFile()
        f.write(bytes(string, 'utf-8'))
        f_name = f.name
        f.flush()
        try:
            # With check = True, throws a CalledProcessError if the exit code is non-zero
            subprocess.run([self.command, f_name], stdout=FNULL, stderr=FNULL, timeout=3, check=True)
            f.close()
            FNULL.close()
            return True
        except subprocess.CalledProcessError as e:
            f.close()
            FNULL.close()
            return False
        except subprocess.TimeoutExpired as e:
            print(f"Caused timeout: {string}")
            f.close()
            FNULL.close()
            return True

    def parse(self, string):
        """
        Caching wrapper around _parse_internal
        """
        self.parse_calls += 1
        if string in self.cache_set:
            if self.cache_set[string]:
                return True
            else:
                raise ParseException(f"doesn't parse: {string}")
        else:
            res = self._parse_internal(string)
            self.cache_set[string] = res
            if res:
                return True
            else:
                raise ParseException(f"doesn't parse: {string}")

class CachingOracle:
    """
    Wraps a "Lark" parser object to provide caching of previous calls.
    """

    def __init__(self, oracle: Lark):
        self.oracle = oracle
        self.cache_set = {}
        self.parse_calls = 0

    def parse(self, string):
        self.parse_calls += 1
        if string in self.cache_set:
            if self.cache_set[string]:
                return True
            else:
                raise ParseException("doesn't parse")
        else:
            try:
                self.oracle.parse(string)
                self.cache_set[string] = True
            except Exception as e:
                self.cache_set[string] = False
                raise ParseException("doesn't parse")
