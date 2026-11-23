"""Lab-written formula language for calculation configurations (CALC-REQ-23, OQ-CALC-52).

A saved formula and an ad hoc formula use this one grammar, one parser, and
one evaluator. The text is data: it is tokenised, parsed into a tree, and the
tree is evaluated here in Python ``decimal``. No formula text is ever passed
to ``eval``, ``exec``, R, SQL, or any other interpreter.

Grammar (Marc, OQ-CALC-52 decisions)
------------------------------------
* Operators ``+ - * / ^``, parentheses, unary minus and plus. Unary minus
  binds tighter than ``^``, as in Excel, so ``-2^2`` is 4. ``^`` is
  left-associative, as in Excel. No ``%``, no ``&``, no text.
* Comparisons ``= <> < <= > >=`` (lowest precedence), ``TRUE`` and ``FALSE``.
* A name stands for one bound result. It is written bare (``mean_od``) or in
  brackets when it has spaces (``[Replicate 1]``). There is no range:
  ``A1:A3`` has nothing to span and is refused at save. A function that takes
  several results takes them one by one, or as a braced list
  (``{[R1], [R2], [R3]}``), which is a list of arguments and not a range.
* Functions: AVERAGE, SUM, MIN, MAX, COUNT, STDEV (divide by n-1), STDEV.P
  (divide by n), ABS, ROUND, SQRT, LOG10, LN, EXP, POWER, IF, AND, OR, NOT,
  LOOKUP, LINEST, FORECAST, TREND. Names are case-insensitive. A name outside
  this list is refused at save (Excel ``#NAME?``).
* No units. The formula layer does not check or convert the units of its
  terms (Marc, 2026-11-19, 7:21 PM ET).

Evaluation
----------
Arithmetic uses precision 50 and ``ROUND_HALF_EVEN`` (CALC-REQ-37). ROUND on
an exact .5 tie rounds to even, so ``ROUND(2.5, 0)`` is 2 (Excel gives 3).
Every error stops the formula and shows one Excel message: ``#DIV/0!``,
``#VALUE!``, ``#N/A``, or ``#NUM!``. A missing or blank input, and a term
bound to a knocked-out result, are ``#N/A``. IF evaluates only the branch it
takes, as Excel does.

Limits are fixed here so a formula cannot exhaust resources: text length,
nesting depth, node count, list length, exponent size, and decimal exponent
range. They are bounds on this evaluator, not assay values.

Nothing here reads the database, writes a result, or calls R. The stage
runner (S9) resolves each term to a decimal string, ``None`` (missing), or
``KNOCKED_OUT``, and calls :func:`evaluate_formula`.
"""
from __future__ import annotations

import bisect
import decimal
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence, Union

from app.services.calculation_catalog_decimal import format_decimal
from app.services.calculation_kat import DECIMAL_PRECISION, DECIMAL_ROUNDING

DIV_ZERO = "#DIV/0!"
VALUE_ERROR = "#VALUE!"
NOT_AVAILABLE = "#N/A"
NUM_ERROR = "#NUM!"
RUN_TIME_ERRORS = (DIV_ZERO, VALUE_ERROR, NOT_AVAILABLE, NUM_ERROR)

MAX_FORMULA_LENGTH = 2000
MAX_DEPTH = 32
MAX_NODES = 500
MAX_LIST_ITEMS = 100
MAX_EXPONENT = 1000
MAX_ROUND_DIGITS = 50
_EXP_ARGUMENT_BOUND = Decimal(10000)
_EMAX = 1000

MAX_NAME_LENGTH = 100


class KnockedOut:
    """A term bound to a result that is knocked out (CALC-REQ-27). Evaluates to ``#N/A``."""

    _instance: Optional["KnockedOut"] = None

    def __new__(cls) -> "KnockedOut":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "KNOCKED_OUT"


KNOCKED_OUT = KnockedOut()


