#!/usr/bin/env python3
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]

# The type-directed sentinel is the one renderer name the section honours
# implicitly, so it is the one name that needs no branch of its own. Every
# other name in the registry union must be *dispatched* by a renderer branch,
# which is what keeps a registry entry from pointing at a control nobody
# renders. Dispatch is matched in its comparison form, and only where that form
# is code: comments are removed first, and a match whose operand sits inside a
# surrounding string, template literal, or template body text is not a branch.
# A comment or a quoted sentence must not be able to satisfy this guard, and the
# fail-closed half must stay bound to the union rather than merely quoting it.
# A branch is a *render* branch: the element carrying it is an imported component
# tag, and the comparison counts for that element's own name alone, so a
# comparison parked in a helper no render element owns is not a dispatch.
TYPE_DIRECTED_RENDERER = "FormSectionField"
RENDERER_BRANCH_GLOBS = (
    "frontend/apps/web/src/components/template/*.vue",
    "frontend/apps/web/src/components/professional-fields/*.ts",
)
RENDERER_DISPATCH = re.compile(r"componentRenderer\s*===?\s*'([^']+)'")
STRING_LITERAL_QUOTES = "'\"`"
FAIL_CLOSED_MARKER = "data-field-fail-closed"
FAIL_CLOSED_MARKER_BINDING = re.compile(rf":{FAIL_CLOSED_MARKER}\s*=")
FAIL_CLOSED_CALL = r"declaresUnknownComponentRenderer\(\s*[A-Za-z_$][\w$]*\s*\)"
FAIL_CLOSED_BINDING = re.compile(
    rf"""v-if\s*=\s*(?:"\s*{FAIL_CLOSED_CALL}\s*"|'\s*{FAIL_CLOSED_CALL}\s*')"""
)
FAIL_CLOSED_PREDICATE = "function declaresUnknownComponentRenderer("
IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*")
SEMANTIC_MARKERS = (
    "data-component-key", "data-component-readiness", "data-component-renderer",
    "data-component-fallback", "data-contract-adapter", "data-contract-component-version",
)
SEMANTIC_BINDINGS = tuple(rf":{marker}\s*=" for marker in SEMANTIC_MARKERS)
ALERT_ROLE = re.compile(r"""\brole\s*=\s*(?:"alert"|'alert')""")
FAIL_CLOSED_MEMBERSHIP = re.compile(r"!\s*([A-Za-z_$][\w$]*)\.has\(")
FAIL_CLOSED_SET_DECLARATION = r"\b{name}\b\s*(?::[^=]*)?=\s*new Set"
FAIL_CLOSED_SET_ARGUMENT = re.compile(r"new Set\b[^(]*\(([^)]*)\)")
FAIL_CLOSED_SET_CONSTANT = r"(?m)^\s*const\s+{name}\b"
FAIL_CLOSED_SET_REASSIGNED = r"(?m)^\s*{name}\s*=(?!=)"
REGEX_START_AFTER = set("(,=:[!&|?{};+-*%<>~^")
TAG_OPEN = re.compile(r"<[/A-Za-z]")
# Another name for the same object: the browser also hands a script the
# global object as `frames`, `parent`, `top`, and `opener`, so a write aimed
# at one of those names is a write aimed at the `Boolean` the predicate
# reads. A host name counts as a whole word of its own, never as a property
# name, because `rect.top` is a value and not the window.
GLOBAL_HOSTS = (
    "globalThis", "window", "self", "global", "frames", "parent", "top", "opener",
)
GLOBAL_NAMES = (
    "Boolean", "String", "Number", "Object", "Array", "Set", "Map", "WeakMap", "WeakSet",
    "Reflect", "JSON", "Function", "Symbol", "Promise", "Proxy",
)
PROTOTYPE_REACH = re.compile(
    r"\.\s*prototype\b|__proto__|setPrototypeOf|getPrototypeOf"
    r"|Reflect\s*\.\s*(?:set|defineProperty|deleteProperty)"
    r"|Object\s*\.\s*(?:defineProperty|defineProperties|getOwnPropertyDescriptor"
    r"|getOwnPropertyNames|setPrototypeOf|getPrototypeOf)"
)
JS_BLANK = "\ufeff"
VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
})
CONDITION_ATTRIBUTE = re.compile(
    r"""v-(?:else-)?if\s*=\s*(?:"([^"]*)"|'([^']*)')|v-show\s*=\s*(?:"([^"]*)"|'([^']*)')"""
)
CONSTANT_CONDITION_NAMES = frozenset({
    "true", "false", "null", "undefined", "NaN", "Infinity", "Boolean", "Number",
    "String", "Object", "Array", "JSON", "Math", "BigInt", "Symbol", "Promise",
    "Reflect", "globalThis", "window", "self", "global", "document",
})
# A tag bound never to be visible carries no observable alert however its
# branches resolve, and the spellings that hide it are ordinary ones: the boolean
# `hidden` attribute, `v-show`, and a `style` binding that asks for
# `display: none`, `visibility: hidden`, or no opacity. The declaration is read
# from the bound value rather than from the attribute text, so the object
# spelling `:style="{ display: 'none' }"` and the casing a browser accepts both
# count.
HIDDEN_ATTRIBUTE = re.compile(r"(?<![:.\w-])hidden(?![\w-])", re.I)
# `:hidden="flag"` is the same declaration written as a binding: `hidden` is a
# boolean attribute, so a bound value that can be truthy hides the element, while
# a constant that renders nothing (`:hidden="false"`) shows it.
# `v-bind` used as an object (`v-bind="{ hidden: true }"`, `v-bind="attrs"`) or
# through a dynamic argument (`v-bind:[name]="true"`, `:[name]="true"`) hands the
# element an attribute set the template never names, and `hidden` or a hiding
# `style` may be any of them.  The fail-closed branch carries a fixed attribute
# set, so both forms are read as hiding what the tag shows.  Vue documents
# modifiers on the same bindings (`.prop`, `.attr`, `.camel`), and a modifier
# rides between the directive and its `=`, so `:hidden.attr="true"` and
# `v-bind.prop="{ hidden: true }"` are the same declaration spelled with one.
BINDING_MODIFIERS = r"(?:\.[\w-]+)*"
V_BIND_OPEN = re.compile(
    rf"""(?<![\w-])(?:v-bind{BINDING_MODIFIERS}\s*=|v-bind{BINDING_MODIFIERS}\s*:\s*\[|:{BINDING_MODIFIERS}\s*\[)""",
    re.I,
)
# `.attr` and `.camel` set the attribute rather than the property, and `hidden` is
# a boolean attribute whose mere presence hides the element, so a spelling that
# carries one of them hides whatever constant it holds - `:hidden.attr="false"`
# renders nothing even though `:hidden="false"` renders the tag.
HIDDEN_BINDING = re.compile(
    rf"""(?<![\w-])(?:v-bind:|:)\s*hidden(?P<modifiers>{BINDING_MODIFIERS})\s*=\s*"""
    r"""(?:"(?P<quoted>[^"]*)"|'(?P<single>[^']*)'|(?P<bare>[^\s"'>`=]+))""",
    re.I,
)
V_SHOW_BINDING = re.compile(r"\bv-show\s*=")
STYLE_BINDING = re.compile(
    rf"""(?<![\w-])(?P<directive>(?:v-bind)?:)?style(?P<modifiers>{BINDING_MODIFIERS})\s*=\s*"""
    r"""(?:"(?P<quoted>[^"]*)"|'(?P<single>[^']*)'|(?P<bare>[^\s"'>`=]+))""",
    re.I,
)
# A bound style value is an expression, and text an expression builds - joined
# with `+`, written as a template literal, or produced by a call such as
# `concat`, `replace`, `join` or `String.fromCharCode` - can spell a declaration
# no single fragment spells, so the value is refused rather than followed.  The
# reading is structural rather than a list of the operator spellings seen so
# far: it is asked of the value with its comments blanked and its literal
# contents blanked on top of them, and a call is any `(` left there - so
# `obj['concat'](':none')` and `obj/*c*/.concat(':none')` are calls, and neither
# a call nor an operator written inside a string or a comment is one.
STYLE_COMPOSITION = re.compile(r"[+`(]")
# `opacity` hides at any spelling of the number zero, and `visibility` hides at
# `collapse` as it does at `hidden`.
CSS_ZERO = r"[-+]?(?:0+(?:\.0*)?|\.0+)(?:[eE][-+]?[0-9]+)?%?"
# A declaration may spell its property name with quotes or as a key
# (`{ 'display': 'none' }`, `{ ['opacity']: 0 }`), and it compiles to the same
# style object either way.
HIDING_DECLARATION = re.compile(
    r"""(?:\[\s*)?["']?display["']?(?:\s*\])?\s*:\s*["']?\s*none\b"""
    r"""|(?:\[\s*)?["']?visibility["']?(?:\s*\])?\s*:\s*["']?\s*(?:hidden|collapse)\b"""
    r"""|(?:\[\s*)?["']?opacity["']?(?:\s*\])?\s*:\s*["']?\s*"""
    + CSS_ZERO
    + r"""["']?(?![\w.%-])""",
    re.I,
)
GLOBAL_REACH_CODE = (
    ("document.defaultView", r"\bdocument\s*\.\s*defaultView\b"),
    ("a constructor", r"\.\s*constructor\b"),
    ("a dynamic import", r"\bimport\s*\("),
    ("a timer that compiles text", r"\b(?:setTimeout|setInterval)\s*\("),
    # `Object.assign(host, ...)` puts a new value behind a global name as plainly
    # as an assignment does, and the name it takes may be any name for the
    # global object rather than only the four the host reading lists.
    ("an `Object.assign` write", r"\bObject\s*\.\s*assign\s*\("),
)
GLOBAL_REACH_KEYS = (
    "defaultView", "constructor", "__proto__", "prototype",
) + GLOBAL_NAMES + GLOBAL_HOSTS
COMPUTED_KEY_FAMILY = frozenset(GLOBAL_REACH_KEYS)
# A key does not have to be written at the bracket, nor as a bare name inside
# it. `const key = 'Bool' + 'ean'` followed by `host[key]` reaches the property
# the name spells, and inside the brackets the same key may be wrapped in
# parentheses, carry `!`, `as`, `satisfies` or an angle-bracket assertion, or be
# built by an operator (`(first ?? second)`).  So the reading starts from the
# brackets and reads the key's *content*: nesting is left to the inner access,
# and the closing bracket is left to the next reading rather than consumed so a
# chain of keys (`value[first][second]`, `value?.[first]?.[second]`) is read as
# one access per key.  Optional chaining
# reads the same property (`value?.[key]`), and every name the content reads is
# looked up among the bindings that can put a string behind it.
COMPUTED_KEY_ACCESS = re.compile(
    r"""(?:(?P<name>[A-Za-z_$][\w$]*)|(?P<close>[)\]]))(?:\s*\?\.)?\s*\[(?P<content>[^\[\]]*)(?=\])"""
)
ANGLE_ASSERTION = re.compile(r"^\s*<[^<>]*>")
KEY_IDENTIFIER = re.compile(r"(?<![.\w$])([A-Za-z_$][\w$]*)")
STRING_BINDING_SOURCES = (
    re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=;\n]*)?=\s*([^;]*)"),
    re.compile(r"(?<![\w$.\]])([A-Za-z_$][\w$]*)\s*=(?!=)\s*([^;]*)"),
)
# A name a script appends to, or destructures out of a value that spells
# strings, may hold a string the reading cannot spell out: `name += 'ean'` and
# the `||=` family build on the value the name already held, and
# `const { name } = { name: 'Boolean' }` binds a string the binding never
# writes out.
STRING_APPEND_SOURCES = (
    re.compile(r"(?<![\w$.\]])([A-Za-z_$][\w$]*)\s*(?:\+=|\|\|=|&&=|\?\?=)\s*([^;]*)"),
    re.compile(r"\b(?:const|let|var)\s*\{([^}]*)\}\s*[^=;\n]*=\s*([^;]*)"),
)
CONTINUATION_ENDINGS = ("+", ".", ",", "(", "[", "{", "=", "?", ":", "&&", "||", "??")
CONTINUATION_STARTINGS = ("+", ".", "?", ":", ")", "]", "}", "&&", "||", "??", "as ", "satisfies ")
TYPE_ASSERTION = re.compile(r"(?:^|\s)(?:as|satisfies)\s")
STRING_TERM = re.compile(r"""["'`]""")
# `gl\u006FbalThis` is `globalThis`: an identifier written with an escape is
# still that identifier, so the readings that answer with names rather than with
# offsets resolve the escapes before they match.
UNICODE_ESCAPE = re.compile(r"\\u\{([0-9A-Fa-f]{1,6})\}|\\u([0-9A-Fa-f]{4})|\\x([0-9A-Fa-f]{2})")
# The compiler reads an attribute value before it parses it, and the first thing
# it reads is the character reference: `'display&#58;none'` is `'display:none'`,
# with the colon spelled as a reference.  A numeric reference is read with or
# without its terminator, because the parser reads it that way; a named one is
# read from the names that spell a character this reading could meet, and a name
# the browser would leave as text is left as text here too.
CHARACTER_REFERENCE = re.compile(
    r"&(?:#(?P<decimal>[0-9]+)|#[xX](?P<hexadecimal>[0-9A-Fa-f]+))(?:;)?"
    r"|&(?P<named>[A-Za-z][A-Za-z0-9]*);"
)
NAMED_REFERENCE = {
    "amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'", "nbsp": "\u00a0",
    "colon": ":", "semi": ";", "num": "#", "percnt": "%", "sol": "/", "bsol": "\\",
    "quest": "?", "excl": "!", "ast": "*", "plus": "+", "comma": ",", "period": ".",
    "hyphen": "-", "lowbar": "_", "grave": "`", "tilde": "~", "dollar": "$",
    "lpar": "(", "rpar": ")", "lbrack": "[", "rbrack": "]", "lbrace": "{",
    "rbrace": "}", "equals": "=", "commat": "@", "Hat": "^", "vert": "|",
    "Tab": "\t", "NewLine": "\n",
}
# An escape in a literal is the character it spells: the numeric forms and the
# one-letter forms, and a backslash before a line break continues the line.
ESCAPE_SEQUENCE = re.compile(
    r"\\u\{(?P<point>[0-9A-Fa-f]{1,6})\}|\\u(?P<unicode>[0-9A-Fa-f]{4})"
    r"|\\x(?P<byte>[0-9A-Fa-f]{2})|\\\r?\n|\\(?P<simple>[tnrfvb0])"
)
SIMPLE_ESCAPES = {"t": "\t", "n": "\n", "r": "\r", "f": "\f", "v": "\v", "b": "\b", "0": "\0"}
# A browser reads a declaration as CSS reads it: comments are not part of it.
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
CONDITION_TOKEN = re.compile(
    r"""\s*(?:(?P<number>\d+(?:\.\d+)?)|(?P<string>"[^"]*"|'[^']*')"""
    r"""|(?P<name>[A-Za-z_$][\w$]*)|(?P<operator>===|!==|==|!=|&&|\|\||!|\(|\)|,))"""
)
CONDITION_ATOMS: dict[str, object] = {
    "true": True, "false": False, "null": None, "undefined": None,
    "NaN": float("nan"), "Infinity": float("inf"),
}
CONDITION_TRUTHY_NAMES = frozenset({
    "Boolean", "Number", "String", "Object", "Array", "JSON", "Math", "BigInt",
    "Symbol", "Promise", "Reflect", "globalThis", "window", "self", "global", "document",
})
NON_ACCESS_WORDS = frozenset({
    "return", "typeof", "case", "in", "of", "new", "delete", "void", "do", "else",
    "instanceof", "yield", "await", "throw",
})
REGEX_START_KEYWORDS = (
    "return", "typeof", "instanceof", "case", "in", "of", "delete", "void", "do",
    "else", "yield", "await", "new", "throw",
)
REGEX_START_CONTROL = ("if", "while", "for", "with", "switch", "catch")
PREDICATE_UNION_SOURCE = "PROFESSIONAL_COMPONENT_RENDERERS"
PREDICATE_TRIMMED = ".trim()"


