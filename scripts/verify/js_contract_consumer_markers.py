#!/usr/bin/env python3
"""Strict lexical recognizers shared by JavaScript contract-consumer guards."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _Token:
    value: str
    kind: str


_REGEX_PREFIXES = {
    "(", "[", "{", ",", ";", ":", "=", "==", "===", "!=", "!==",
    "!", "?", "&&", "||", "??", "+", "-", "*", "%", "&", "|", "^",
    "~", "<", ">", "<=", ">=", "=>", "return", "throw", "case", "delete",
    "typeof", "void", "in", "instanceof", "yield", "await",
}


def _regex_can_start(tokens: list[_Token]) -> bool:
    return not tokens or tokens[-1].value in _REGEX_PREFIXES


def _consume_quoted(source: str, index: int, quote: str) -> int | None:
    index += 1
    while index < len(source):
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char == quote:
            return index + 1
        if char in {"\n", "\r"}:
            return None
        index += 1
    return None


def _consume_template(source: str, index: int) -> int | None:
    """Skip a template literal without treating its text as executable source.

    Template expressions are deliberately skipped with the surrounding literal.
    A consumer guard must see the authority access in ordinary executable code;
    hiding it inside interpolation is not accepted as its required source marker.
    """

    index += 1
    expression_depth = 0
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if char == "\\":
            index += 2
            continue
        if char == "`" and expression_depth == 0:
            return index + 1
        if char == "$" and next_char == "{":
            expression_depth += 1
            index += 2
            continue
        if expression_depth:
            if char in {"'", '"'}:
                consumed = _consume_quoted(source, index, char)
                if consumed is None:
                    return None
                index = consumed
                continue
            if char == "`":
                consumed = _consume_template(source, index)
                if consumed is None:
                    return None
                index = consumed
                continue
            if char == "{" :
                expression_depth += 1
            elif char == "}":
                expression_depth -= 1
        index += 1
    return None


def _consume_regex(source: str, index: int) -> int | None:
    index += 1
    in_character_class = False
    while index < len(source):
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char in {"\n", "\r"}:
            return None
        if char == "[":
            in_character_class = True
        elif char == "]":
            in_character_class = False
        elif char == "/" and not in_character_class:
            index += 1
            while index < len(source) and (source[index].isalpha() or source[index] == "_"):
                index += 1
            return index
        index += 1
    return None


def _tokenize_javascript(source: str) -> list[_Token] | None:
    tokens: list[_Token] = []
    brackets: list[str] = []
    matching = {")": "(", "]": "[", "}": "{"}
    index = 0
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if char.isspace():
            index += 1
            continue
        if char == "/" and next_char == "/":
            newline = source.find("\n", index + 2)
            index = len(source) if newline < 0 else newline + 1
            continue
        if char == "/" and next_char == "*":
            end = source.find("*/", index + 2)
            if end < 0:
                return None
            index = end + 2
            continue
        if char in {"'", '"'}:
            consumed = _consume_quoted(source, index, char)
            if consumed is None:
                return None
            index = consumed
            continue
        if char == "`":
            consumed = _consume_template(source, index)
            if consumed is None:
                return None
            index = consumed
            continue
        if char == "/" and _regex_can_start(tokens):
            consumed = _consume_regex(source, index)
            if consumed is None:
                return None
            index = consumed
            continue
        if char.isalpha() or char in {"_", "$"}:
            end = index + 1
            while end < len(source) and (source[end].isalnum() or source[end] in {"_", "$"}):
                end += 1
            tokens.append(_Token(source[index:end], "identifier"))
            index = end
            continue
        operator = next((value for value in ("===", "!==", "?.", "=>", "==", "!=", "&&", "||", "??", "<=", ">=")
                         if source.startswith(value, index)), None)
        if operator:
            tokens.append(_Token(operator, "operator"))
            index += len(operator)
            continue
        if char in "([{":
            brackets.append(char)
        elif char in ")]}":
            if not brackets or brackets.pop() != matching[char]:
                return None
        tokens.append(_Token(char, "punctuation"))
        index += 1
    return tokens if not brackets else None


def has_contract_page_info_view_type_access(source: str) -> bool:
    """Recognize only the canonical contract.snapshot.pageInfo.viewType chain.

    Optional chaining may be used after ``contract``, ``snapshot`` or
    ``pageInfo`` without changing the consumed contract identity. The root
    guard remains mandatory and computed/dynamic or extended paths are not
    accepted.
    """

    tokens = _tokenize_javascript(source)
    if tokens is None:
        return False
    expected_identifiers = ("contract", "snapshot", "pageInfo", "viewType")
    for index in range(len(tokens) - 6):
        window = tokens[index:index + 7]
        if tuple(window[offset].value for offset in (0, 2, 4, 6)) != expected_identifiers:
            continue
        if any(window[offset].kind != "identifier" for offset in (0, 2, 4, 6)):
            continue
        if window[1].value != "?." or window[3].value not in {".", "?."} or window[5].value not in {".", "?."}:
            continue
        previous = tokens[index - 1].value if index else ""
        following = tokens[index + 7].value if index + 7 < len(tokens) else ""
        if previous in {".", "?."} or following in {".", "?.", "["}:
            continue
        return True
    return False
