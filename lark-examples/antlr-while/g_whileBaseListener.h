
// Generated from g_while.g4 by ANTLR 4.7.1

#pragma once


#include "antlr4-runtime.h"
#include "g_whileListener.h"


/**
 * This class provides an empty implementation of g_whileListener,
 * which can be extended to create a listener which only needs to handle a subset
 * of the available methods.
 */
class  g_whileBaseListener : public g_whileListener {
public:

  virtual void enterStart(g_whileParser::StartContext * /*ctx*/) override { }
  virtual void exitStart(g_whileParser::StartContext * /*ctx*/) override { }

  virtual void enterStmt(g_whileParser::StmtContext * /*ctx*/) override { }
  virtual void exitStmt(g_whileParser::StmtContext * /*ctx*/) override { }

  virtual void enterBoolexpr(g_whileParser::BoolexprContext * /*ctx*/) override { }
  virtual void exitBoolexpr(g_whileParser::BoolexprContext * /*ctx*/) override { }

  virtual void enterNumexpr(g_whileParser::NumexprContext * /*ctx*/) override { }
  virtual void exitNumexpr(g_whileParser::NumexprContext * /*ctx*/) override { }


  virtual void enterEveryRule(antlr4::ParserRuleContext * /*ctx*/) override { }
  virtual void exitEveryRule(antlr4::ParserRuleContext * /*ctx*/) override { }
  virtual void visitTerminal(antlr4::tree::TerminalNode * /*node*/) override { }
  virtual void visitErrorNode(antlr4::tree::ErrorNode * /*node*/) override { }

};

