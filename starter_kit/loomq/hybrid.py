"""Hybrid-QASM classical-block parser and deterministic RISC-V compiler."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence, Tuple, Union

from .qasm import Circuit, Gate, Measurement, parse_qasm


class HybridError(ValueError):
    """Raised for programs outside the published Hybrid-QASM grammar."""


@dataclass(frozen=True)
class Number:
    value: int


@dataclass(frozen=True)
class Reference:
    register: int


@dataclass(frozen=True)
class Arithmetic:
    operator: str
    left: "Expression"
    right: "Expression"


Expression = Union[Number, Reference, Arithmetic]


@dataclass(frozen=True)
class Assignment:
    target: int
    expression: Expression


@dataclass(frozen=True)
class Branch:
    operator: str
    left: Expression
    right: Expression
    when_true: List["Statement"]
    when_false: List["Statement"]


Statement = Union[Assignment, Branch]


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    position: int


_TOKEN = re.compile(
    r"(?P<SPACE>\s+)"
    r"|(?P<COMMENT>//[^\n]*|/\*.*?\*/)"
    r"|(?P<EQ>==)"
    r"|(?P<NE>!=)"
    r"|(?P<NUMBER>\d+)"
    r"|(?P<IDENT>[A-Za-z_]\w*)"
    r"|(?P<LBRACE>\{)|(?P<RBRACE>\})"
    r"|(?P<LPAREN>\()|(?P<RPAREN>\))"
    r"|(?P<LBRACKET>\[)|(?P<RBRACKET>\])"
    r"|(?P<ASSIGN>=)|(?P<PLUS>\+)|(?P<MINUS>-)"
    r"|(?P<SEMICOLON>;)",
    re.DOTALL,
)


def _tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    position = 0
    while position < len(source):
        match = _TOKEN.match(source, position)
        if not match:
            snippet = source[position : position + 20].splitlines()[0]
            raise HybridError(f"unexpected classical syntax near: {snippet}")
        kind = match.lastgroup
        assert kind is not None
        if kind not in {"SPACE", "COMMENT"}:
            tokens.append(Token(kind, match.group(), position))
        position = match.end()
    tokens.append(Token("EOF", "", len(source)))
    return tokens


class _Parser:
    def __init__(self, source: str, classical_bits: int):
        self.tokens = _tokenize(source)
        self.position = 0
        self.classical_bits = classical_bits

    @property
    def current(self) -> Token:
        return self.tokens[self.position]

    def advance(self) -> Token:
        token = self.current
        self.position += 1
        return token

    def accept(self, kind: str, value: str | None = None) -> Token | None:
        token = self.current
        if token.kind != kind or (value is not None and token.value != value):
            return None
        return self.advance()

    def expect(self, kind: str, value: str | None = None) -> Token:
        token = self.accept(kind, value)
        if token is None:
            expected = value if value is not None else kind
            raise HybridError(
                f"expected {expected} at classical offset {self.current.position}, "
                f"got {self.current.value or 'end of input'}"
            )
        return token

    def parse(self) -> List[Statement]:
        statements = self.statements("EOF")
        self.expect("EOF")
        return statements

    def statements(self, terminator: str) -> List[Statement]:
        statements: List[Statement] = []
        while self.current.kind != terminator:
            if self.current.kind == "EOF":
                raise HybridError("unterminated classical block")
            statements.append(self.statement())
        return statements

    def statement(self) -> Statement:
        if self.current.kind == "IDENT" and self.current.value == "if":
            return self.branch()
        return self.assignment()

    def assignment(self) -> Assignment:
        target = self.expect("IDENT").value
        if not re.fullmatch(r"r[1-9]", target):
            raise HybridError("assignment target must be r1..r9")
        self.expect("ASSIGN")
        expression = self.expression()
        self.expect("SEMICOLON")
        return Assignment(int(target[1:]), expression)

    def branch(self) -> Branch:
        self.expect("IDENT", "if")
        self.expect("LPAREN")
        left = self.expression()
        operator = self.current
        if operator.kind not in {"EQ", "NE"}:
            raise HybridError("if condition must use == or !=")
        self.advance()
        right = self.expression()
        self.expect("RPAREN")
        self.expect("LBRACE")
        when_true = self.statements("RBRACE")
        self.expect("RBRACE")
        when_false: List[Statement] = []
        if self.current.kind == "IDENT" and self.current.value == "else":
            self.advance()
            self.expect("LBRACE")
            when_false = self.statements("RBRACE")
            self.expect("RBRACE")
        return Branch(operator.value, left, right, when_true, when_false)

    def expression(self) -> Expression:
        expression = self.atom()
        while self.current.kind in {"PLUS", "MINUS"}:
            operator = self.advance().value
            expression = Arithmetic(operator, expression, self.atom())
        return expression

    def atom(self) -> Expression:
        if self.accept("MINUS"):
            value = int(self.expect("NUMBER").value)
            return Number(-value)
        number = self.accept("NUMBER")
        if number:
            return Number(int(number.value))
        if self.accept("LPAREN"):
            expression = self.expression()
            self.expect("RPAREN")
            return expression
        name = self.expect("IDENT").value
        if re.fullmatch(r"r[1-9]", name):
            return Reference(int(name[1:]))
        if name == "c":
            self.expect("LBRACKET")
            index = int(self.expect("NUMBER").value)
            self.expect("RBRACKET")
            if index >= self.classical_bits:
                raise HybridError("measurement index exceeds declared classical register")
            if index > 21:
                raise HybridError("measurement index exceeds available RISC-V registers")
            return Reference(10 + index)
        raise HybridError(f"unknown classical reference: {name}")


def _referenced_measurements(expression: Expression) -> set[int]:
    if isinstance(expression, Reference):
        return {expression.register} if expression.register >= 10 else set()
    if isinstance(expression, Arithmetic):
        return _referenced_measurements(expression.left) | _referenced_measurements(
            expression.right
        )
    return set()


def _statement_measurements(statement: Statement) -> set[int]:
    if isinstance(statement, Assignment):
        return _referenced_measurements(statement.expression)
    registers = _referenced_measurements(statement.left) | _referenced_measurements(
        statement.right
    )
    for child in statement.when_true + statement.when_false:
        registers |= _statement_measurements(child)
    return registers


def _references_register(expression: Expression, register: int) -> bool:
    if isinstance(expression, Reference):
        return expression.register == register
    if isinstance(expression, Arithmetic):
        return _references_register(expression.left, register) or _references_register(
            expression.right, register
        )
    return False


class _Compiler:
    def __init__(self, statements: Sequence[Statement]):
        self.lines: List[str] = ["# LoomQ Hybrid-QASM classical control"]
        self.label_counter = 0
        self.temporary_stack: List[int] = []
        reserved = set()
        for statement in statements:
            reserved |= _statement_measurements(statement)
        self.temporary_registers = [
            register for register in range(31, 9, -1) if register not in reserved
        ]

    def label(self, prefix: str) -> str:
        self.label_counter += 1
        return f"LOOMQ_{prefix}_{self.label_counter}"

    def acquire(self) -> int:
        depth = len(self.temporary_stack)
        if depth >= len(self.temporary_registers):
            raise HybridError("classical expression requires too many temporary registers")
        register = self.temporary_registers[depth]
        self.temporary_stack.append(register)
        return register

    def release(self, register: int) -> None:
        if not self.temporary_stack or self.temporary_stack[-1] != register:
            raise RuntimeError("temporary register release order is invalid")
        self.temporary_stack.pop()

    def expression(self, expression: Expression, target: int) -> None:
        if isinstance(expression, Number):
            self.lines.append(f"li x{target}, {expression.value}")
            return
        if isinstance(expression, Reference):
            if expression.register != target:
                self.lines.append(f"addi x{target}, x{expression.register}, 0")
            return
        self.expression(expression.left, target)
        right = self.acquire()
        self.expression(expression.right, right)
        instruction = "add" if expression.operator == "+" else "sub"
        self.lines.append(f"{instruction} x{target}, x{target}, x{right}")
        self.release(right)

    def direct_expression(self, expression: Expression, target: int) -> None:
        """Compile an expression into a destination absent from the input expression."""
        if isinstance(expression, Number):
            self.lines.append(f"li x{target}, {expression.value}")
            return
        if isinstance(expression, Reference):
            self.lines.append(f"addi x{target}, x{expression.register}, 0")
            return
        self.direct_expression(expression.left, target)
        if isinstance(expression.right, Number):
            immediate = (
                expression.right.value
                if expression.operator == "+"
                else -expression.right.value
            )
            self.lines.append(f"addi x{target}, x{target}, {immediate}")
            return
        if isinstance(expression.right, Reference):
            instruction = "add" if expression.operator == "+" else "sub"
            self.lines.append(
                f"{instruction} x{target}, x{target}, x{expression.right.register}"
            )
            return
        right = self.acquire()
        self.expression(expression.right, right)
        instruction = "add" if expression.operator == "+" else "sub"
        self.lines.append(f"{instruction} x{target}, x{target}, x{right}")
        self.release(right)

    def statement(self, statement: Statement) -> None:
        if isinstance(statement, Assignment):
            if not _references_register(statement.expression, statement.target):
                self.direct_expression(statement.expression, statement.target)
                return
            temporary = self.acquire()
            self.expression(statement.expression, temporary)
            self.lines.append(f"addi x{statement.target}, x{temporary}, 0")
            self.release(temporary)
            return

        false_label = self.label("ELSE")
        end_label = self.label("END")
        left = self.acquire()
        self.expression(statement.left, left)
        right = self.acquire()
        self.expression(statement.right, right)
        branch_instruction = "bne" if statement.operator == "==" else "beq"
        self.lines.append(f"{branch_instruction} x{left}, x{right}, {false_label}")
        self.release(right)
        self.release(left)
        for child in statement.when_true:
            self.statement(child)
        self.lines.append(f"j {end_label}")
        self.lines.append(f"{false_label}:")
        for child in statement.when_false:
            self.statement(child)
        self.lines.append(f"{end_label}:")

    def compile(self, statements: Sequence[Statement]) -> str:
        for statement in statements:
            self.statement(statement)
        return "\n".join(self.lines) + "\n"


def _mask_non_code(source: str) -> str:
    """Replace comments and quoted strings while retaining source offsets."""
    masked = list(source)
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        if state == "code":
            if source.startswith("//", index):
                masked[index : index + 2] = "  "
                index += 2
                state = "line_comment"
                continue
            if source.startswith("/*", index):
                masked[index : index + 2] = "  "
                index += 2
                state = "block_comment"
                continue
            if source[index] in {'"', "'"}:
                quote = source[index]
                masked[index] = " "
                index += 1
                state = "string"
                continue
            index += 1
            continue
        if state == "line_comment":
            if source[index] == "\n":
                state = "code"
            else:
                masked[index] = " "
            index += 1
            continue
        if state == "block_comment":
            if source.startswith("*/", index):
                masked[index : index + 2] = "  "
                index += 2
                state = "code"
            else:
                if source[index] != "\n":
                    masked[index] = " "
                index += 1
            continue
        masked[index] = " "
        if source[index] == "\\" and index + 1 < len(source):
            masked[index + 1] = " "
            index += 2
        elif source[index] == quote:
            index += 1
            state = "code"
        else:
            index += 1
    return "".join(masked)


def _split_classical(source: str) -> Tuple[str, str]:
    masked = _mask_non_code(source)
    match = re.search(r"\bclassical\s*\{", masked)
    if not match:
        raise HybridError("Hybrid-QASM requires one classical block")
    opening = masked.find("{", match.start())
    depth = 0
    closing = None
    for index in range(opening, len(source)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                closing = index
                break
    if closing is None:
        raise HybridError("unterminated classical block")
    remainder = source[: match.start()] + source[closing + 1 :]
    if re.search(r"\bclassical\s*\{", _mask_non_code(remainder)):
        raise HybridError("Hybrid-QASM supports exactly one classical block")
    return remainder, source[opening + 1 : closing]


def _quantum_operations(circuit: Circuit) -> List[str]:
    operations: List[str] = []
    for operation in circuit.operations:
        if isinstance(operation, Measurement):
            operations.append(f"measure q[{operation.qubit}] -> c[{operation.clbit}]")
            continue
        parameter = f"({operation.parameter!r})" if operation.parameter is not None else ""
        operands = ",".join(f"q[{index}]" for index in operation.qubits)
        operations.append(f"{operation.name}{parameter} {operands}")
    return operations


def compile_hybrid(source: str) -> Tuple[List[str], str]:
    quantum_source, classical_source = _split_classical(source)
    circuit = parse_qasm(quantum_source)
    quantum = _quantum_operations(circuit)
    statements = _Parser(classical_source, circuit.num_clbits).parse()
    assembly = _Compiler(statements).compile(statements)
    return quantum, assembly