class FormulaSyntaxError(ValueError):
    """The formula is refused at save. ``code`` is a stable machine code."""

    def __init__(self, code: str, message: str, position: Optional[int] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.position = position


class FormulaError(Exception):
    """A run-time formula error. ``text`` is the Excel message that is shown."""

    def __init__(self, text: str, detail: str = "") -> None:
        super().__init__(detail or text)
        self.text = text
        self.detail = detail


# ---- tokens ----------------------------------------------------------------

_NUMBER_RE = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
_IDENT_RE = re.compile(_IDENT)
_BARE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_RESERVED_NAMES = frozenset({"TRUE", "FALSE"})

# Characters Excel formulas allow that this language does not. Each one gets
# its own refusal so a lab admin sees why, instead of a bare "unexpected".
_REFUSED_CHARACTERS = {
    ":": ("formula_range_not_supported", "A range such as A1:A3 is not supported. Name each result."),
    "%": ("formula_token_not_allowed", "Percent (%) is not supported. Write /100."),
    "&": ("formula_token_not_allowed", "Text concatenation (&) is not supported."),
    '"': ("formula_token_not_allowed", "Text is not supported."),
    "'": ("formula_token_not_allowed", "Text and sheet names are not supported."),
    "!": ("formula_token_not_allowed", "External and sheet references are not supported."),
    "$": ("formula_token_not_allowed", "Cell references are not supported."),
    ";": ("formula_token_not_allowed", "Use a comma between arguments."),
    "@": ("formula_token_not_allowed", "The character @ is not supported."),
}


@dataclass(frozen=True)
class Token:
    kind: str  # num, name, bracket, op, eof
    text: str
    position: int


def tokenise(text: str) -> list[Token]:
    if not isinstance(text, str):
        raise FormulaSyntaxError("formula_syntax", "The formula must be text.")
    if _CONTROL_RE.search(text.replace("\n", " ").replace("\t", " ").replace("\r", " ")):
        raise FormulaSyntaxError("formula_token_not_allowed", "The formula has a control character.")
    if len(text) > MAX_FORMULA_LENGTH:
        raise FormulaSyntaxError(
            "formula_too_long", f"The formula is longer than {MAX_FORMULA_LENGTH} characters."
        )
    tokens: list[Token] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "[":
            end = text.find("]", i + 1)
            if end == -1:
                raise FormulaSyntaxError("formula_syntax", "A [name] is missing its closing ].", i)
            name = text[i + 1 : end].strip()
            if not name:
                raise FormulaSyntaxError("formula_syntax", "A [name] is empty.", i)
            if "[" in name:
                raise FormulaSyntaxError("formula_syntax", "A [name] cannot contain [.", i)
            tokens.append(Token("bracket", name, i))
            i = end + 1
            continue
        number = _NUMBER_RE.match(text, i)
        if number:
            tokens.append(Token("num", number.group(0), i))
            i = number.end()
            continue
        ident = _IDENT_RE.match(text, i)
        if ident:
            tokens.append(Token("name", ident.group(0), i))
            i = ident.end()
            continue
        two = text[i : i + 2]
        if two in ("<>", "<=", ">="):
            tokens.append(Token("op", two, i))
            i += 2
            continue
        if ch in "+-*/^(),{}=<>":
            tokens.append(Token("op", ch, i))
            i += 1
            continue
        if ch in _REFUSED_CHARACTERS:
            code, message = _REFUSED_CHARACTERS[ch]
            raise FormulaSyntaxError(code, message, i)
        raise FormulaSyntaxError(
            "formula_token_not_allowed", f"The character {ch!r} is not allowed.", i
        )
    tokens.append(Token("eof", "", n))
    return tokens


# ---- tree ------------------------------------------------------------------


@dataclass(frozen=True)
class Num:
    value: Decimal


@dataclass(frozen=True)
class Bool:
    value: bool


@dataclass(frozen=True)
class Ref:
    name: str
    position: int = 0


@dataclass(frozen=True)
class ListLit:
    items: tuple["Node", ...]


@dataclass(frozen=True)
class Unary:
    op: str
    operand: "Node"


@dataclass(frozen=True)
class Binary:
    op: str
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple["Node", ...]
    position: int = 0


Node = Union[Num, Bool, Ref, ListLit, Unary, Binary, Call]


@dataclass(frozen=True)
class FunctionSpec:
    min_args: int
    max_args: Optional[int]  # None means any number
    # Argument positions that must be a list (a braced list, or a call that
    # returns one). ``list_any`` means every argument may be a list that is
    # flattened (the aggregate functions).
    list_positions: tuple[int, ...] = ()
    list_any: bool = False
    # Positions where a list is allowed in addition to a scalar.
    list_ok_positions: tuple[int, ...] = ()


FORMULA_FUNCTIONS: Mapping[str, FunctionSpec] = {
    "AVERAGE": FunctionSpec(1, None, list_any=True),
    "SUM": FunctionSpec(1, None, list_any=True),
    "MIN": FunctionSpec(1, None, list_any=True),
    "MAX": FunctionSpec(1, None, list_any=True),
    "COUNT": FunctionSpec(1, None, list_any=True),
    "STDEV": FunctionSpec(1, None, list_any=True),
    "STDEV.P": FunctionSpec(1, None, list_any=True),
    "ABS": FunctionSpec(1, 1),
    "ROUND": FunctionSpec(2, 2),
    "SQRT": FunctionSpec(1, 1),
    "LOG10": FunctionSpec(1, 1),
    "LN": FunctionSpec(1, 1),
    "EXP": FunctionSpec(1, 1),
    "POWER": FunctionSpec(2, 2),
    "IF": FunctionSpec(3, 3),
    "AND": FunctionSpec(1, None),
    "OR": FunctionSpec(1, None),
    "NOT": FunctionSpec(1, 1),
    "LOOKUP": FunctionSpec(3, 3, list_positions=(1, 2)),
    "LINEST": FunctionSpec(2, 3, list_positions=(0, 1)),
    "FORECAST": FunctionSpec(3, 3, list_positions=(1, 2)),
    "TREND": FunctionSpec(2, 4, list_positions=(0, 1), list_ok_positions=(2,)),
}

_LIST_RETURNING = frozenset({"LINEST", "TREND"})


@dataclass(frozen=True)
class ParsedFormula:
    """A formula that passed the grammar. ``names`` are the terms it refers to."""

    text: str
    root: Node
    names: frozenset[str]
    functions: frozenset[str]
    node_count: int = 0


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0
        self.nodes = 0
        self.names: set[str] = set()
        self.functions: set[str] = set()

    # -- helpers
    def peek(self) -> Token:
        return self.tokens[self.index]

    def take(self) -> Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def is_op(self, *ops: str) -> bool:
        token = self.peek()
        return token.kind == "op" and token.text in ops

    def expect_op(self, op: str) -> Token:
        token = self.peek()
        if token.kind != "op" or token.text != op:
            found = token.text if token.kind != "eof" else "the end of the formula"
            raise FormulaSyntaxError(
                "formula_syntax", f"Expected {op!r} but found {found}.", token.position
            )
        return self.take()

    def count(self) -> None:
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise FormulaSyntaxError(
                "formula_too_complex", f"The formula has more than {MAX_NODES} parts."
            )

    # -- grammar
    def parse(self) -> Node:
        node = self.comparison(0)
        token = self.peek()
        if token.kind != "eof":
            raise FormulaSyntaxError(
                "formula_syntax", f"Unexpected {token.text!r}.", token.position
            )
        return node

    def comparison(self, depth: int) -> Node:
        left = self.additive(depth)
        while self.is_op("=", "<>", "<", "<=", ">", ">="):
            op = self.take().text
            right = self.additive(depth)
            self.count()
            left = Binary(op, left, right)
        return left

    def additive(self, depth: int) -> Node:
        left = self.multiplicative(depth)
        while self.is_op("+", "-"):
            op = self.take().text
            right = self.multiplicative(depth)
            self.count()
            left = Binary(op, left, right)
        return left

    def multiplicative(self, depth: int) -> Node:
        left = self.power(depth)
        while self.is_op("*", "/"):
            op = self.take().text
            right = self.power(depth)
            self.count()
            left = Binary(op, left, right)
        return left

    def power(self, depth: int) -> Node:
        left = self.unary(depth)
        while self.is_op("^"):
            self.take()
            right = self.unary(depth)
            self.count()
            left = Binary("^", left, right)
        return left

    def unary(self, depth: int) -> Node:
        if depth > MAX_DEPTH:
            raise FormulaSyntaxError(
                "formula_too_deep", f"The formula is nested more than {MAX_DEPTH} levels."
            )
        if self.is_op("-", "+"):
            op = self.take().text
            operand = self.unary(depth + 1)
            self.count()
            return Unary(op, operand)
        return self.primary(depth)

    def primary(self, depth: int) -> Node:
        token = self.peek()
        if token.kind == "num":
            self.take()
            self.count()
            return Num(Decimal(token.text))
        if token.kind == "bracket":
            self.take()
            self.count()
            self.names.add(token.text)
            return Ref(token.text, token.position)
        if token.kind == "name":
            self.take()
            if self.is_op("("):
                return self.call(token, depth)
            upper = token.text.upper()
            if upper in _RESERVED_NAMES:
                self.count()
                return Bool(upper == "TRUE")
            if "." in token.text:
                raise FormulaSyntaxError(
                    "formula_unknown_name",
                    f"{token.text!r} is not a result name. Write a name with a dot as [{token.text}].",
                    token.position,
                )
            self.count()
            self.names.add(token.text)
            return Ref(token.text, token.position)
        if token.kind == "op" and token.text == "(":
            self.take()
            inner = self.comparison(depth + 1)
            self.expect_op(")")
            return inner
        if token.kind == "op" and token.text == "{":
            return self.list_literal(depth)
        found = token.text if token.kind != "eof" else "the end of the formula"
        raise FormulaSyntaxError(
            "formula_syntax", f"Expected a value but found {found}.", token.position
        )

    def list_literal(self, depth: int) -> Node:
        open_token = self.take()
        items: list[Node] = []
        if self.is_op("}"):
            raise FormulaSyntaxError("formula_syntax", "A list needs at least one value.", open_token.position)
        while True:
            items.append(self.comparison(depth + 1))
            if len(items) > MAX_LIST_ITEMS:
                raise FormulaSyntaxError(
                    "formula_too_complex", f"A list has more than {MAX_LIST_ITEMS} values.", open_token.position
                )
            if self.is_op(","):
                self.take()
                continue
            break
        self.expect_op("}")
        self.count()
        return ListLit(tuple(items))

    def call(self, name_token: Token, depth: int) -> Node:
        name = name_token.text.upper()
        spec = FORMULA_FUNCTIONS.get(name)
        if spec is None:
            raise FormulaSyntaxError(
                "formula_unknown_function",
                f"{name_token.text!r} is not a formula function.",
                name_token.position,
            )
        self.take()  # (
        args: list[Node] = []
        if not self.is_op(")"):
            while True:
                args.append(self.comparison(depth + 1))
                if self.is_op(","):
                    self.take()
                    continue
                break
        self.expect_op(")")
        if len(args) < spec.min_args or (spec.max_args is not None and len(args) > spec.max_args):
            if spec.max_args is None:
                wanted = f"at least {spec.min_args}"
            elif spec.min_args == spec.max_args:
                wanted = str(spec.min_args)
            else:
                wanted = f"{spec.min_args} to {spec.max_args}"
            raise FormulaSyntaxError(
                "formula_arity",
                f"{name} takes {wanted} argument(s), not {len(args)}.",
                name_token.position,
            )
        self._check_list_positions(name, spec, args, name_token.position)
        self.count()
        self.functions.add(name)
        return Call(name, tuple(args), name_token.position)

    def _check_list_positions(
        self, name: str, spec: FunctionSpec, args: Sequence[Node], position: int
    ) -> None:
        for index, arg in enumerate(args):
            is_list_value = isinstance(arg, ListLit) or (
                isinstance(arg, Call) and arg.name in _LIST_RETURNING
            )
            if index in spec.list_positions:
                if not is_list_value:
                    raise FormulaSyntaxError(
                        "formula_list_expected",
                        f"Argument {index + 1} of {name} must be a list such as {{[R1], [R2]}}.",
                        position,
                    )
            elif is_list_value and not (spec.list_any or index in spec.list_ok_positions):
                raise FormulaSyntaxError(
                    "formula_list_misplaced",
                    f"Argument {index + 1} of {name} is one value, not a list.",
                    position,
                )
        # A list is not a number: it cannot be an operand.


def _reject_list_operands(node: Node) -> None:
    """A list or a list-returning call may only be a function argument."""
    if isinstance(node, (Unary,)):
        if _is_list_value(node.operand):
            raise FormulaSyntaxError("formula_list_misplaced", "A list cannot be used in arithmetic.")
        _reject_list_operands(node.operand)
    elif isinstance(node, Binary):
        for side in (node.left, node.right):
            if _is_list_value(side):
                raise FormulaSyntaxError(
                    "formula_list_misplaced", "A list cannot be used in arithmetic or a comparison."
                )
            _reject_list_operands(side)
    elif isinstance(node, Call):
        for arg in node.args:
            if isinstance(arg, ListLit):
                for item in arg.items:
                    if _is_list_value(item):
                        raise FormulaSyntaxError(
                            "formula_list_misplaced", "A list cannot contain a list."
                        )
                    _reject_list_operands(item)
            else:
                _reject_list_operands(arg)
    elif isinstance(node, ListLit):
        for item in node.items:
            _reject_list_operands(item)


def _is_list_value(node: Node) -> bool:
    return isinstance(node, ListLit) or (isinstance(node, Call) and node.name in _LIST_RETURNING)


def parse_formula(text: str) -> ParsedFormula:
    """Parse ``text``. Raises :class:`FormulaSyntaxError` for anything outside the grammar."""
    if not isinstance(text, str) or not text.strip():
        raise FormulaSyntaxError("formula_empty", "The formula is empty.")
    tokens = tokenise(text)
    parser = _Parser(tokens)
    root = parser.parse()
    if _is_list_value(root) and isinstance(root, ListLit):
        raise FormulaSyntaxError("formula_list_misplaced", "A formula cannot be a bare list.")
    _reject_list_operands(root)
    for name in parser.names:
        if len(name) > MAX_NAME_LENGTH:
            raise FormulaSyntaxError("formula_unknown_name", f"The name {name[:20]!r}... is too long.")
    return ParsedFormula(
        text=text,
        root=root,
        names=frozenset(parser.names),
        functions=frozenset(parser.functions),
        node_count=parser.nodes,
    )


def check_names(parsed: ParsedFormula, known: Sequence[str] | set[str] | frozenset[str]) -> None:
    """A name that is not bound is refused at save (Excel ``#NAME?``)."""
    known_set = set(known)
    unknown = sorted(name for name in parsed.names if name not in known_set)
    if unknown:
        listed = ", ".join(repr(name) for name in unknown)
        raise FormulaSyntaxError(
            "formula_unknown_name",
            f"Not bound to a result in this calculation: {listed}.",
        )


def term_name_error(name: Any) -> Optional[str]:
    """Why ``name`` cannot be a term name, or None."""
    if not isinstance(name, str) or not name.strip():
        return "A term name must be non-empty text."
    if name != name.strip():
        return "A term name cannot start or end with a space."
    if len(name) > MAX_NAME_LENGTH:
        return f"A term name is at most {MAX_NAME_LENGTH} characters."
    if _CONTROL_RE.search(name) or "[" in name or "]" in name:
        return "A term name cannot contain [, ], or a control character."
    if name.upper() in _RESERVED_NAMES:
        return "TRUE and FALSE are not term names."
    if name.upper() in FORMULA_FUNCTIONS and _BARE_NAME_RE.match(name):
        return "A term name cannot be a formula function name."
    return None


def render_term(name: str) -> str:
    """How ``name`` is written in formula text."""
    if _BARE_NAME_RE.match(name) and name.upper() not in _RESERVED_NAMES:
        return name
    return f"[{name}]"


# ---- evaluation ------------------------------------------------------------

Value = Union[Decimal, bool, tuple]


def _context() -> decimal.Context:
    return decimal.Context(
        prec=DECIMAL_PRECISION,
        rounding=DECIMAL_ROUNDING,
        Emax=_EMAX,
        Emin=-_EMAX,
        traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow],
    )


