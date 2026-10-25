"""Lightweight, dependency-free SQL inspector shared by Core and plugins.

Replaces raw substring matching on the query text. The query is tokenized first so
comments, string literals and quoted identifiers can never be mistaken for keywords
(``-- WHERE``, ``'UPDATE'``, ``[Orders]``, column ``UPDATED_AT``).

This is a conservative guard, not a full SQL parser: anything it cannot classify is
treated as the *safer* outcome by callers (WRITE, unbounded, multi-statement).
"""

import re
from dataclasses import dataclass

WRITE_KEYWORDS: frozenset[str] = frozenset(
    {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "MERGE",
        "EXEC", "EXECUTE", "GRANT", "REVOKE", "DENY", "BULK", "RENAME", "REPLACE",
        "UPSERT", "CALL", "SHUTDOWN", "KILL", "BACKUP", "RESTORE", "DBCC",
    }
)
_CLAUSE_END = frozenset({"GROUP", "ORDER", "HAVING", "UNION", "INTERSECT", "EXCEPT", "LIMIT", "OFFSET", "FETCH", "FOR", "OPTION", "WINDOW"})
_TABLE_STOP = frozenset({"WHERE", "ON", "USING", "SET", "SELECT", "VALUES", "GROUP", "ORDER", "HAVING", "UNION", "INTERSECT", "EXCEPT", "LIMIT", "OFFSET", "FETCH", "FOR", "OPTION", "WINDOW", "WITH"})
_JOIN_MODIFIERS = frozenset({"INNER", "LEFT", "RIGHT", "FULL", "CROSS", "OUTER", "NATURAL"})

# Token kinds
WORD, IDENT, STRING, NUMBER, PUNCT = "word", "ident", "string", "number", "punct"


@dataclass(frozen=True)
class Token:
    kind: str
    text: str  # words are upper-cased; identifiers keep their unquoted, upper-cased name

    def is_kw(self, *names: str) -> bool:
        return self.kind == WORD and self.text in names