def is_blank(char: str) -> bool:
    """The whitespace the JavaScript lexer skips, not just Python's."""
    return char.isspace() or char == JS_BLANK


def blank_literals(text: str, spans: list[tuple[int, int]]) -> str:
    """Erase literal contents so a marker quoted in code is not a marker."""
    blanked = list(text)
    for start, end in spans:
        for position in range(start, end):
            if blanked[position] != "\n":
                blanked[position] = " "
    return "".join(blanked)


def previous_word(blanked: list[str], index: int) -> str:
    """The identifier ending at or before `index`, if any."""
    return previous_identifier(blanked, index)[0]


def previous_identifier(blanked: list[str], index: int) -> tuple[str, int]:
    """The identifier ending at or before `index`, and the offset before it."""
    prefix = "".join(blanked[: index + 1]).rstrip()
    word = re.search(r"[A-Za-z_$][\w$]*$", prefix)
    if not word:
        return "", index
    return word.group(0), word.start() - 1


def matching_paren(blanked: list[str], index: int) -> int:
    """Index of the `(` that matches the `)` at `index`, or -1."""
    depth = 0
    position = index
    while position >= 0:
        char = blanked[position]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
            if depth == 0:
                return position
        position -= 1
    return -1


def regex_can_start(blanked: list[str], index: int) -> bool:
    """Whether a `/` at `index` opens a literal rather than dividing two values."""
    previous = index - 1
    while previous >= 0 and is_blank(blanked[previous]):
        previous -= 1
    if previous < 0:
        return True
    if (
        blanked[previous] in "+-*"
        and previous > 0
        and blanked[previous - 1] == blanked[previous]
    ):
        return False
    if blanked[previous] in REGEX_START_AFTER:
        return True
    if blanked[previous] == ")":
        opening = matching_paren(blanked, previous)
        if opening < 0:
            return False
        word, head = previous_identifier(blanked, opening - 1)
        if word == "await":
            word, head = previous_identifier(blanked, head)
        if word not in REGEX_START_CONTROL:
            return False
        while head >= 0 and is_blank(blanked[head]):
            head -= 1
        return head < 0 or blanked[head] not in ".?"
    return previous_word(blanked, previous) in REGEX_START_KEYWORDS