_PLAIN_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")


def _term_value(raw: Any, name: str) -> Decimal:
    """One term. A missing value or a knocked-out result is ``#N/A``; text that is not a number is ``#VALUE!``."""
    if raw is None or raw is KNOCKED_OUT:
        raise FormulaError(NOT_AVAILABLE, f"{name} has no value")
    if isinstance(raw, bool):
        raise FormulaError(VALUE_ERROR, f"{name} is not a number")
    if isinstance(raw, Decimal):
        if not raw.is_finite():
            raise FormulaError(VALUE_ERROR, f"{name} is not a number")
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if text == "" or text.upper() in ("N/A", "#N/A"):
            raise FormulaError(NOT_AVAILABLE, f"{name} has no value")
        if not _PLAIN_DECIMAL_RE.match(text):
            raise FormulaError(VALUE_ERROR, f"{name} is not a number")
        return Decimal(text)
    raise FormulaError(VALUE_ERROR, f"{name} is not a number")


def _number(value: Value, what: str = "a number") -> Decimal:
    if isinstance(value, bool) or isinstance(value, tuple) or not isinstance(value, Decimal):
        raise FormulaError(VALUE_ERROR, f"expected {what}")
    return value


def _boolean(value: Value) -> bool:
    if not isinstance(value, bool):
        raise FormulaError(VALUE_ERROR, "expected TRUE or FALSE")
    return value


