
// Generated from g_while.g4 by ANTLR 4.7.1


#include "g_whileListener.h"

#include "g_whileParser.h"


using namespace antlrcpp;
using namespace antlr4;

g_whileParser::g_whileParser(TokenStream *input) : Parser(input) {
  _interpreter = new atn::ParserATNSimulator(this, _atn, _decisionToDFA, _sharedContextCache);
}

g_whileParser::~g_whileParser() {
  delete _interpreter;
}

std::string g_whileParser::getGrammarFileName() const {
  return "g_while.g4";
}

const std::vector<std::string>& g_whileParser::getRuleNames() const {
  return _ruleNames;
}

dfa::Vocabulary& g_whileParser::getVocabulary() const {
  return _vocabulary;
}


//----------------- StartContext ------------------------------------------------------------------

g_whileParser::StartContext::StartContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

g_whileParser::StmtContext* g_whileParser::StartContext::stmt() {
  return getRuleContext<g_whileParser::StmtContext>(0);
}

tree::TerminalNode* g_whileParser::StartContext::EOF() {
  return getToken(g_whileParser::EOF, 0);
}


size_t g_whileParser::StartContext::getRuleIndex() const {
  return g_whileParser::RuleStart;
}

void g_whileParser::StartContext::enterRule(tree::ParseTreeListener *listener) {
  auto parserListener = dynamic_cast<g_whileListener *>(listener);
  if (parserListener != nullptr)
    parserListener->enterStart(this);
}

void g_whileParser::StartContext::exitRule(tree::ParseTreeListener *listener) {
  auto parserListener = dynamic_cast<g_whileListener *>(listener);
  if (parserListener != nullptr)
    parserListener->exitStart(this);
}