def tokenize(query: str) -> list[Token]:
    """Split SQL into tokens, dropping comments and whitespace."""
    tokens: list[Token] = []
    i, n = 0, len(query)
    while i < n:
        ch = query[i]
        if ch.isspace():
            i += 1
        elif query.startswith("--", i):
            end = query.find("\n", i)
            i = n if end == -1 else end + 1
        elif query.startswith("/*", i):
            end = query.find("*/", i + 2)
            i = n if end == -1 else end + 2  # unterminated comment swallows the rest
        elif ch == "'":
            j = i + 1
            while j < n:
                if query[j] == "'":
                    if j + 1 < n and query[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            tokens.append(Token(STRING, query[i + 1 : j]))
            i = j + 1
        elif ch in '"`[':
            closer = "]" if ch == "[" else ch
            end = query.find(closer, i + 1)
            end = n if end == -1 else end
            tokens.append(Token(IDENT, query[i + 1 : end].upper()))
            i = end + 1
        elif ch.isdigit():
            j = i
            while j < n and (query[j].isalnum() or query[j] == "."):
                j += 1
            tokens.append(Token(NUMBER, query[i:j]))
            i = j
        elif ch.isalpha() or ch in "_@":
            j = i
            while j < n and (query[j].isalnum() or query[j] in "_@$"):
                j += 1
            tokens.append(Token(WORD, query[i:j].upper()))
            i = j
        elif query[i : i + 2] in ("<>", "!=", "<=", ">="):
            tokens.append(Token(PUNCT, query[i : i + 2]))
            i += 2
        else:
            tokens.append(Token(PUNCT, ch))
            i += 1
    return tokens


def split_statements(tokens: list[Token]) -> list[list[Token]]:
    """Split on top-level ``;`` and drop empty statements."""
    statements: list[list[Token]] = [[]]
    for tok in tokens:
        if tok.kind == PUNCT and tok.text == ";":
            statements.append([])
        else:
            statements[-1].append(tok)
    return [s for s in statements if s]


def statement_count(query: str) -> int:
    return len(split_statements(tokenize(query)))


def classify_query(query: str) -> str:
    """Return ``WRITE`` if any statement can modify data/state, else ``READ``.

    Works on word tokens only, so ``UPDATED_AT`` or ``'DELETE'`` never count.
    ``SELECT ... INTO`` and ``WITH ... INSERT`` are WRITE. Unparseable/empty -> WRITE.
    """
    tokens = tokenize(query)
    if not tokens:
        return "WRITE"
    for idx, tok in enumerate(tokens):
        if tok.kind != WORD:
            continue
        if tok.text in WRITE_KEYWORDS:
            return "WRITE"
        if tok.text == "INTO" and any(t.is_kw("SELECT") for t in tokens[:idx]):
            return "WRITE"
    return "READ"


def _strip_name(parts: list[str]) -> str:
    return parts[-1] if parts else ""


def referenced_tables(statement: list[Token]) -> set[str]:
    """Collect table names following FROM/JOIN/INTO/UPDATE (schema prefix removed, aliases ignored).

    Subqueries and CTE bodies are scanned too because the whole token list is walked.
    """
    tables: set[str] = set()
    i, n = 0, len(statement)
    while i < n:
        tok = statement[i]
        if tok.is_kw("FROM", "JOIN", "INTO", "UPDATE"):
            expect_list = tok.is_kw("FROM")
            i += 1
            while i < n:
                parts: list[str] = []
                while i < n and statement[i].kind in (WORD, IDENT) and not (
                    statement[i].kind == WORD and statement[i].text in _TABLE_STOP
                ):
                    parts.append(statement[i].text)
                    i += 1
                    if i < n and statement[i].kind == PUNCT and statement[i].text == ".":
                        i += 1
                        continue
                    break
                if parts:
                    tables.add(_strip_name(parts))
                # skip alias / AS alias
                if i < n and statement[i].is_kw("AS"):
                    i += 1
                if (
                    i < n
                    and statement[i].kind in (WORD, IDENT)
                    and not (statement[i].kind == WORD and (statement[i].text in _TABLE_STOP or statement[i].text in _JOIN_MODIFIERS or statement[i].text in ("JOIN", "WITH")))
                ):
                    i += 1
                if expect_list and i < n and statement[i].kind == PUNCT and statement[i].text == ",":
                    i += 1
                    continue
                break
            continue
        i += 1
    tables.discard("")
    return tables


def joins_tables(query: str, table_names: list[str]) -> bool:
    """True if one statement really combines *all* ``table_names`` (JOIN or comma-join)."""
    wanted = {t.strip().upper() for t in table_names if t.strip()}
    if len(wanted) < 2:
        return False
    for stmt in split_statements(tokenize(query)):
        tables = referenced_tables(stmt)
        has_join = any(t.is_kw("JOIN") for t in stmt) or _has_comma_join(stmt)
        if has_join and wanted.issubset(tables):
            return True
    return False


def _has_comma_join(statement: list[Token]) -> bool:
    depth = 0
    in_from = False
    for tok in statement:
        if tok.kind == PUNCT and tok.text == "(":
            depth += 1
        elif tok.kind == PUNCT and tok.text == ")":
            depth -= 1
        elif tok.is_kw("FROM"):
            in_from = True
        elif tok.kind == WORD and tok.text in _TABLE_STOP:
            in_from = False
        elif in_from and tok.kind == PUNCT and tok.text == "," and depth == 0:
            return True
    return False


def _top_level_where(statement: list[Token]) -> list[Token] | None:
    """Tokens of the first depth-0 WHERE clause, or None."""
    depth = 0
    collecting = False
    clause: list[Token] = []
    for tok in statement:
        if tok.kind == PUNCT and tok.text == "(":
            depth += 1
        elif tok.kind == PUNCT and tok.text == ")":
            depth -= 1
        if depth == 0 and tok.is_kw("WHERE") and not collecting:
            collecting = True
            continue
        if collecting:
            if depth == 0 and tok.kind == WORD and tok.text in _CLAUSE_END:
                break
            clause.append(tok)
    return clause if collecting else None


def _strip_parens(tokens: list[Token]) -> list[Token]:
    while (
        len(tokens) >= 2
        and tokens[0].kind == PUNCT and tokens[0].text == "("
        and tokens[-1].kind == PUNCT and tokens[-1].text == ")"
    ):
        tokens = tokens[1:-1]
    return tokens


def _split_top(tokens: list[Token], keyword: str) -> list[list[Token]]:
    parts: list[list[Token]] = [[]]
    depth = 0
    for tok in tokens:
        if tok.kind == PUNCT and tok.text == "(":
            depth += 1
        elif tok.kind == PUNCT and tok.text == ")":
            depth -= 1
        if depth == 0 and tok.is_kw(keyword):
            parts.append([])
        else:
            parts[-1].append(tok)
    return parts


def _is_tautology(tokens: list[Token]) -> bool:
    tokens = _strip_parens(tokens)
    if not tokens:
        return True
    ors = _split_top(tokens, "OR")
    if len(ors) > 1:
        return any(_is_tautology(p) for p in ors)
    ands = _split_top(tokens, "AND")
    if len(ands) > 1:
        return all(_is_tautology(p) for p in ands)
    if len(tokens) == 1 and tokens[0].is_kw("TRUE"):
        return True
    if len(tokens) == 2 and tokens[0].is_kw("NOT") and tokens[1].is_kw("FALSE"):
        return True
    if len(tokens) == 3 and tokens[1].kind == PUNCT:
        left, op, right = tokens
        same = left.kind == right.kind and left.text == right.text
        if op.text in ("=", "<=", ">=") and same:
            return True
        if op.text in ("<>", "!=") and not same and left.kind in (NUMBER, STRING) and right.kind in (NUMBER, STRING):
            return True
        if op.text == "=" and left.kind in (NUMBER, STRING) and right.kind in (NUMBER, STRING) and same:
            return True
    return False


def is_unbounded_scan(query: str) -> bool:
    """True if any SELECT ... FROM statement lacks a *meaningful* top-level WHERE.

    ``-- WHERE`` comments, ``WHERE`` inside a subquery only, and tautologies such as
    ``WHERE 1=1`` / ``WHERE 'a'='a'`` / ``WHERE TRUE`` do not count as a filter.
    """
    for stmt in split_statements(tokenize(query)):
        if not (any(t.is_kw("SELECT") for t in stmt) and any(t.is_kw("FROM") for t in stmt)):
            continue
        where = _top_level_where(stmt)
        if where is None or _is_tautology(where):
            return True
    return False


def plan_mentions_table(plan_text: str, table: str) -> bool:
    """Whole-word table match inside a plan dump (no substring false positives)."""
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(table)}(?![A-Za-z0-9_])", plan_text, re.IGNORECASE) is not None
