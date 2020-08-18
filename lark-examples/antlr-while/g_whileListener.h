
// Generated from g_while.g4 by ANTLR 4.7.1

#pragma once


#include "antlr4-runtime.h"
#include "g_whileParser.h"


/**
 * This interface defines an abstract listener for a parse tree produced by g_whileParser.
 */
class  g_whileListener : public antlr4::tree::ParseTreeListener {
public:

  virtual void enterStart(g_whileParser::StartContext *ctx) = 0;
  virtual void exitStart(g_whileParser::StartContext *ctx) = 0;

  virtual void enterStmt(g_whileParser::StmtContext *ctx) = 0;
  virtual void exitStmt(g_whileParser::StmtContext *ctx) = 0;

  virtual void enterBoolexpr(g_whileParser::BoolexprContext *ctx) = 0;
  virtual void exitBoolexpr(g_whileParser::BoolexprContext *ctx) = 0;

  virtual void enterNumexpr(g_whileParser::NumexprContext *ctx) = 0;
  virtual void exitNumexpr(g_whileParser::NumexprContext *ctx) = 0;


};