g_whileParser::StartContext* g_whileParser::start() {
  StartContext *_localctx = _tracker.createInstance<StartContext>(_ctx, getState());
  enterRule(_localctx, 0, g_whileParser::RuleStart);

  auto onExit = finally([=] {
    exitRule();
  });
  try {
    enterOuterAlt(_localctx, 1);
    setState(8);
    stmt(0);
    setState(9);
    match(g_whileParser::EOF);
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- StmtContext ------------------------------------------------------------------

g_whileParser::StmtContext::StmtContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

std::vector<tree::TerminalNode *> g_whileParser::StmtContext::SPACE() {
  return getTokens(g_whileParser::SPACE);
}

tree::TerminalNode* g_whileParser::StmtContext::SPACE(size_t i) {
  return getToken(g_whileParser::SPACE, i);
}

g_whileParser::NumexprContext* g_whileParser::StmtContext::numexpr() {
  return getRuleContext<g_whileParser::NumexprContext>(0);
}

g_whileParser::BoolexprContext* g_whileParser::StmtContext::boolexpr() {
  return getRuleContext<g_whileParser::BoolexprContext>(0);
}

std::vector<g_whileParser::StmtContext *> g_whileParser::StmtContext::stmt() {
  return getRuleContexts<g_whileParser::StmtContext>();
}

g_whileParser::StmtContext* g_whileParser::StmtContext::stmt(size_t i) {
  return getRuleContext<g_whileParser::StmtContext>(i);
}


size_t g_whileParser::StmtContext::getRuleIndex() const {
  return g_whileParser::RuleStmt;
}

void g_whileParser::StmtContext::enterRule(tree::ParseTreeListener *listener) {
  auto parserListener = dynamic_cast<g_whileListener *>(listener);
  if (parserListener != nullptr)
    parserListener->enterStmt(this);
}

void g_whileParser::StmtContext::exitRule(tree::ParseTreeListener *listener) {
  auto parserListener = dynamic_cast<g_whileListener *>(listener);
  if (parserListener != nullptr)
    parserListener->exitStmt(this);
}


g_whileParser::StmtContext* g_whileParser::stmt() {
   return stmt(0);
}

g_whileParser::StmtContext* g_whileParser::stmt(int precedence) {
  ParserRuleContext *parentContext = _ctx;
  size_t parentState = getState();
  g_whileParser::StmtContext *_localctx = _tracker.createInstance<StmtContext>(_ctx, parentState);
  g_whileParser::StmtContext *previousContext = _localctx;
  size_t startState = 2;
  enterRecursionRule(_localctx, 2, g_whileParser::RuleStmt, precedence);

    

  auto onExit = finally([=] {
    unrollRecursionContexts(parentContext);
  });
  try {
    size_t alt;
    enterOuterAlt(_localctx, 1);
    setState(38);
    _errHandler->sync(this);
    switch (_input->LA(1)) {
      case g_whileParser::T__0: {
        setState(12);
        match(g_whileParser::T__0);
        setState(13);
        match(g_whileParser::SPACE);
        setState(14);
        match(g_whileParser::T__1);
        setState(15);
        match(g_whileParser::SPACE);
        setState(16);
        numexpr();
        break;
      }

      case g_whileParser::T__2: {
        setState(17);
        match(g_whileParser::T__2);
        setState(18);
        match(g_whileParser::SPACE);
        setState(19);
        boolexpr(0);
        setState(20);
        match(g_whileParser::SPACE);
        setState(21);
        match(g_whileParser::T__3);
        setState(22);
        match(g_whileParser::SPACE);
        setState(23);
        stmt(0);
        setState(24);
        match(g_whileParser::SPACE);
        setState(25);
        match(g_whileParser::T__4);
        setState(26);
        match(g_whileParser::SPACE);
        setState(27);
        stmt(4);
        break;
      }

      case g_whileParser::T__6: {
        setState(29);
        match(g_whileParser::T__6);
        setState(30);
        match(g_whileParser::SPACE);
        setState(31);
        boolexpr(0);
        setState(32);
        match(g_whileParser::SPACE);
        setState(33);
        match(g_whileParser::T__7);
        setState(34);
        match(g_whileParser::SPACE);
        setState(35);
        stmt(2);
        break;
      }

      case g_whileParser::T__8: {
        setState(37);
        match(g_whileParser::T__8);
        break;
      }

    default:
      throw NoViableAltException(this);
    }
    _ctx->stop = _input->LT(-1);
    setState(47);
    _errHandler->sync(this);
    alt = getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 1, _ctx);
    while (alt != 2 && alt != atn::ATN::INVALID_ALT_NUMBER) {
      if (alt == 1) {
        if (!_parseListeners.empty())
          triggerExitRuleEvent();
        previousContext = _localctx;
        _localctx = _tracker.createInstance<StmtContext>(parentContext, parentState);
        pushNewRecursionContext(_localctx, startState, RuleStmt);
        setState(40);

        if (!(precpred(_ctx, 3))) throw FailedPredicateException(this, "precpred(_ctx, 3)");
        setState(41);
        match(g_whileParser::SPACE);
        setState(42);
        match(g_whileParser::T__5);
        setState(43);
        match(g_whileParser::SPACE);
        setState(44);
        stmt(4); 
      }
      setState(49);
      _errHandler->sync(this);
      alt = getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 1, _ctx);
    }
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }
  return _localctx;
}

//----------------- BoolexprContext ------------------------------------------------------------------

g_whileParser::BoolexprContext::BoolexprContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

std::vector<g_whileParser::NumexprContext *> g_whileParser::BoolexprContext::numexpr() {
  return getRuleContexts<g_whileParser::NumexprContext>();
}

g_whileParser::NumexprContext* g_whileParser::BoolexprContext::numexpr(size_t i) {
  return getRuleContext<g_whileParser::NumexprContext>(i);
}

std::vector<tree::TerminalNode *> g_whileParser::BoolexprContext::SPACE() {
  return getTokens(g_whileParser::SPACE);
}

tree::TerminalNode* g_whileParser::BoolexprContext::SPACE(size_t i) {
  return getToken(g_whileParser::SPACE, i);
}

std::vector<g_whileParser::BoolexprContext *> g_whileParser::BoolexprContext::boolexpr() {
  return getRuleContexts<g_whileParser::BoolexprContext>();
}

g_whileParser::BoolexprContext* g_whileParser::BoolexprContext::boolexpr(size_t i) {
  return getRuleContext<g_whileParser::BoolexprContext>(i);
}


size_t g_whileParser::BoolexprContext::getRuleIndex() const {
  return g_whileParser::RuleBoolexpr;
}