def _flatten(values: Sequence[Value]) -> list[Decimal]:
    flat: list[Decimal] = []
    for value in values:
        if isinstance(value, tuple):
            flat.extend(_number(item) for item in value)
        else:
            flat.append(_number(value))
    return flat


def _vector(value: Value) -> list[Decimal]:
    if not isinstance(value, tuple):
        raise FormulaError(VALUE_ERROR, "expected a list")
    return [_number(item) for item in value]


def _power(base: Decimal, exponent: Decimal, ctx: decimal.Context) -> Decimal:
    if base == 0:
        if exponent == 0:
            raise FormulaError(NUM_ERROR, "0 to the power 0")
        if exponent < 0:
            raise FormulaError(DIV_ZERO, "0 to a negative power")
        return Decimal(0)
    if abs(exponent) > MAX_EXPONENT:
        raise FormulaError(NUM_ERROR, f"an exponent larger than {MAX_EXPONENT}")
    integral = exponent == exponent.to_integral_value()
    if not integral and base < 0:
        raise FormulaError(NUM_ERROR, "a negative number to a fractional power")
    return ctx.power(base, exponent)


def _round(value: Decimal, digits: Decimal, ctx: decimal.Context) -> Decimal:
    places = int(digits.to_integral_value(rounding=decimal.ROUND_DOWN))
    if abs(places) > MAX_ROUND_DIGITS:
        raise FormulaError(NUM_ERROR, "ROUND digits out of range")
    quantum = Decimal(1).scaleb(-places, context=ctx)
    return value.quantize(quantum, rounding=decimal.ROUND_HALF_EVEN, context=ctx)