def scan_spans(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Blank comments and collect literal spans in one left-to-right pass.

    One pass matters: a `//` inside a string, or a quote inside a regular
    expression, must not desynchronise the walk.  Comments are blanked in place
    so every offset survives, and string, template and regular expression
    literals are spanned so their contents are never read as code.
    """
    blanked = list(text)
    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in STRING_LITERAL_QUOTES:
            start = index
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                    continue
                index += 1
                if text[index - 1] == char:
                    break
            spans.append((start, index))
            continue
        if char == "/" and not text.startswith(("//", "/*"), index) and regex_can_start(blanked, index):
            start = index
            index += 1
            in_class = False
            while index < len(text) and text[index] != "\n":
                current = text[index]
                if current == "\\":
                    index += 2
                    continue
                if current == "[":
                    in_class = True
                elif current == "]":
                    in_class = False
                index += 1
                if current == "/" and not in_class:
                    break
            spans.append((start, index))
            continue
        end = None
        if text.startswith("<!--", index):
            found = text.find("-->", index + 4)
            end = len(text) if found < 0 else found + 3
        elif text.startswith("/*", index):
            found = text.find("*/", index + 2)
            end = len(text) if found < 0 else found + 2
        elif text.startswith("//", index):
            found = text.find("\n", index)
            end = len(text) if found < 0 else found
        if end is None:
            index += 1
            continue
        for position in range(index, end):
            if text[position] != "\n":
                blanked[position] = " "
        index = end
    return "".join(blanked), spans


def without_comments(text: str) -> str:
    """The same walk with every comment blanked, so prose cannot satisfy a check."""
    return scan_spans(text)[0]


def _decode_reference(match: re.Match[str]) -> str:
    """The character a reference spells, or the reference itself when it spells none."""
    if match.group("named") is not None:
        return NAMED_REFERENCE.get(match.group("named"), match.group(0))
    base = 16 if match.group("hexadecimal") is not None else 10
    digits = match.group("hexadecimal") or match.group("decimal")
    try:
        return chr(int(digits, base))
    except (ValueError, OverflowError):
        return match.group(0)


def _decode_escape(match: re.Match[str]) -> str:
    """The character an escape spells, or nothing when it continues the line."""
    if match.group(0) in ("\\\n", "\\\r\n"):
        return ""
    if match.group("simple") is not None:
        return SIMPLE_ESCAPES[match.group("simple")]
    point = match.group("point") or match.group("unicode") or match.group("byte")
    try:
        return chr(int(point, 16))
    except (ValueError, OverflowError):
        return match.group(0)


def decoded_spellings(text: str) -> str:
    """The text a compiler reads: the references first, then the escapes.

    `\u0067lobalThis` is `globalThis`, and `'display&#58;none'` is
    `'display:none'`: both readings are the compiler's, so a spelling that
    reaches the DOM reaches this reading too.
    """
    text = CHARACTER_REFERENCE.sub(_decode_reference, text)
    text = ESCAPE_SEQUENCE.sub(_decode_escape, text)

    def decode(match: re.Match[str]) -> str:
        digits = "".join(group for group in match.groups() if group)
        try:
            return chr(int(digits, 16))
        except ValueError:
            return match.group(0)

    return UNICODE_ESCAPE.sub(decode, text)


def css_declaration_text(text: str) -> str:
    """The text a CSS reader reads: comments are not part of a declaration."""
    return re.sub(r"\s+", " ", CSS_COMMENT.sub("", text))


def outside_literals(text: str, spans: list[tuple[int, int]], index: int) -> bool:
    """Whether an offset sits in code rather than inside a string or a pattern."""
    return not any(start < index < end for start, end in spans)


def search_code(pattern: str, text: str, spans: list[tuple[int, int]]):
    """First match that starts in code, so a quoted marker is not an attribute."""
    for match in re.finditer(pattern, text):
        if outside_literals(text, spans, match.start()):
            return match
    return None


def comment_spans(text: str) -> list[tuple[int, int]]:
    """Spans of markup and code comments, so a comment cannot carry a tag."""
    spans: list[tuple[int, int]] = []
    position = 0
    while True:
        found = None
        for opening, terminator, terminator_length in (
            ("<!--", "-->", 3),
            ("/*", "*/", 2),
        ):
            candidate = text.find(opening, position)
            if candidate >= 0 and (found is None or candidate < found[0]):
                found = (candidate, terminator, terminator_length)
        if found is None:
            return spans
        start, terminator, terminator_length = found
        closing = text.find(terminator, start + 2)
        end = len(text) if closing < 0 else closing + terminator_length
        spans.append((start, end))
        position = end


def outside_spans(spans: list[tuple[int, int]], index: int) -> bool:
    """Whether an offset currently sits outside every excluded span."""
    return not any(start <= index < end for start, end in spans)


def script_block_spans(text: str, excluded: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Spans of the component's script blocks, found in the markup by position.

    A `<script` written inside a comment or an attribute value is not a script
    block, and a block without a closing tag is not one either.
    """
    spans: list[tuple[int, int]] = []
    opener = re.compile(r"<script\b")
    closer = re.compile(r"</script\s*>")
    position = 0
    while True:
        opening = opener.search(text, position)
        if opening is None:
            return spans
        if not outside_spans(excluded, opening.start()):
            position = opening.end()
            continue
        closing = closer.search(text, opening.end())
        if closing is None or not outside_spans(excluded, closing.start()):
            return spans
        spans.append((opening.start(), closing.end()))
        position = closing.end()


def root_template_span(text: str, excluded: list[tuple[int, int]]) -> tuple[int, int] | None:
    """Span of the root template block, closed by nesting depth rather than by a match.

    Reading the block by position is what keeps the two halves apart: a shortest
    match stops at the first inner `</template>`, so it would both drop the tail
    of the real block and accept a `<template>` written inside a script literal.
    """
    def excluded_at(index: int) -> bool:
        return any(start <= index < end for start, end in excluded)

    opener = re.compile(r"<template\b")
    closer = re.compile(r"</template\s*>")
    start = None
    position = 0
    while True:
        opening = opener.search(text, position)
        if opening is None:
            return None
        if not excluded_at(opening.start()):
            start = opening.start()
            break
        position = opening.end()
    depth = 0
    cursor = start
    while cursor < len(text):
        opening = opener.search(text, cursor)
        closing = closer.search(text, cursor)
        if (
            opening is not None
            and not excluded_at(opening.start())
            and (closing is None or opening.start() < closing.start())
        ):
            depth += 1
            cursor = opening.end()
            continue
        if closing is not None and not excluded_at(closing.start()):
            depth -= 1
            if depth == 0:
                return (start, closing.end())
            cursor = closing.end()
            continue
        if opening is None and closing is None:
            return None
        if opening is not None and (closing is None or opening.start() < closing.start()):
            cursor = opening.end()
        else:
            cursor = closing.end()
    return None


def attribute_value_spans(text: str) -> list[tuple[int, int]]:
    """Spans of quoted attribute values, so a marker written inside one is inert.

    Anchored on `=` so prose apostrophes are not read as opening a value.
    """
    spans: list[tuple[int, int]] = []
    for match in re.finditer(r"=\s*(\"[^\"]*\"|'[^']*')", text):
        spans.append((match.start(1) + 1, match.end(1) - 1))
    return spans


TAG_ATTRIBUTE_VALUE = re.compile(r"""=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>`=]+))""")


def attribute_text_spans(text: str) -> list[tuple[int, int]]:
    """Spans of every attribute value's text, quoted or bare.

    `hidden`, `v-show=…` and `style=…` read on a tag are declarations on that
    tag, so the same words written inside an attribute's *value* are that value's
    text and nothing else.  A quoted value is read before a bare one, because an
    `=` inside quotes would otherwise look like it opened a second value.
    """
    spans: list[tuple[int, int]] = []
    for match in TAG_ATTRIBUTE_VALUE.finditer(text):
        group = next(index for index in (1, 2, 3) if match.group(index) is not None)
        spans.append((match.start(group), match.end(group)))
    return spans


def matches_outside(pattern, text: str, spans: list[tuple[int, int]]):
    """Matches whose start sits outside every span, so a value's text is inert."""
    for match in pattern.finditer(text):
        if not any(start <= match.start() < end for start, end in spans):
            yield match


def search_outside(pattern: str, text: str, spans: list[tuple[int, int]]):
    """First match whose start sits outside every span, so a quoted value is inert."""
    for match in re.finditer(pattern, text):
        if not any(start <= match.start() < end for start, end in spans):
            return match
    return None


def tag_spans(text: str, value_spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Spans of markup tags, so an attribute name can be told from body text."""
    spans: list[tuple[int, int]] = []
    position = 0
    while True:
        opening = text.find("<", position)
        if opening < 0:
            return spans
        if TAG_OPEN.match(text, opening) is None:
            position = opening + 1
            continue
        cursor = opening
        while cursor < len(text) and text[cursor] != ">":
            enclosed = [end for start, end in value_spans if start <= cursor < end]
            cursor = max(enclosed) if enclosed else cursor + 1
        if cursor >= len(text):
            return spans
        spans.append((opening, cursor + 1))
        position = cursor + 1


def search_in_tag(pattern: str, text: str, tags: list[tuple[int, int]], values: list[tuple[int, int]]):
    """First match that is an attribute name inside a tag, not markup text or a value."""
    for match in re.finditer(pattern, text):
        index = match.start()
        if any(start <= index < end for start, end in values):
            continue
        if any(start <= index < end for start, end in tags):
            return match
    return None


def tags_carrying(
    text: str,
    tags: list[tuple[int, int]],
    values: list[tuple[int, int]],
    patterns: tuple[str, ...],
) -> list[tuple[int, int]]:
    """Tags on which every pattern holds as a binding, not as a quoted value."""
    return [
        tag
        for tag in tags
        if all(search_in_tag(pattern, text, [tag], values) is not None for pattern in patterns)
    ]


def tags_carrying_indexes(
    text: str,
    tags: list[tuple[int, int]],
    values: list[tuple[int, int]],
    patterns: tuple[str, ...],
) -> list[int]:
    """The indexes of the tags `tags_carrying` answers with.

    A shape parked in a dead subtree or on the wrong element satisfies
    `tags_carrying` while no render reaches it, so the callers need the index to
    ask where the tag actually sits.
    """
    return [
        index
        for index, tag in enumerate(tags)
        if all(search_in_tag(pattern, text, [tag], values) is not None for pattern in patterns)
    ]


def element_nesting(
    text: str, tags: list[tuple[int, int]]
) -> tuple[list[str], list[int | None], list[int]]:
    """The name, enclosing element and matching end tag of every tag.

    The checks ask whether a branch really sits in the subtree that renders the
    field list, which needs the element tree rather than the flat list of tags.
    """
    names: list[str] = []
    parents: list[int | None] = []
    closes: list[int] = []
    stack: list[int] = []
    for index, (start, end) in enumerate(tags):
        tag = text[start:end]
        closing = re.match(r"</\s*([A-Za-z][\w.-]*)", tag)
        opening = re.match(r"<\s*([A-Za-z][\w.-]*)", tag)
        resolved = closing or opening
        name = resolved.group(1) if resolved is not None else ""
        names.append(name)
        closes.append(index)
        if closing is not None:
            parents.append(None)
            for depth in range(len(stack) - 1, -1, -1):
                if names[stack[depth]] == name:
                    closes[stack[depth]] = index
                    parents[index] = stack[depth - 1] if depth else None
                    del stack[depth:]
                    break
            continue
        parents.append(stack[-1] if stack else None)
        if tag.rstrip().endswith("/>") or name.lower() in VOID_TAGS:
            continue
        stack.append(index)
    return names, parents, closes


def condition_tokens(value: str) -> list[tuple[str, str]] | None:
    """The condition's tokens, or None when it uses something this reading cannot follow."""
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(value):
        match = CONDITION_TOKEN.match(value, position)
        if match is None:
            return None
        kind = match.lastgroup or ""
        tokens.append((kind, match.group(kind)))
        position = match.end()
    return tokens


def condition_truthy(value: object) -> bool:
    """JavaScript truth for the values this reading holds, where `NaN` is falsy."""
    if isinstance(value, float) and value != value:
        return False
    return bool(value)


def condition_equal(left: object, right: object) -> bool:
    """Equality for the constants this reading holds, where `null` and `undefined` are one value."""
    if left is None or right is None:
        return left is None and right is None
    return left == right


class ConditionReader:
    """Reads a condition built only out of constants down to its truth value.

    The branch checks need to know whether a branch renders, and what renders is
    not written in one shape: `true`, `1`, and `'x'` render while `false`, `0`,
    `''`, and `!true` do not.  A token this reading cannot follow answers as
    unknown rather than as a constant, so a shape outside the model is never
    mistaken for one that renders nothing.
    """

    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens = tokens
        self.position = 0

    def peek(self) -> tuple[str, str]:
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return ("", "")

    def take(self) -> tuple[str, str]:
        token = self.peek()
        self.position += 1
        return token

    def read(self) -> tuple[bool, object]:
        return self.read_or()

    def read_or(self) -> tuple[bool, object]:
        known, value = self.read_and()
        while self.peek() == ("operator", "||"):
            self.take()
            other_known, other = self.read_and()
            known = known and other_known
            value = condition_truthy(value) or condition_truthy(other)
        return known, value

    def read_and(self) -> tuple[bool, object]:
        known, value = self.read_not()
        while self.peek() == ("operator", "&&"):
            self.take()
            other_known, other = self.read_not()
            known = known and other_known
            value = condition_truthy(value) and condition_truthy(other)
        return known, value

    def read_not(self) -> tuple[bool, object]:
        if self.peek() == ("operator", "!"):
            self.take()
            known, value = self.read_not()
            return known, not condition_truthy(value)
        return self.read_comparison()

    def read_comparison(self) -> tuple[bool, object]:
        known, value = self.read_atom()
        operator = self.peek()
        if operator in (
            ("operator", "==="), ("operator", "=="), ("operator", "!=="), ("operator", "!="),
        ):
            self.take()
            other_known, other = self.read_atom()
            if not (known and other_known):
                return False, False
            equal = condition_equal(value, other)
            return True, equal if operator[1] in ("===", "==") else not equal
        return known, value

    def read_atom(self) -> tuple[bool, object]:
        kind, text = self.take()
        if kind == "number":
            return True, float(text)
        if kind == "string":
            return True, len(text) > 2
        if kind == "name":
            if self.peek() == ("operator", "("):
                self.take()
                inner_known, inner = self.read_or()
                if self.peek() != ("operator", ")"):
                    return False, False
                self.take()
                if text == "Boolean" and inner_known:
                    return True, condition_truthy(inner)
                return False, False
            if text in CONDITION_ATOMS:
                return True, CONDITION_ATOMS[text]
            if text in CONDITION_TRUTHY_NAMES:
                return True, True
            return False, False
        if (kind, text) == ("operator", "("):
            known, value = self.read_or()
            if self.peek() != ("operator", ")"):
                return False, False
            self.take()
            return known, value
        return False, False


def constant_condition_truth(value: str) -> bool | None:
    """The truth of a condition built only from constants, or None when it is not one."""
    tokens = condition_tokens(value.strip())
    if not tokens:
        return None
    reader = ConditionReader(tokens)
    known, result = reader.read()
    if not known or reader.position != len(tokens):
        return None
    return condition_truthy(result)


def condition_is_live(value: str) -> bool:
    """Whether a branch condition can render anything at all.

    A condition built only out of constants (`false`, `0`, `!true`, `1 === 2`,
    `Boolean(false)`, `undefined`) reads as a branch and renders nothing, so the
    check is stated over what the condition evaluates to rather than over the
    spellings of a constant - which keeps `true`, a condition that does render,
    from being read as one of them.  A condition that keeps a name the template
    can vary is live by construction, and one this reading cannot follow is taken
    as dead, so the answer errs toward refusing a branch.
    """
    names = IDENTIFIER.findall(value)
    if any(name not in CONSTANT_CONDITION_NAMES for name in names):
        return True
    return constant_condition_truth(value) is True


def unreachable_tags(
    text: str, tags: list[tuple[int, int]], parents: list[int | None]
) -> list[bool]:
    """Tags whose own or inherited condition is a constant, so no render reaches them.

    A branch shape parked there satisfies a check while the field still falls
    back silently, so the fail-closed half has to ignore those tags.
    """
    blocked = [False] * len(tags)
    for index in range(len(tags)):
        cursor: int | None = index
        while cursor is not None:
            match = CONDITION_ATTRIBUTE.search(text[tags[cursor][0]:tags[cursor][1]])
            if match is not None:
                value = next(group for group in match.groups() if group is not None)
                if not condition_is_live(value):
                    blocked[index] = True
                    break
            cursor = parents[cursor]
    return blocked


def binding_modifiers(group: str | None) -> set[str]:
    """The modifiers a binding carries, lowercased: `.prop`, `.attr`, `.camel`."""
    return {part.lower() for part in re.findall(r"\.([\w-]+)", group or "")}


def strip_parentheses(text: str) -> str:
    """A parenthesized constant is that same constant: `(null)` is `null`."""
    value = text.strip()
    while len(value) > 1 and value.startswith("(") and value.endswith(")"):
        value = value[1:-1].strip()
    return value


def binding_value(match) -> str:
    """The text a binding's `=` declares, trimmed, or the empty string for none.

    One of the three spellings always participates, so the caller reads the empty
    string as "this spelling binds nothing" rather than as a missing group.
    """
    declared = next(
        (
            group
            for group in (match.group("quoted"), match.group("single"), match.group("bare"))
            if group is not None
        ),
        None,
    )
    return "" if declared is None else declared.strip()


def shows_nothing(text: str, tag: tuple[int, int]) -> bool:
    """Whether a tag is bound never to be visible, however its branches resolve.

    A tag whose attribute set the template does not name — `v-bind` as an object
    or through a dynamic argument — counts too, because the attributes it takes
    may hide it.
    """
    markup = text[tag[0]:tag[1]]
    values = attribute_text_spans(markup)
    if next(matches_outside(V_BIND_OPEN, markup, values), None) is not None:
        return True
    if next(matches_outside(HIDDEN_ATTRIBUTE, markup, values), None) is not None:
        return True
    for match in matches_outside(HIDDEN_BINDING, markup, values):
        declared = binding_value(match)
        if not declared:
            # An empty expression binds nothing at all, and Vue never sees a
            # value for it.
            continue
        modifiers = binding_modifiers(match.group("modifiers"))
        if "attr" in modifiers and "prop" not in modifiers:
            # `.attr` sets the attribute, and `hidden` is a boolean attribute: its
            # presence is the declaration, so every value but the two Vue uses to
            # remove it hides the tag, a parenthesized constant included.
            if strip_parentheses(decoded_spellings(declared)) not in {"null", "undefined"}:
                return True
            continue
        # Without `.attr` the binding sets the property, which reads its
        # truthiness - and a string is a value the template wrote, so it hides
        # whatever it holds: Vue turns even the empty string into `true` for a
        # boolean DOM property, and `:hidden.camel="`false`"` holds a string.
        # The constant is read through parentheses here as it is for `.attr`,
        # because `:hidden="('')"` is that same empty string.
        unwrapped = strip_parentheses(decoded_spellings(declared))
        if unwrapped[:1] in STRING_LITERAL_QUOTES or condition_is_live(unwrapped):
            return True
    if next(matches_outside(V_SHOW_BINDING, markup, values), None) is not None:
        return True
    for match in matches_outside(STYLE_BINDING, markup, values):
        declared = binding_value(match)
        if not declared:
            continue
        # `.prop` and `.attr` hand the value straight to `el.style` or to
        # `setAttribute`, which coerce it to a string instead of merging it: an
        # object becomes `[object Object]`, and arrays and a `toString` are joined
        # into text a browser parses.  Which of those a given literal does is not
        # read here, so every spelling is read as a stylesheet, and an object that
        # coerces to nothing is refused rather than trusted.
        # The value is read the way the template compiler reads it: an escape
        # inside a literal spells its character, so `'display:\u006eone'` is
        # `display:none` to the browser.
        declared = decoded_spellings(declared)
        if HIDING_DECLARATION.search(css_declaration_text(declared)) is not None:
            return True
        # Only a bound value is an expression: `style="width: calc(100% - 4px)"`
        # is markup, and the declaration it holds is the text it wrote, so the
        # composition reading is asked of the bindings alone.  A value that
        # composes its text is refused rather than followed, because the text it
        # builds is not in the source to read.
        bound = match.group("directive") is not None or bool(match.group("modifiers"))
        # The reading is asked of the value with its comments blanked and its
        # literal contents blanked on top of them: a comment cannot park an
        # operator or a `(` where the walk would not see it, `obj['concat'](…)`
        # is a call as plainly as `obj.concat(…)` is, and a backtick that opens
        # a template is read from the same blanked view.
        code, spans = scan_spans(declared)
        template = any(code[start] == "`" for start, _ in spans)
        if bound and (
            template or STYLE_COMPOSITION.search(blank_literals(code, spans)) is not None
        ):
            return True
    return False


def shows_nothing_with_ancestors(
    text: str, tags: list[tuple[int, int]], parents: list[int | None], index: int
) -> bool:
    """Whether a tag or any element enclosing it is bound never to be visible.

    A tag that shows nothing hides everything it contains, so the alert has to be
    read along the whole ancestor chain: a `hidden` or a `v-bind` written on the
    field row hides the fail-closed branch exactly as one written on the branch
    itself does.  The chain is the one `unreachable_tags` already walks, so an
    inherited condition and an inherited hiding attribute are read from the same
    elements.
    """
    cursor: int | None = index
    while cursor is not None:
        if shows_nothing(text, tags[cursor]):
            return True
        cursor = parents[cursor]
    return False


def enclosing_vfors(
    text: str, tags: list[tuple[int, int]], parents: list[int | None], index: int
) -> list[int]:
    """The elements that loop over data and enclose a tag, innermost first.

    The markers have to ride the innermost one — an element looping over
    something else above the field list is not the field list — and that loop has
    to be the only one the field renders under, so a wrapper cannot stand in for
    it.
    """
    found: list[int] = []
    cursor: int | None = index
    while cursor is not None:
        if re.search(r"\bv-for\s*=", text[tags[cursor][0]:tags[cursor][1]]) is not None:
            found.append(cursor)
        cursor = parents[cursor]
    return found


def loops_over_the_field_list(
    text: str,
    tags: list[tuple[int, int]],
    parents: list[int | None],
    index: int,
    fields: list[int],
) -> bool:
    """Whether a tag renders directly under the one loop that iterates the fields."""
    loops = enclosing_vfors(text, tags, parents, index)
    return len(loops) == 1 and loops[0] in fields


def vue_component_name(name: str) -> str:
    """The name Vue resolves a tag to: a kebab-case tag is its PascalCase import."""
    if "-" not in name:
        return name
    return "".join(part[:1].upper() + part[1:] for part in name.split("-"))


def vfor_source(text: str, tag: tuple[int, int]) -> str | None:
    """The list a `v-for` iterates, so an empty literal is not a field list.

    Both of Vue's spellings count, `in` and `of`: they iterate the same list.
    """
    match = re.search(r"""v-for\s*=\s*(?:"([^"]*)"|'([^']*)')""", text[tag[0]:tag[1]])
    if match is None:
        return None
    value = match.group(1) or match.group(2) or ""
    parts = re.split(r"\s+(?:in|of)\s+", value, maxsplit=1)
    return parts[1] if len(parts) == 2 else None


def resolve_specifier(relative: str, specifier: str) -> str:
    """The repo path a relative import names, without its extension."""
    parts: list[str] = []
    for part in (PurePosixPath(relative).parent / specifier).parts:
        if part == ".":
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


MODULE_EXTENSIONS = (".vue", ".ts", ".mts", ".cts", ".tsx", ".jsx", ".js")


def module_spellings(relative: str) -> tuple[str, ...]:
    """The spellings an import specifier may use to name this one file.

    A `.vue` import carries its extension and a `.ts` import usually does not,
    so a branch surface has to answer to both spellings or the strict module
    reading will quietly scan nothing at all.
    """
    for extension in MODULE_EXTENSIONS:
        if relative.endswith(extension):
            return (relative, relative[: -len(extension)])
    return (relative,)


def imported_modules(
    relative: str,
    text: str,
    spans: list[tuple[int, int]] | None = None,
) -> dict[str, dict[str, str]]:
    """Modules a module imports, and the local name each import binds.

    Read from code: a comment or a quoted sentence that spells an import is not
    an import, and it must not be able to make an unreachable branch count.  The
    value maps the bound name to the exported name, because a branch is reached
    under the bound name and has to be found under the exported one.
    """
    modules: dict[str, dict[str, str]] = {}
    for match in re.finditer(
        r"""import\s*(?:type\s+)?(?:([A-Za-z_$][\w$]*)\s*,?\s*)?(?:\{([^}]*)\})?\s*from\s*['"]([^'"]+)['"]"""
        r"""|(?:from|import)\s*['"]([^'"]+)['"]""",
        text,
    ):
        if spans is not None and not outside_spans(spans, match.start()):
            continue
        specifier = match.group(3) or match.group(4)
        if specifier is None or not specifier.startswith("."):
            continue
        bindings = modules.setdefault(resolve_specifier(relative, specifier), {})
        default = match.group(1)
        if default is not None:
            bindings[default] = "default"
        for binding in (match.group(2) or "").split(","):
            parts = [part.strip() for part in binding.split(" as ")]
            exported, local = parts[0], parts[-1]
            if re.fullmatch(r"[A-Za-z_$][\w$]*", exported) and re.fullmatch(r"[A-Za-z_$][\w$]*", local):
                bindings[local] = exported
    return modules


def template_branches(text: str, tags: list[tuple[int, int]]) -> list[tuple[int, str, str]]:
    """The index, element name and condition of every tag carrying a branch.

    The name is the one Vue resolves the tag to, so a kebab-case tag counts as
    the component it renders, and it is what makes a branch a *render* branch:
    the comparison a branch can reach only counts for the element that branch
    renders, so a comparison parked in a helper no render element owns is not a
    dispatch, and neither is one only a dead subtree mentions.
    """
    branches: list[tuple[int, str, str]] = []
    for index, (start, end) in enumerate(tags):
        tag = text[start:end]
        name = re.match(r"<\s*([A-Za-z][\w.-]*)", tag)
        condition = re.search(r"""v-(?:else-)?if\s*=\s*(?:"([^"]*)"|'([^']*)')""", tag)
        if name is None or condition is None:
            continue
        branches.append(
            (index, vue_component_name(name.group(1)), condition.group(1) or condition.group(2) or "")
        )
    return branches


def reached_names(code: str, names: set[str]) -> set[str]:
    """The names themselves, plus every identifier their function bodies reach."""
    reached = set(names)
    for name in sorted(names):
        body = function_body(code, f"function {name}(")
        if body is not None:
            reached.update(IDENTIFIER.findall(body))
    return reached


def call_arguments(text: str, callee: str) -> list[list[str]]:
    """Top-level argument lists of every `callee(...)` call, split outside quotes."""
    calls: list[list[str]] = []
    for match in re.finditer(rf"\b{callee}\s*\(", text):
        depth = 1
        nested = 1
        position = match.end()
        start = position
        parts: list[str] = []
        while position < len(text) and depth:
            char = text[position]
            if char in "([{":
                nested += 1
                if char == "(":
                    depth += 1
            elif char in ")]}":
                if char == ")":
                    depth -= 1
                    if depth == 0:
                        parts.append(text[start:position])
                        break
                nested -= 1
            elif char == "," and depth == 1 and nested == 1:
                parts.append(text[start:position])
                start = position + 1
            elif char in STRING_LITERAL_QUOTES:
                position += 1
                while position < len(text) and text[position] != char:
                    if text[position] == "\\":
                        position += 1
                    position += 1
            position += 1
        calls.append([part.strip() for part in parts])
    return calls


def rebound_globals(code: str) -> set[str]:
    """Engine globals the fail-closed half reads that the script can replace.

    The predicate reads `Boolean` and a `Set`, so every binding that can put a
    different value behind one of those names anywhere in the script disarms it
    at load time: reaching a name for the global object, a shadowing declaration,
    a reassignment, or an import that binds the same name.  The reach is read
    from the script's own identifiers, so an escape spelling counts as the name
    it resolves to and a property named `top` is not the window.  `eval` and
    `Function` compile fresh code and are reported as the same class of reach.
    """
    code = decoded_spellings(code)
    names = "|".join(GLOBAL_NAMES)
    found: set[str] = set()
    host = re.search(rf"(?<![\w$.])({'|'.join(GLOBAL_HOSTS)})\b", code)
    if host is not None:
        found.add(host.group(1))
    for pattern in (
        rf"\b(?:const|let|var|class|function)\s+({names})\b",
        rf"\b({names})\s*=(?!=)",
        r"\b(?:eval|Function)\b",
    ):
        found.update(re.findall(pattern, code))
    for clause in re.findall(r"\bimport\s*(?:type\s+)?\{([^}]*)\}", code):
        for binding in clause.split(","):
            binding = binding.strip()
            if not binding or binding.startswith("type "):
                continue
            local = binding.split(" as ")[-1].strip()
            if local in GLOBAL_NAMES:
                found.add(local)
    return found


def global_reach(code: str, keys: str) -> set[str]:
    """Routes from the section to the global object, read off either view of it.

    The predicate reads `Boolean` and a `Set`, so any expression that can put a
    different value behind one of those names at load time disarms it.  A
    constructor reached off a value, the window behind `document`, a dynamic
    import, and a global name written as a string key all do that as plainly as
    naming `globalThis`.  `code` is read with literals blanked and `keys` with
    them intact, so a quoted sentence is not mistaken for either.
    """
    code = decoded_spellings(code)
    keys = decoded_spellings(keys)
    found: set[str] = set()
    for label, pattern in GLOBAL_REACH_CODE:
        if re.search(pattern, code):
            found.add(label)
    for name in GLOBAL_REACH_KEYS:
        if re.search(rf"""[\[\s*["']{name}["']\s*\]""", keys):
            found.add(f"a computed key that names {name}")
    for spelling in computed_string_keys(keys):
        found.add(f"a computed key ({spelling})")
    return found


def string_literal_value(term: str) -> tuple[bool, str | None]:
    """Whether a term is a string literal, and the string it spells out.

    A template with an interpolation, or a literal carrying an escape, is a
    string this reading cannot spell out, so it answers as a string with no
    value rather than as something that is not a string.
    """
    text = term.strip()
    if len(text) < 2 or text[0] != text[-1] or text[0] not in STRING_LITERAL_QUOTES:
        return False, None
    body = text[1:-1]
    if "${" in body or "\\" in body:
        return True, None
    return True, body


def strip_outer_parens(text: str) -> str:
    """The expression without the parens that wrap all of it, since `('x')` is `'x'`."""
    while len(text) >= 2 and text[0] == "(" and text[-1] == ")":
        depth = 0
        position = 0
        wrapped = True
        while position < len(text):
            char = text[position]
            if char in STRING_LITERAL_QUOTES:
                position += 1
                while position < len(text):
                    if text[position] == "\\":
                        position += 1
                    elif text[position] == char:
                        break
                    position += 1
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and position != len(text) - 1:
                    wrapped = False
                    break
            position += 1
        if not wrapped or depth != 0:
            return text
        text = text[1:-1].strip()
    return text


def statement_initializer(expression: str) -> str:
    """An initializer cut at the first line that ends a statement rather than continuing it.

    A declaration is captured up to its semicolon, which may run past the
    initializer when a file omits one, so the capture is cut again at the first
    line whose predecessor does not end in an operator: `'default' +` continues
    onto the next line while `'x'` followed by another statement does not.
    """
    lines = expression.split("\n")
    kept = [lines[0]]
    for line in lines[1:]:
        continues = kept[-1].rstrip().endswith(CONTINUATION_ENDINGS)
        continues = continues or line.lstrip().startswith(CONTINUATION_STARTINGS)
        if not continues:
            break
        kept.append(line)
    return "\n".join(kept)


def top_level_sum_terms(expression: str) -> list[str] | None:
    """The terms of a `+` chain, or None when the expression is not one."""
    terms: list[str] = []
    start = 0
    depth = 0
    position = 0
    while position < len(expression):
        char = expression[position]
        if char in STRING_LITERAL_QUOTES:
            position += 1
            while position < len(expression):
                if expression[position] == "\\":
                    position += 1
                elif expression[position] == char:
                    break
                position += 1
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "+" and depth == 0:
            terms.append(expression[start:position])
            start = position + 1
        position += 1
    if depth != 0:
        return None
    terms.append(expression[start:])
    return terms


def strip_type_assertion(term: str) -> str:
    """The term without the type assertions written after it, since `'x' as T as U` is `'x'`.

    Assertions stack, so the strip repeats: taking only the last one would leave
    `'Boolean' as unknown` behind, which is not the string it spells.
    """
    text = term.strip()
    while True:
        spans = scan_spans(text)[1]
        assertion = next(
            (match for match in TYPE_ASSERTION.finditer(text) if outside_literals(text, spans, match.start())),
            None,
        )
        if assertion is None:
            return text
        stripped = text[: assertion.start()].strip()
        if len(stripped) == 0 or stripped == text:
            return text
        text = stripped


def string_expression_value(
    expression: str, known: dict[str, list[str | None]]
) -> tuple[bool, str | None]:
    """Whether an expression always yields a string, and which string when it is spelled out.

    A name may hold more than one string, because a script may bind it more than
    once: the reading answers with the one string when every binding agrees and
    with no value when they do not, so a key that is a string without being
    spelled out is still read as a string.
    """
    text = strip_outer_parens(expression.strip().rstrip(";").strip())
    if not text:
        return False, None
    if text.startswith("["):
        return (True, None) if STRING_TERM.search(text) is not None else (False, None)
    terms = top_level_sum_terms(text)
    if terms is None:
        return False, None
    if len(terms) > 1:
        value = ""
        for term in terms:
            is_string, spelled = string_expression_value(strip_type_assertion(term), known)
            if not is_string:
                return False, None
            if spelled is None:
                return True, None
            value += spelled
        return True, value
    term = strip_outer_parens(strip_type_assertion(strip_outer_parens(terms[0].strip())))
    literal, spelled = string_literal_value(term)
    if literal:
        return True, spelled
    head = IDENTIFIER.fullmatch(term)
    if head is not None:
        if term not in known:
            return False, None
        values = known[term]
        spelled_values = sorted({value for value in values if value is not None})
        if len(spelled_values) == 1 and None not in values:
            return True, spelled_values[0]
        return True, None
    picked = IDENTIFIER.match(term)
    if picked is not None and picked.group(0) in known:
        return True, None
    return False, None


def string_key_bindings(code: str) -> dict[str, list[str | None]]:
    """The names the script binds to a string, and every string each can hold.

    A key hidden behind a name reaches the same property as the same key written
    out, so the bracket is not where this check can start: the binding is.  Every
    binding of a name counts rather than the last one the text happens to hold,
    because the access may sit at any of them, and a name a script appends to
    with `+=` may hold a string the text does not spell out at all.
    """
    sources: dict[str, list[str]] = {}
    appended: set[str] = set()
    for pattern in STRING_BINDING_SOURCES:
        for name, expression in pattern.findall(code):
            sources.setdefault(name, []).append(statement_initializer(expression))
    for name, expression in STRING_APPEND_SOURCES[0].findall(code):
        if STRING_TERM.search(expression) is not None:
            appended.add(name)
    for pattern, expression in STRING_APPEND_SOURCES[1].findall(code):
        if STRING_TERM.search(expression) is None:
            continue
        appended.update(destructured_names(pattern))
    bindings: dict[str, list[str | None]] = {}
    names = set(sources) | appended
    for _ in range(len(names) + 1):
        changed = False
        for name in sorted(names):
            expressions = sources.get(name, [])
            values: list[str | None] = []
            for expression in expressions:
                is_string, value = string_expression_value(expression, bindings)
                if is_string and value not in values:
                    values.append(value)
            if name in appended and None not in values:
                values.append(None)
            if not values:
                if name in bindings:
                    del bindings[name]
                    changed = True
                continue
            if name not in bindings or bindings[name] != values:
                bindings[name] = values
                changed = True
        if not changed:
            break
    return bindings


def destructured_names(pattern: str) -> list[str]:
    """The names a destructuring pattern binds, with renames and defaults read.

    `const { k: gk } = …` binds `gk` rather than the `k` it is read from, and
    `const { gk: other } = …` binds nothing called `gk`; a rest element binds an
    object rather than a string, so it names nothing here.
    """
    names: list[str] = []
    for part in pattern.split(","):
        part = part.strip()
        if not part or part.startswith("..."):
            continue
        if ":" in part:
            part = part.split(":", 1)[1]
        part = part.split("=", 1)[0].strip()
        if IDENTIFIER.fullmatch(part):
            names.append(part)
    return names


def computed_string_keys(code: str) -> list[str]:
    """String-keyed accesses, whatever the quotes and however the key is built.

    `target['Boolean']` needed one spelling to be caught; the same key written
    with a template literal, concatenated out of two literals, or held in a name
    for the script to read reaches the same property, so the check is stated
    over the access and the binding behind it rather than over the key's text.
    """
    found: list[str] = []
    bindings = string_key_bindings(code)
    for match in COMPUTED_KEY_ACCESS.finditer(code):
        base = match.group("name")
        if base is not None and base in NON_ACCESS_WORDS:
            continue
        expression = strip_key_wrappers(match.group("content").strip())
        keys = [name for name in key_identifiers(expression) if name in bindings]
        if keys:
            for key in keys:
                values = bindings[key]
                named = sorted({value for value in values if value in COMPUTED_KEY_FAMILY})
                if named:
                    found.append(f"[{key}], a key the script holds as {', '.join(named)}")
                elif any(value is None for value in values):
                    found.append(f"[{key}], a key the script holds as a string it does not spell out")
            continue
        if expression.startswith(("'", '"', "`")):
            found.append(" ".join(match.group(0).split()))
    return found


def key_identifiers(expression: str) -> list[str]:
    """The names a key expression reads, with the tails of member reads left out."""
    spans = scan_spans(expression)[1]
    names: list[str] = []
    for match in KEY_IDENTIFIER.finditer(expression):
        if not outside_literals(expression, spans, match.start()):
            continue
        names.append(match.group(1))
    return names


def strip_key_wrappers(expression: str) -> str:
    """The key expression with its outer parentheses and assertions peeled off."""
    text = expression
    while True:
        stripped = ANGLE_ASSERTION.sub("", strip_type_assertion(strip_outer_parens(text).strip())).strip()
        if stripped == text:
            return text
        text = stripped


def renderer_surface(text: str, suffix: str) -> str:
    """Only a component's script carries branches; its markup text is not code."""
    if suffix != ".vue":
        return text
    blocks = script_block_spans(text, comment_spans(text) + attribute_value_spans(text))
    return "\n".join(text[start:end] for start, end in blocks)


def dispatched_renderers(
    text: str,
    within: list[tuple[int, int]] | None = None,
) -> set[str]:
    """Renderer names a branch really dispatches, not names written inside text.

    `within` holds the index spans of the function bodies a template branch can
    actually reach, so a comparison that only a dead sibling holds cannot stand
    in for a branch.  Offsets are read from text whose literals survive, while
    the spans come from the same text read with its literals blanked, which is
    why the two readings must keep one length.
    """
    code, literals = scan_spans(text)
    names: set[str] = set()
    for match in RENDERER_DISPATCH.finditer(code):
        operand_start = match.start(1) - 1
        if any(start < operand_start < end for start, end in literals):
            continue
        if within is not None and not any(start <= match.start() < end for start, end in within):
            continue
        names.add(match.group(1))
    return names


def function_body_span(text: str, signature: str) -> tuple[int, int] | None:
    """Index span of the first function carrying `signature`, balanced on braces.

    Read the text with its literals blanked: a brace written inside a string is
    not a brace, so it must not be able to move the closing offset.
    """
    start = text.find(signature)
    if start < 0:
        return None
    opening = text.find("{", start)
    if opening < 0:
        return None
    depth = 0
    for index in range(opening, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return (opening + 1, index)
    return None


def function_body(text: str, signature: str) -> str | None:
    """Body of the first function carrying `signature`, balanced on braces."""
    span = function_body_span(text, signature)
    return None if span is None else text[span[0]:span[1]]


def reachable_body_spans(text: str, names: set[str]) -> list[tuple[int, int]]:
    """Bodies of every named function this module declares, in declaration order."""
    spans: list[tuple[int, int]] = []
    for name in sorted(names):
        span = function_body_span(text, f"function {name}(")
        if span is not None:
            spans.append(span)
    return sorted(spans)


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    registry = read_text("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts")
    presenter = read_text("frontend/apps/web/src/app/presentation/contractFormPresenter.ts")
    renderer = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    canonical_renderer = read_text("frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts")
    renderer_exclusions = comment_spans(renderer) + attribute_value_spans(renderer)
    renderer_script_blocks = script_block_spans(renderer, renderer_exclusions)
    template_span = root_template_span(renderer, renderer_exclusions + renderer_script_blocks)
    renderer_script_blocks = [
        span
        for span in renderer_script_blocks
        if template_span is None or not template_span[0] <= span[0] < template_span[1]
    ]
    renderer_template_code = without_comments(
        "" if template_span is None else renderer[template_span[0]:template_span[1]]
    )
    renderer_template_spans = attribute_value_spans(renderer_template_code)
    renderer_template_tags = tag_spans(renderer_template_code, renderer_template_spans)
    renderer_template_names, renderer_template_parents, renderer_template_closes = element_nesting(
        renderer_template_code, renderer_template_tags
    )
    renderer_template_unreachable = unreachable_tags(
        renderer_template_code, renderer_template_tags, renderer_template_parents
    )
    # The field list is the element that carries the six markers on a real
    # `v-for` and that no constant condition hides: the field branches have to
    # render under it, and an element no render can reach cannot carry the
    # fail-closed contract on the field's behalf.
    field_iterators: list[int] = []
    for index in tags_carrying_indexes(
        renderer_template_code,
        renderer_template_tags,
        renderer_template_spans,
        SEMANTIC_BINDINGS + (r"\bv-for\s*=",),
    ):
        if renderer_template_unreachable[index]:
            continue
        if IDENTIFIER.search(vfor_source(renderer_template_code, renderer_template_tags[index]) or "") is None:
            continue
        field_iterators.append(index)
    renderer_script_raw, renderer_script_spans = scan_spans(
        "".join(renderer[start:end] for start, end in renderer_script_blocks)
    )
    renderer_script_code = blank_literals(renderer_script_raw, renderer_script_spans)
    # `renderer_script_raw` keeps its literals so a dispatch spelling survives;
    # `renderer_script_code` blanks them so prose cannot satisfy a shape check.
    # Imports are read from the script block alone: that half is JavaScript, so
    # an apostrophe in markup text cannot open a literal that swallows them.
    required_registration_fields = (
        "componentKey", "semanticType", "supportedFieldTypes", "supportedPresentationModes",
        "supportedRenderProfiles", "requiredCapabilities", "renderer", "rendererByFieldType", "fallback", "readiness",
    )
    for marker in required_registration_fields:
        if marker not in registry:
            failures.append(f"registry missing required field {marker}")
    for marker in (
        "PROFESSIONAL_COMPONENT_UNREGISTERED", "PROFESSIONAL_COMPONENT_FIELD_TYPE_MISSING", "PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH",
        "PROFESSIONAL_COMPONENT_PRESENTATION_MODE_MISMATCH", "PROFESSIONAL_COMPONENT_RENDER_PROFILE_MISMATCH",
        "PROFESSIONAL_COMPONENT_CAPABILITY_MISSING",
        "PROFESSIONAL_COMPONENT_CONTRACT_REGISTRY_MISSING", "PROFESSIONAL_COMPONENT_CONTRACT_VERSION_MISSING",
        "PROFESSIONAL_COMPONENT_CONTRACT_ADAPTER_MISSING",
    ):
        if marker not in registry:
            failures.append(f"registry missing fail-closed invariant {marker}")
    registry_code = without_comments(registry)
    union = re.search(
        r"PROFESSIONAL_COMPONENT_RENDERERS = Object\.freeze\(\[(.*?)\]\s*as const\)",
        registry_code,
        re.S,
    )
    if union is None:
        failures.append("registry does not declare one closed renderer union")
    else:
        renderer_names = re.findall(r"'([^']+)'", union.group(1))
        if not renderer_names:
            failures.append("registry renderer union is empty")
        if "renderer: ProfessionalComponentRenderer;" not in registry:
            failures.append("registry registration renderer is not typed by the closed union")
        if "Readonly<Record<string, ProfessionalComponentRenderer>>" not in registry:
            failures.append("registry rendererByFieldType is not typed by the closed union")
        if TYPE_DIRECTED_RENDERER not in renderer_names:
            failures.append(f"registry renderer union does not name the {TYPE_DIRECTED_RENDERER} sentinel")
        dispatched: set[str] = set()
        renderer_relative = "frontend/apps/web/src/components/template/FormSection.vue"
        imported = imported_modules(renderer_relative, renderer_script_raw, renderer_script_spans)
        imported_names: set[str] = set()
        for bindings in imported.values():
            imported_names.update(bindings)
        imported_by_file: dict[str, dict[str, str]] = {}
        for pattern in RENDERER_BRANCH_GLOBS:
            for branch_path in sorted(ROOT.glob(pattern)):
                relative = branch_path.relative_to(ROOT).as_posix()
                bindings: dict[str, str] = {}
                for spelling in module_spellings(relative):
                    bindings.update(imported.get(spelling, {}))
                if bindings:
                    imported_by_file[relative] = bindings
        if not imported_by_file:
            failures.append("no renderer branch surface was scanned")
        module_views: dict[str, tuple[str, str]] = {}
        for relative in sorted(imported_by_file):
            module_surface = renderer_surface(read_text(relative), PurePosixPath(relative).suffix)
            module_views[relative] = (module_surface, blank_literals(*scan_spans(module_surface)))
        branches = template_branches(renderer_template_code, renderer_template_tags)
        if not branches:
            failures.append("FormSection declares no renderer branch")
        for index, element, condition in branches:
            # A branch is a render branch only for an element the script imports,
            # and it dispatches only the renderer that element itself renders —
            # inside the field list, because a name parked where no field render
            # reaches it dispatches nothing.
            if element not in imported_names:
                continue
            reached = reached_names(renderer_script_code, set(IDENTIFIER.findall(condition)))
            found = dispatched_renderers(
                renderer_script_raw,
                reachable_body_spans(renderer_script_code, reached),
            )
            for relative, (module_surface, module_code) in module_views.items():
                exports = {
                    exported
                    for local, exported in imported_by_file[relative].items()
                    if local in reached
                }
                if exports:
                    found |= dispatched_renderers(
                        module_surface,
                        reachable_body_spans(module_code, exports),
                    )
            if element in found:
                if renderer_template_unreachable[index] or not loops_over_the_field_list(
                    renderer_template_code,
                    renderer_template_tags,
                    renderer_template_parents,
                    index,
                    field_iterators,
                ):
                    failures.append(
                        f"the {element} branch is not rendered by the field iterator element"
                    )
                    continue
                dispatched.add(element)
        for name in renderer_names:
            if name == TYPE_DIRECTED_RENDERER:
                continue
            if name not in dispatched:
                failures.append(f"no renderer branch dispatches {name}")
        registration_list = re.search(r"(?ms)^const REGISTRATIONS = \[(.*?)^\] as const;", registry_code)
        if registration_list is None:
            failures.append("registry does not declare one closed registration list")
        else:
            calls = call_arguments(registration_list.group(1), "registration")
            registry_blank = blank_literals(*scan_spans(registry_code))
            if len(re.findall(r"\bregistration\s*\(", registry_blank)) != len(calls) + 1:
                failures.append("registry registers a component outside its closed registration list")
            registered: set[str] = set()
            for arguments in calls:
                if len(arguments) < 5:
                    continue
                literal = re.fullmatch(r"'([^']*)'", arguments[4])
                if literal is None:
                    failures.append("registry registration names a renderer that is not a bare union member")
                    continue
                registered.add(literal.group(1))
            for name in sorted(registered):
                if name not in renderer_names:
                    failures.append(f"the closed renderer union does not name the registered renderer {name}")
                elif name != TYPE_DIRECTED_RENDERER and name not in dispatched:
                    failures.append(f"no renderer branch dispatches the registered renderer {name}")
            factory = function_body(registry_code, "function registration(")
            if factory is None:
                failures.append("registry does not declare one registration factory")
            else:
                for name in re.findall(r"\[\s*fieldType\s*,\s*'([^']+)'", factory):
                    if name not in renderer_names:
                        failures.append(f"the closed renderer union does not name the mapped renderer {name}")
        if "as unknown as" in registry_code:
            failures.append("registry launders a renderer through an unknown-typed cast")
    if search_in_tag(
        re.escape(FAIL_CLOSED_MARKER), renderer_template_code, renderer_template_tags, renderer_template_spans
    ) is None:
        failures.append("FormSection does not fail closed on an unregistered renderer")
    if search_in_tag(
        FAIL_CLOSED_MARKER_BINDING.pattern, renderer_template_code, renderer_template_tags, renderer_template_spans
    ) is None:
        failures.append("FormSection does not bind the fail-closed marker as an attribute")
    if search_in_tag(
        FAIL_CLOSED_BINDING.pattern, renderer_template_code, renderer_template_tags, renderer_template_spans
    ) is None:
        failures.append("FormSection does not bind the fail-closed branch to the unregistered-renderer predicate")
    fail_closed_tags = tags_carrying_indexes(
        renderer_template_code,
        renderer_template_tags,
        renderer_template_spans,
        (FAIL_CLOSED_BINDING.pattern, FAIL_CLOSED_MARKER_BINDING.pattern, ALERT_ROLE.pattern),
    )
    if not fail_closed_tags:
        failures.append(
            "FormSection does not carry the fail-closed branch, its marker, and a visible alert role on one element"
        )
    elif not any(
        not renderer_template_unreachable[index]
        and not shows_nothing_with_ancestors(
            renderer_template_code,
            renderer_template_tags,
            renderer_template_parents,
            index,
        )
        and loops_over_the_field_list(
            renderer_template_code,
            renderer_template_tags,
            renderer_template_parents,
            index,
            field_iterators,
        )
        for index in fail_closed_tags
    ):
        failures.append(
            "FormSection parks the fail-closed branch where no field render reaches it, so the field falls back silently"
        )
    if FAIL_CLOSED_PREDICATE not in renderer_script_code:
        failures.append("FormSection does not declare the unregistered-renderer predicate")
    else:
        predicate_body = function_body(renderer_script_code, FAIL_CLOSED_PREDICATE)
        if PREDICATE_TRIMMED in predicate_body:
            failures.append("FormSection fail-closed predicate trims the renderer instead of reading it as written")
        membership = FAIL_CLOSED_MEMBERSHIP.search(predicate_body)
        if membership is None:
            failures.append("FormSection fail-closed predicate does not test membership in a renderer set")
        else:
            name = re.escape(membership.group(1))
            declaration = re.search(
                rf"(?m)^\s*const\s+{name}\b[^=]*=\s*new Set\b[^(]*\(([^)]*)\)",
                renderer_script_code,
            )
            if declaration is None:
                failures.append("FormSection fail-closed predicate set is not a constant built from the closed renderer union")
            else:
                argument = declaration.group(1)
                if PREDICATE_UNION_SOURCE not in argument:
                    failures.append("FormSection fail-closed predicate set is not built from the closed renderer union")
                elif not re.fullmatch(
                    rf"\s*(?:\[\s*\.\.\.\s*)?{PREDICATE_UNION_SOURCE}(?:\s*\])?\s*",
                    argument,
                ):
                    failures.append("FormSection fail-closed predicate set spreads past the closed renderer union")
            if re.search(
                rf"\b{name}\b[^\n]*?\.\s*(?:add|delete|clear)\s*\(|Object\.assign\s*\(\s*{name}\b",
                renderer_script_code,
            ):
                failures.append("FormSection fail-closed predicate set is mutated after it is built")
            if len(re.findall(rf"\b{name}\b", renderer_script_code)) != 2:
                failures.append(
                    "FormSection fail-closed predicate set is referenced beyond its declaration and membership test"
                )
    rebound = rebound_globals(renderer_script_code)
    if rebound:
        failures.append(
            "FormSection rebinds the global "
            + ", ".join(sorted(rebound))
            + " that the fail-closed predicate reads, so the predicate can be disarmed at load time"
        )
    reach = global_reach(renderer_script_code, renderer_script_raw)
    if reach:
        failures.append(
            "FormSection reaches the global object at load time through "
            + ", ".join(sorted(reach))
            + ", so the fail-closed predicate can be disarmed at load time"
        )
    if PROTOTYPE_REACH.search(renderer_script_code):
        failures.append(
            "FormSection reaches a builtin prototype, so the fail-closed predicate can be patched at load time"
        )
    if "resolveContractProfessionalComponent({" not in presenter:
        failures.append("Presenter does not resolve every canonical field through the registry")
    if "componentResolution," not in presenter:
        failures.append("Presenter does not retain the registry resolution")
    for marker in SEMANTIC_MARKERS:
        if search_in_tag(
            rf":{marker}\s*=", renderer_template_code, renderer_template_tags, renderer_template_spans
        ) is None:
            failures.append(f"FormSection missing semantic marker {marker}")
    if not tags_carrying(
        renderer_template_code,
        renderer_template_tags,
        renderer_template_spans,
        SEMANTIC_BINDINGS + (r"\bv-for\s*=",),
    ):
        failures.append(
            "FormSection does not carry the six semantic markers together on the field iterator element"
        )
    elif not field_iterators:
        failures.append(
            "FormSection carries the six semantic markers on an element that renders no field list"
        )
    if "componentResolution" not in canonical_renderer:
        failures.append("canonical renderer does not forward registry resolution")
    forbidden = ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目")
    for marker in forbidden:
        if marker in registry:
            failures.append(f"registry contains forbidden product special case {marker}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_component_registry_guard] FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[frontend_professional_component_registry_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
