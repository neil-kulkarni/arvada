from lark import Lark
import tempfile
import subprocess
import os

class ParseException(Exception):
    pass

class ExternalOracle:
    def __init__(self, command):
        self.command = command
        self.cache_set = {}
        self.parse_calls = 0

    def _parse_internal(self, string):
        FNULL = open(os.devnull, 'w')
        f = tempfile.NamedTemporaryFile()
        f.write(bytes(string, 'utf-8'))
        f_name = f.name
        f.flush()
        try:
            # With check = True, throws a CalledProcessError if the exit code is non-zero
            subprocess.run([self.command, f_name], stdout=FNULL, stderr=FNULL, check=True)
            f.close()
            FNULL.close()
            return True
        except subprocess.CalledProcessError as e:
            f.close()
            FNULL.close()
            return False

    def parse(self, string):
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