void g_whileParser::BoolexprContext::enterRule(tree::ParseTreeListener *listener) {
  auto parserListener = dynamic_cast<g_whileListener *>(listener);
  if (parserListener != nullptr)
    parserListener->enterBoolexpr(this);
}

void g_whileParser::BoolexprContext::exitRule(tree::ParseTreeListener *listener) {
  auto parserListener = dynamic_cast<g_whileListener *>(listener);
  if (parserListener != nullptr)
    parserListener->exitBoolexpr(this);
}


g_whileParser::BoolexprContext* g_whileParser::boolexpr() {
   return boolexpr(0);
}

g_whileParser::BoolexprContext* g_whileParser::boolexpr(int precedence) {
  ParserRuleContext *parentContext = _ctx;
  size_t parentState = getState();
  g_whileParser::BoolexprContext *_localctx = _tracker.createInstance<BoolexprContext>(_ctx, parentState);
  g_whileParser::BoolexprContext *previousContext = _localctx;
  size_t startState = 4;
  enterRecursionRule(_localctx, 4, g_whileParser::RuleBoolexpr, precedence);

    

  auto onExit = finally([=] {
    unrollRecursionContexts(parentContext);
  });
  try {
    size_t alt;
    enterOuterAlt(_localctx, 1);
    setState(61);
    _errHandler->sync(this);
    switch (_input->LA(1)) {
      case g_whileParser::T__9: {
        setState(51);
        match(g_whileParser::T__9);
        break;
      }

      case g_whileParser::T__10: {
        setState(52);
        match(g_whileParser::T__10);
        break;
      }

      case g_whileParser::T__0:
      case g_whileParser::T__14:
      case g_whileParser::T__15: {
        setState(53);
        numexpr();
        setState(54);
        match(g_whileParser::SPACE);
        setState(55);
        match(g_whileParser::T__11);
        setState(56);
        match(g_whileParser::SPACE);
        setState(57);
        numexpr();
        break;
      }

      case g_whileParser::T__13: {
        setState(59);
        match(g_whileParser::T__13);
        setState(60);
        boolexpr(1);
        break;
      }

    default:
      throw NoViableAltException(this);
    }
    _ctx->stop = _input->LT(-1);
    setState(70);
    _errHandler->sync(this);
    alt = getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 3, _ctx);
    while (alt != 2 && alt != atn::ATN::INVALID_ALT_NUMBER) {
      if (alt == 1) {
        if (!_parseListeners.empty())
          triggerExitRuleEvent();
        previousContext = _localctx;
        _localctx = _tracker.createInstance<BoolexprContext>(parentContext, parentState);
        pushNewRecursionContext(_localctx, startState, RuleBoolexpr);
        setState(63);

        if (!(precpred(_ctx, 2))) throw FailedPredicateException(this, "precpred(_ctx, 2)");
        setState(64);
        match(g_whileParser::SPACE);
        setState(65);
        match(g_whileParser::T__12);
        setState(66);
        match(g_whileParser::SPACE);
        setState(67);
        boolexpr(3); 
      }
      setState(72);
      _errHandler->sync(this);
      alt = getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 3, _ctx);
    }
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }
  return _localctx;
}

//----------------- NumexprContext ------------------------------------------------------------------

g_whileParser::NumexprContext::NumexprContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

std::vector<g_whileParser::NumexprContext *> g_whileParser::NumexprContext::numexpr() {
  return getRuleContexts<g_whileParser::NumexprContext>();
}

g_whileParser::NumexprContext* g_whileParser::NumexprContext::numexpr(size_t i) {
  return getRuleContext<g_whileParser::NumexprContext>(i);
}


size_t g_whileParser::NumexprContext::getRuleIndex() const {
  return g_whileParser::RuleNumexpr;
}

void g_whileParser::NumexprContext::enterRule(tree::ParseTreeListener *listener) {
  auto parserListener = dynamic_cast<g_whileListener *>(listener);
  if (parserListener != nullptr)
    parserListener->enterNumexpr(this);
}

void g_whileParser::NumexprContext::exitRule(tree::ParseTreeListener *listener) {
  auto parserListener = dynamic_cast<g_whileListener *>(listener);
  if (parserListener != nullptr)
    parserListener->exitNumexpr(this);
}