def _mean(values: Sequence[Decimal], ctx: decimal.Context) -> Decimal:
    total = Decimal(0)
    for item in values:
        total = ctx.add(total, item)
    return ctx.divide(total, Decimal(len(values)))


def _sd(values: Sequence[Decimal], ddof: int, ctx: decimal.Context) -> Decimal:
    count = len(values)
    if count - ddof < 1:
        raise FormulaError(DIV_ZERO, "not enough values for the standard deviation")
    mean = _mean(values, ctx)
    total = Decimal(0)
    for item in values:
        diff = ctx.subtract(item, mean)
        total = ctx.add(total, ctx.multiply(diff, diff))
    return ctx.sqrt(ctx.divide(total, Decimal(count - ddof)))


def _line(
    ys: Sequence[Decimal], xs: Sequence[Decimal], through_origin_free: bool, ctx: decimal.Context
) -> tuple[Decimal, Decimal]:
    """Ordinary least squares of y on x, returned as (slope, intercept).

    ``through_origin_free`` is the Excel ``const`` argument. TRUE fits an
    intercept; FALSE forces it to 0. Fewer than two points is ``#NUM!``. No
    spread in x leaves the slope undefined and is ``#DIV/0!``.
    """
    if len(ys) != len(xs):
        raise FormulaError(VALUE_ERROR, "the y and x lists are not the same length")
    count = len(xs)
    if count < 2:
        raise FormulaError(NUM_ERROR, "a line needs at least two points")
    if through_origin_free:
        mean_x = _mean(xs, ctx)
        mean_y = _mean(ys, ctx)
        sxx = Decimal(0)
        sxy = Decimal(0)
        for x, y in zip(xs, ys):
            dx = ctx.subtract(x, mean_x)
            sxx = ctx.add(sxx, ctx.multiply(dx, dx))
            sxy = ctx.add(sxy, ctx.multiply(dx, ctx.subtract(y, mean_y)))
        if sxx == 0:
            raise FormulaError(DIV_ZERO, "the x values do not vary")
        slope = ctx.divide(sxy, sxx)
        intercept = ctx.subtract(mean_y, ctx.multiply(slope, mean_x))
        return slope, intercept
    sxx = Decimal(0)
    sxy = Decimal(0)
    for x, y in zip(xs, ys):
        sxx = ctx.add(sxx, ctx.multiply(x, x))
        sxy = ctx.add(sxy, ctx.multiply(x, y))
    if sxx == 0:
        raise FormulaError(DIV_ZERO, "the x values are all 0")
    return ctx.divide(sxy, sxx), Decimal(0)


