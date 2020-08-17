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


def lark_to_antlr(gram_name: str, gram_contents: List[str]) -> str:
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
    return '\n'.join(antlr_lines)


def cmake_contents(gram_name: str) -> str:
    contents = """
cmake_minimum_required (VERSION 3.17.1)
project(!!REPLACEME!!)

if(DEFINED ENV{ANTLR_RUNTIME})
        set(ANTLR_RUNTIME  $ENV{ANTLR_RUNTIME})
else()
   message(FATAL_ERROR "Please set ANTLR_RUNTIME to the location of the antlr c++ runtime")
endif()

add_custom_command(OUTPUT !!REPLACEME!!Lexer.cpp !!REPLACEME!!Parser.cpp
        COMMAND antlr4 !!REPLACEME!!.g4 -Dlanguage=Cpp -no-listener -no-visitor
        DEPENDS !!REPLACEME!!.g4)

add_executable(file_parser file_parser.cpp !!REPLACEME!!Lexer.cpp !!REPLACEME!!Parser.cpp)
target_include_directories(file_parser PUBLIC ${ANTLR_RUNTIME}/runtime/src/)
target_link_libraries(file_parser ${ANTLR_RUNTIME}/dist/libantlr4-runtime.a)
"""

    #add_executable(stdin_parser stdin_parser.cpp !!REPLACEME!!Lexer.cpp !!REPLACEME!!Parser.cpp)
    #target_include_directories(stdin_parser PUBLIC ${ANTLR_RUNTIME}/runtime/src/)
    #target_link_libraries(stdin_parser ${ANTLR_RUNTIME}/dist/libantlr4-runtime.a)

    contents =contents.replace("!!REPLACEME!!", gram_name)
    return contents

def parser_contents(gram_name: str, mode :str):
    parser_common= """
    #include <strstream>
#include <string>
#include "antlr4-runtime.h"
#include "!!!REPLACEME!!!Lexer.h"
#include "!!!REPLACEME!!!Parser.h"

class MyParserErrorListener: public antlr4::BaseErrorListener {
  virtual void syntaxError(
      antlr4::Recognizer *recognizer,
      antlr4::Token *offendingSymbol,
      size_t line,
      size_t charPositionInLine,
      const std::string &msg,
      std::exception_ptr e) override {
    std::ostrstream s;
    s << "Line(" << line << ":" << charPositionInLine << ") Error(" << msg << ")";
    throw std::invalid_argument(s.str());
  }
};

int main(int argc, char *argv[]) {
  !!!INPUT_MODE!!!
  !!!REPLACEME!!!Lexer lexer(&input);
  antlr4::CommonTokenStream tokens(&lexer);

  MyParserErrorListener errorListener;

  !!!REPLACEME!!!Parser parser(&tokens);
  parser.removeErrorListeners();
  parser.addErrorListener(&errorListener);
  try {
    antlr4::tree::ParseTree* tree = parser.start();
    return 0;
  } catch (std::invalid_argument &e) {
    std::cerr << e.what() << std::endl;
    return 10;
  }
}
    """
    file_input = """
      std::ifstream input_file(argv[1]);
  antlr4::ANTLRInputStream input(input_file);
    """
    stdin_input = """
    antlr4::ANTLRInputStream input(argv[1]);
    """

    if mode == "stdin":
        return parser_common.replace("!!!REPLACEME!!!", gram_name).replace("!!!INPUT_MODE!!!", stdin_input)
    elif mode == "file":
        return parser_common.replace("!!!REPLACEME!!!", gram_name).replace("!!!INPUT_MODE!!!", file_input)
    else: raise NotImplementedError(f"Don't know what to do with mode {mode}")