g_whileParser::NumexprContext* g_whileParser::numexpr() {
  NumexprContext *_localctx = _tracker.createInstance<NumexprContext>(_ctx, getState());
  enterRule(_localctx, 6, g_whileParser::RuleNumexpr);

  auto onExit = finally([=] {
    exitRule();
  });
  try {
    setState(81);
    _errHandler->sync(this);
    switch (_input->LA(1)) {
      case g_whileParser::T__0: {
        enterOuterAlt(_localctx, 1);
        setState(73);
        match(g_whileParser::T__0);
        break;
      }

      case g_whileParser::T__14: {
        enterOuterAlt(_localctx, 2);
        setState(74);
        match(g_whileParser::T__14);
        break;
      }

      case g_whileParser::T__15: {
        enterOuterAlt(_localctx, 3);
        setState(75);
        match(g_whileParser::T__15);
        setState(76);
        numexpr();
        setState(77);
        match(g_whileParser::T__16);
        setState(78);
        numexpr();
        setState(79);
        match(g_whileParser::T__17);
        break;
      }

    default:
      throw NoViableAltException(this);
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

bool g_whileParser::sempred(RuleContext *context, size_t ruleIndex, size_t predicateIndex) {
  switch (ruleIndex) {
    case 1: return stmtSempred(dynamic_cast<StmtContext *>(context), predicateIndex);
    case 2: return boolexprSempred(dynamic_cast<BoolexprContext *>(context), predicateIndex);

  default:
    break;
  }
  return true;
}

bool g_whileParser::stmtSempred(StmtContext *_localctx, size_t predicateIndex) {
  switch (predicateIndex) {
    case 0: return precpred(_ctx, 3);

  default:
    break;
  }
  return true;
}

bool g_whileParser::boolexprSempred(BoolexprContext *_localctx, size_t predicateIndex) {
  switch (predicateIndex) {
    case 1: return precpred(_ctx, 2);

  default:
    break;
  }
  return true;
}

// Static vars and initialization.
std::vector<dfa::DFA> g_whileParser::_decisionToDFA;
atn::PredictionContextCache g_whileParser::_sharedContextCache;

// We own the ATN which in turn owns the ATN states.
atn::ATN g_whileParser::_atn;
std::vector<uint16_t> g_whileParser::_serializedATN;

std::vector<std::string> g_whileParser::_ruleNames = {
  "start", "stmt", "boolexpr", "numexpr"
};

std::vector<std::string> g_whileParser::_literalNames = {
  "", "'L'", "'='", "'if'", "'then'", "'else'", "';'", "'while'", "'do'", 
  "'skip'", "'true'", "'false'", "'=='", "'&'", "'~'", "'n'", "'('", "'+'", 
  "')'", "' '"
};

std::vector<std::string> g_whileParser::_symbolicNames = {
  "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", 
  "", "SPACE"
};

dfa::Vocabulary g_whileParser::_vocabulary(_literalNames, _symbolicNames);

std::vector<std::string> g_whileParser::_tokenNames;

g_whileParser::Initializer::Initializer() {
	for (size_t i = 0; i < _symbolicNames.size(); ++i) {
		std::string name = _vocabulary.getLiteralName(i);
		if (name.empty()) {
			name = _vocabulary.getSymbolicName(i);
		}

		if (name.empty()) {
			_tokenNames.push_back("<INVALID>");
		} else {
      _tokenNames.push_back(name);
    }
	}

  _serializedATN = {
    0x3, 0x608b, 0xa72a, 0x8133, 0xb9ed, 0x417c, 0x3be7, 0x7786, 0x5964, 
    0x3, 0x15, 0x56, 0x4, 0x2, 0x9, 0x2, 0x4, 0x3, 0x9, 0x3, 0x4, 0x4, 0x9, 
    0x4, 0x4, 0x5, 0x9, 0x5, 0x3, 0x2, 0x3, 0x2, 0x3, 0x2, 0x3, 0x3, 0x3, 
    0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 
    0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 
    0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 
    0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x5, 0x3, 0x29, 0xa, 0x3, 
    0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x3, 0x7, 0x3, 0x30, 0xa, 
    0x3, 0xc, 0x3, 0xe, 0x3, 0x33, 0xb, 0x3, 0x3, 0x4, 0x3, 0x4, 0x3, 0x4, 
    0x3, 0x4, 0x3, 0x4, 0x3, 0x4, 0x3, 0x4, 0x3, 0x4, 0x3, 0x4, 0x3, 0x4, 
    0x3, 0x4, 0x5, 0x4, 0x40, 0xa, 0x4, 0x3, 0x4, 0x3, 0x4, 0x3, 0x4, 0x3, 
    0x4, 0x3, 0x4, 0x7, 0x4, 0x47, 0xa, 0x4, 0xc, 0x4, 0xe, 0x4, 0x4a, 0xb, 
    0x4, 0x3, 0x5, 0x3, 0x5, 0x3, 0x5, 0x3, 0x5, 0x3, 0x5, 0x3, 0x5, 0x3, 
    0x5, 0x3, 0x5, 0x5, 0x5, 0x54, 0xa, 0x5, 0x3, 0x5, 0x2, 0x4, 0x4, 0x6, 
    0x6, 0x2, 0x4, 0x6, 0x8, 0x2, 0x2, 0x2, 0x5b, 0x2, 0xa, 0x3, 0x2, 0x2, 
    0x2, 0x4, 0x28, 0x3, 0x2, 0x2, 0x2, 0x6, 0x3f, 0x3, 0x2, 0x2, 0x2, 0x8, 
    0x53, 0x3, 0x2, 0x2, 0x2, 0xa, 0xb, 0x5, 0x4, 0x3, 0x2, 0xb, 0xc, 0x7, 
    0x2, 0x2, 0x3, 0xc, 0x3, 0x3, 0x2, 0x2, 0x2, 0xd, 0xe, 0x8, 0x3, 0x1, 
    0x2, 0xe, 0xf, 0x7, 0x3, 0x2, 0x2, 0xf, 0x10, 0x7, 0x15, 0x2, 0x2, 0x10, 
    0x11, 0x7, 0x4, 0x2, 0x2, 0x11, 0x12, 0x7, 0x15, 0x2, 0x2, 0x12, 0x29, 
    0x5, 0x8, 0x5, 0x2, 0x13, 0x14, 0x7, 0x5, 0x2, 0x2, 0x14, 0x15, 0x7, 
    0x15, 0x2, 0x2, 0x15, 0x16, 0x5, 0x6, 0x4, 0x2, 0x16, 0x17, 0x7, 0x15, 
    0x2, 0x2, 0x17, 0x18, 0x7, 0x6, 0x2, 0x2, 0x18, 0x19, 0x7, 0x15, 0x2, 
    0x2, 0x19, 0x1a, 0x5, 0x4, 0x3, 0x2, 0x1a, 0x1b, 0x7, 0x15, 0x2, 0x2, 
    0x1b, 0x1c, 0x7, 0x7, 0x2, 0x2, 0x1c, 0x1d, 0x7, 0x15, 0x2, 0x2, 0x1d, 
    0x1e, 0x5, 0x4, 0x3, 0x6, 0x1e, 0x29, 0x3, 0x2, 0x2, 0x2, 0x1f, 0x20, 
    0x7, 0x9, 0x2, 0x2, 0x20, 0x21, 0x7, 0x15, 0x2, 0x2, 0x21, 0x22, 0x5, 
    0x6, 0x4, 0x2, 0x22, 0x23, 0x7, 0x15, 0x2, 0x2, 0x23, 0x24, 0x7, 0xa, 
    0x2, 0x2, 0x24, 0x25, 0x7, 0x15, 0x2, 0x2, 0x25, 0x26, 0x5, 0x4, 0x3, 
    0x4, 0x26, 0x29, 0x3, 0x2, 0x2, 0x2, 0x27, 0x29, 0x7, 0xb, 0x2, 0x2, 
    0x28, 0xd, 0x3, 0x2, 0x2, 0x2, 0x28, 0x13, 0x3, 0x2, 0x2, 0x2, 0x28, 
    0x1f, 0x3, 0x2, 0x2, 0x2, 0x28, 0x27, 0x3, 0x2, 0x2, 0x2, 0x29, 0x31, 
    0x3, 0x2, 0x2, 0x2, 0x2a, 0x2b, 0xc, 0x5, 0x2, 0x2, 0x2b, 0x2c, 0x7, 
    0x15, 0x2, 0x2, 0x2c, 0x2d, 0x7, 0x8, 0x2, 0x2, 0x2d, 0x2e, 0x7, 0x15, 
    0x2, 0x2, 0x2e, 0x30, 0x5, 0x4, 0x3, 0x6, 0x2f, 0x2a, 0x3, 0x2, 0x2, 
    0x2, 0x30, 0x33, 0x3, 0x2, 0x2, 0x2, 0x31, 0x2f, 0x3, 0x2, 0x2, 0x2, 
    0x31, 0x32, 0x3, 0x2, 0x2, 0x2, 0x32, 0x5, 0x3, 0x2, 0x2, 0x2, 0x33, 
    0x31, 0x3, 0x2, 0x2, 0x2, 0x34, 0x35, 0x8, 0x4, 0x1, 0x2, 0x35, 0x40, 
    0x7, 0xc, 0x2, 0x2, 0x36, 0x40, 0x7, 0xd, 0x2, 0x2, 0x37, 0x38, 0x5, 
    0x8, 0x5, 0x2, 0x38, 0x39, 0x7, 0x15, 0x2, 0x2, 0x39, 0x3a, 0x7, 0xe, 
    0x2, 0x2, 0x3a, 0x3b, 0x7, 0x15, 0x2, 0x2, 0x3b, 0x3c, 0x5, 0x8, 0x5, 
    0x2, 0x3c, 0x40, 0x3, 0x2, 0x2, 0x2, 0x3d, 0x3e, 0x7, 0x10, 0x2, 0x2, 
    0x3e, 0x40, 0x5, 0x6, 0x4, 0x3, 0x3f, 0x34, 0x3, 0x2, 0x2, 0x2, 0x3f, 
    0x36, 0x3, 0x2, 0x2, 0x2, 0x3f, 0x37, 0x3, 0x2, 0x2, 0x2, 0x3f, 0x3d, 
    0x3, 0x2, 0x2, 0x2, 0x40, 0x48, 0x3, 0x2, 0x2, 0x2, 0x41, 0x42, 0xc, 
    0x4, 0x2, 0x2, 0x42, 0x43, 0x7, 0x15, 0x2, 0x2, 0x43, 0x44, 0x7, 0xf, 
    0x2, 0x2, 0x44, 0x45, 0x7, 0x15, 0x2, 0x2, 0x45, 0x47, 0x5, 0x6, 0x4, 
    0x5, 0x46, 0x41, 0x3, 0x2, 0x2, 0x2, 0x47, 0x4a, 0x3, 0x2, 0x2, 0x2, 
    0x48, 0x46, 0x3, 0x2, 0x2, 0x2, 0x48, 0x49, 0x3, 0x2, 0x2, 0x2, 0x49, 
    0x7, 0x3, 0x2, 0x2, 0x2, 0x4a, 0x48, 0x3, 0x2, 0x2, 0x2, 0x4b, 0x54, 
    0x7, 0x3, 0x2, 0x2, 0x4c, 0x54, 0x7, 0x11, 0x2, 0x2, 0x4d, 0x4e, 0x7, 
    0x12, 0x2, 0x2, 0x4e, 0x4f, 0x5, 0x8, 0x5, 0x2, 0x4f, 0x50, 0x7, 0x13, 
    0x2, 0x2, 0x50, 0x51, 0x5, 0x8, 0x5, 0x2, 0x51, 0x52, 0x7, 0x14, 0x2, 
    0x2, 0x52, 0x54, 0x3, 0x2, 0x2, 0x2, 0x53, 0x4b, 0x3, 0x2, 0x2, 0x2, 
    0x53, 0x4c, 0x3, 0x2, 0x2, 0x2, 0x53, 0x4d, 0x3, 0x2, 0x2, 0x2, 0x54, 
    0x9, 0x3, 0x2, 0x2, 0x2, 0x7, 0x28, 0x31, 0x3f, 0x48, 0x53, 
  };

  atn::ATNDeserializer deserializer;
  _atn = deserializer.deserialize(_serializedATN);

  size_t count = _atn.getNumberOfDecisions();
  _decisionToDFA.reserve(count);
  for (size_t i = 0; i < count; i++) { 
    _decisionToDFA.emplace_back(_atn.getDecisionState(i), i);
  }
}

g_whileParser::Initializer g_whileParser::_init;