class _Evaluator:
    def __init__(self, env: Mapping[str, Any]) -> None:
        self.env = env
        self.ctx = _context()

    def run(self, node: Node) -> Value:
        try:
            return self.eval(node)
        except decimal.DivisionByZero as exc:
            raise FormulaError(DIV_ZERO, "division by zero") from exc
        except (decimal.InvalidOperation, decimal.Overflow) as exc:
            raise FormulaError(NUM_ERROR, "the number is out of range") from exc

    def eval(self, node: Node) -> Value:
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Bool):
            return node.value
        if isinstance(node, Ref):
            return _term_value(self.env.get(node.name), node.name)
        if isinstance(node, ListLit):
            return tuple(_number(self.eval(item)) for item in node.items)
        if isinstance(node, Unary):
            operand = _number(self.eval(node.operand))
            return self.ctx.minus(operand) if node.op == "-" else self.ctx.plus(operand)
        if isinstance(node, Binary):
            return self.binary(node)
        if isinstance(node, Call):
            return self.call(node)
        raise FormulaError(VALUE_ERROR, "unknown formula part")

    def binary(self, node: Binary) -> Value:
        left = self.eval(node.left)
        right = self.eval(node.right)
        op = node.op
        if op in ("=", "<>"):
            if isinstance(left, bool) != isinstance(right, bool):
                raise FormulaError(VALUE_ERROR, "cannot compare a number with TRUE or FALSE")
            equal = left == right
            return equal if op == "=" else not equal
        a = _number(left)
        b = _number(right)
        if op == "+":
            return self.ctx.add(a, b)
        if op == "-":
            return self.ctx.subtract(a, b)
        if op == "*":
            return self.ctx.multiply(a, b)
        if op == "/":
            if b == 0:
                raise FormulaError(DIV_ZERO, "division by zero")
            return self.ctx.divide(a, b)
        if op == "^":
            return _power(a, b, self.ctx)
        if op == "<":
            return a < b
        if op == "<=":
            return a <= b
        if op == ">":
            return a > b
        if op == ">=":
            return a >= b
        raise FormulaError(VALUE_ERROR, f"unknown operator {op}")

    def call(self, node: Call) -> Value:
        name = node.name
        args = node.args
        ctx = self.ctx
        if name == "IF":
            condition = _boolean(self.eval(args[0]))
            return self.eval(args[1] if condition else args[2])
        values = [self.eval(arg) for arg in args]
        if name in ("AVERAGE", "SUM", "MIN", "MAX", "COUNT", "STDEV", "STDEV.P"):
            numbers = _flatten(values)
            if name == "COUNT":
                return Decimal(len(numbers))
            if not numbers:
                raise FormulaError(VALUE_ERROR, f"{name} has no numbers")
            if name == "SUM":
                total = Decimal(0)
                for item in numbers:
                    total = ctx.add(total, item)
                return total
            if name == "AVERAGE":
                return _mean(numbers, ctx)
            if name == "MIN":
                return min(numbers)
            if name == "MAX":
                return max(numbers)
            return _sd(numbers, 1 if name == "STDEV" else 0, ctx)
        if name == "ABS":
            return ctx.abs(_number(values[0]))
        if name == "ROUND":
            return _round(_number(values[0]), _number(values[1]), ctx)
        if name == "SQRT":
            x = _number(values[0])
            if x < 0:
                raise FormulaError(NUM_ERROR, "square root of a negative number")
            return ctx.sqrt(x)
        if name in ("LOG10", "LN"):
            x = _number(values[0])
            if x <= 0:
                raise FormulaError(NUM_ERROR, f"{name} of a number that is not greater than 0")
            return ctx.log10(x) if name == "LOG10" else ctx.ln(x)
        if name == "EXP":
            x = _number(values[0])
            if abs(x) > _EXP_ARGUMENT_BOUND:
                raise FormulaError(NUM_ERROR, "EXP argument out of range")
            return ctx.exp(x)
        if name == "POWER":
            return _power(_number(values[0]), _number(values[1]), ctx)
        if name == "AND":
            return all([_boolean(v) for v in values])
        if name == "OR":
            return any([_boolean(v) for v in values])
        if name == "NOT":
            return not _boolean(values[0])
        if name == "LOOKUP":
            target = _number(values[0])
            keys = _vector(values[1])
            results = _vector(values[2])
            if len(keys) != len(results):
                raise FormulaError(NOT_AVAILABLE, "the lookup and result lists are not the same length")
            index = bisect.bisect_right(keys, target) - 1
            if index < 0:
                raise FormulaError(NOT_AVAILABLE, "the value is below the first lookup item")
            return results[index]
        if name in ("LINEST", "FORECAST", "TREND"):
            return self.line_function(name, values)
        raise FormulaError(VALUE_ERROR, f"unknown function {name}")

    def line_function(self, name: str, values: Sequence[Value]) -> Value:
        ctx = self.ctx
        if name == "FORECAST":
            x = _number(values[0])
            ys = _vector(values[1])
            xs = _vector(values[2])
            slope, intercept = _line(ys, xs, True, ctx)
            return ctx.add(intercept, ctx.multiply(slope, x))
        ys = _vector(values[0])
        xs = _vector(values[1])
        if name == "LINEST":
            const = _boolean(values[2]) if len(values) > 2 else True
            slope, intercept = _line(ys, xs, const, ctx)
            return (slope, intercept)
        new_xs: list[Decimal] = list(xs)
        if len(values) > 2:
            raw_new = values[2]
            new_xs = _vector(raw_new) if isinstance(raw_new, tuple) else [_number(raw_new)]
        const = _boolean(values[3]) if len(values) > 3 else True
        slope, intercept = _line(ys, xs, const, ctx)
        return tuple(ctx.add(intercept, ctx.multiply(slope, x)) for x in new_xs)


