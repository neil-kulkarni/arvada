grammar g_while;

start: stmt EOF;
stmt : 'L' SPACE '=' SPACE numexpr
  | 'if' SPACE boolexpr SPACE 'then' SPACE stmt SPACE 'else' SPACE stmt
  | stmt SPACE ';' SPACE stmt
  | 'while' SPACE boolexpr SPACE 'do' SPACE stmt
  | 'skip';

boolexpr : 'true' | 'false' | numexpr SPACE '==' SPACE numexpr | boolexpr SPACE '&' SPACE boolexpr | '~' boolexpr;

numexpr : 'L' | 'n' | '(' numexpr '+' numexpr ')';

SPACE: ' ';