def evaluate_formula(parsed: ParsedFormula, terms: Mapping[str, Any]) -> Value:
    """Evaluate ``parsed``. ``terms`` maps each name to a decimal string, ``Decimal``,
    ``None`` (missing), or ``KNOCKED_OUT``. Raises :class:`FormulaError` with the Excel
    message that is shown. The result is a ``Decimal``, a ``bool``, or a tuple of ``Decimal``.
    """
    return _Evaluator(terms).run(parsed.root)


@dataclass(frozen=True)
class FormulaOutcome:
    """The result of one formula run: a value, or the Excel message that stopped it."""

    value: Optional[Value] = None
    error: Optional[str] = None
    detail: str = ""

    @property
    def stopped(self) -> bool:
        return self.error is not None


def run_formula(parsed: ParsedFormula, terms: Mapping[str, Any]) -> FormulaOutcome:
    """Like :func:`evaluate_formula`, but an error is returned, not raised.

    Each formula runs on its own. An error here is that calculation's error
    only: it does not stop a different calculation (CALC-REQ-23).
    """
    try:
        return FormulaOutcome(value=evaluate_formula(parsed, terms))
    except FormulaError as exc:
        return FormulaOutcome(error=exc.text, detail=exc.detail)


def format_value(value: Value) -> str:
    """A result as plain text with no exponent (the stored form)."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, tuple):
        return "{" + ", ".join(format_value(item) for item in value) + "}"
    return format_decimal(value)
