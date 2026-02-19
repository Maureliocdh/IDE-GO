from dataclasses import dataclass, field
from typing import List, Optional, Union, Any


# Base classes
class ASTNode:
    """Base class for all AST nodes"""
    pass


class Type(ASTNode):
    """Base class for all type nodes"""
    pass


class Statement(ASTNode):
    """Base class for all statement nodes"""
    pass


class Expression(ASTNode):
    """Base class for all expression nodes"""
    pass


# Top-level declarations
@dataclass
class Program(ASTNode):
    """Root node representing the entire Go program"""
    package: Optional['PackageDecl']
    imports: List['ImportDecl']
    declarations: List[Union['FuncDecl', 'VarDecl', 'ConstDecl', 'TypeDecl', 'StructDecl', 'InterfaceDecl']]


@dataclass
class PackageDecl(ASTNode):
    """Package declaration: package main"""
    name: str


@dataclass
class ImportDecl(ASTNode):
    """Import declaration: import "fmt" or import f "fmt" """
    path: str
    alias: Optional[str] = None


@dataclass
class VarDecl(Statement):
    """Variable declaration: var x int = 5"""
    name: str
    type_: Optional[Type]
    value: Optional[Expression]


@dataclass
class ConstDecl(Statement):
    """Constant declaration: const PI = 3.14"""
    name: str
    type_: Optional[Type]
    value: Expression


@dataclass
class TypeDecl(ASTNode):
    """Type declaration: type MyInt int"""
    name: str
    type_: Type


@dataclass
class Parameter(ASTNode):
    """Function parameter: name Type"""
    name: str
    type_: Type


@dataclass
class FuncDecl(ASTNode):
    """Function declaration: func add(a, b int) int { ... }"""
    name: str
    params: List[Parameter]
    returns: List[Type]
    body: Optional['Block']
    receiver: Optional[Parameter] = None


@dataclass
class StructDecl(ASTNode):
    """Struct declaration: struct { fields }"""
    name: str
    fields: List['StructField']


@dataclass
class StructField(ASTNode):
    """Struct field: Name Type `tag`"""
    name: str
    type_: Type
    tag: Optional[str] = None


@dataclass
class InterfaceDecl(ASTNode):
    """Interface declaration: interface { methods }"""
    name: str
    methods: List['InterfaceMethod']


@dataclass
class InterfaceMethod(ASTNode):
    """Interface method signature"""
    name: str
    signature: 'FuncDecl'


# Type nodes
@dataclass
class PrimitiveType(Type):
    """Primitive types: int, string, bool, float64, etc."""
    name: str


@dataclass
class PointerType(Type):
    """Pointer type: *T"""
    type_: Type


@dataclass
class ArrayType(Type):
    """Array type: [size]T"""
    size: Optional[Expression]
    type_: Type


@dataclass
class SliceType(Type):
    """Slice type: []T"""
    type_: Type


@dataclass
class MapType(Type):
    """Map type: map[KeyType]ValueType"""
    key_type: Type
    value_type: Type


@dataclass
class FuncType(Type):
    """Function type: func(params...) returnTypes..."""
    params: List[Type]
    returns: List[Type]


@dataclass
class ChannelType(Type):
    """Channel type: chan T, <-chan T, chan<- T"""
    type_: Type
    direction: str


@dataclass
class NamedType(Type):
    """Named type reference: CustomType"""
    name: str


@dataclass
class InterfaceType(Type):
    """Interface type: interface{}"""
    methods: Optional[List[InterfaceMethod]] = None


# Block
@dataclass
class Block(ASTNode):
    """Block of statements: { ... }"""
    statements: List[Statement]


# Statement nodes
@dataclass
class ExpressionStmt(Statement):
    """Expression used as statement: x++; add(1, 2)"""
    expr: Expression


@dataclass
class ReturnStmt(Statement):
    """Return statement: return x, err"""
    values: List[Expression]


@dataclass
class IfStmt(Statement):
    """If statement: if x > 0 { ... } else { ... }"""
    init: Optional[Statement]
    condition: Expression
    then_block: Block
    else_block: Optional[Union[Block, 'IfStmt']]


@dataclass
class ForStmt(Statement):
    """For loop: for init; condition; post { ... }"""
    init: Optional[Statement]
    condition: Optional[Expression]
    post: Optional[Statement]
    body: Block


@dataclass
class ForRangeStmt(Statement):
    """For range loop: for key, value := range iterable { ... }"""
    key: Optional[str]
    value: Optional[str]
    iterable: Expression
    body: Block


@dataclass
class SwitchStmt(Statement):
    """Switch statement: switch expr { case ... }"""
    init: Optional[Statement]
    expr: Optional[Expression]
    cases: List['CaseClause']


@dataclass
class CaseClause(Statement):
    """Case clause in switch: case value: statements"""
    values: List[Expression]
    statements: List[Statement]


@dataclass
class SelectStmt(Statement):
    """Select statement for channels: select { case ... }"""
    cases: List['SelectCase']


@dataclass
class SelectCase(Statement):
    """Case in select statement"""
    expr: Optional[Expression]
    statements: List[Statement]
    is_default: bool = False


@dataclass
class DeferStmt(Statement):
    """Defer statement: defer funcCall()"""
    call: Expression


@dataclass
class GoStmt(Statement):
    """Go statement (goroutine): go funcCall()"""
    call: Expression


@dataclass
class BreakStmt(Statement):
    """Break statement"""
    pass


@dataclass
class ContinueStmt(Statement):
    """Continue statement"""
    pass


@dataclass
class FallthroughStmt(Statement):
    """Fallthrough statement"""
    pass


@dataclass
class AssignStmt(Statement):
    """Assignment statement: x = 5 or x, y := 1, 2"""
    targets: List[Expression]
    values: List[Expression]
    operator: str = '='


@dataclass
class IncDecStmt(Statement):
    """Increment/Decrement: x++ or x--"""
    expr: Expression
    operator: str


# Expression nodes
@dataclass
class Literal(Expression):
    """Literal value: 42, 3.14, "hello", true"""
    value: str
    type_: str


@dataclass
class Identifier(Expression):
    """Identifier: variable name, function name, etc."""
    name: str


@dataclass
class BinaryOp(Expression):
    """Binary operation: a + b, a && b, etc."""
    left: Expression
    op: str
    right: Expression


@dataclass
class UnaryOp(Expression):
    """Unary operation: -x, !b, *ptr, &var, ++x, --x"""
    op: str
    operand: Expression


@dataclass
class CallExpr(Expression):
    """Function call: func(arg1, arg2)"""
    func: Expression
    args: List[Expression]


@dataclass
class IndexExpr(Expression):
    """Index access: arr[i] or map[key]"""
    expr: Expression
    index: Expression


@dataclass
class SliceExpr(Expression):
    """Slice expression: arr[start:end] or arr[start:end:cap]"""
    expr: Expression
    start: Optional[Expression]
    end: Optional[Expression]
    step: Optional[Expression]


@dataclass
class FieldExpr(Expression):
    """Field access: struct.field or package.Name"""
    expr: Expression
    field: str


@dataclass
class ArrayLiteral(Expression):
    """Array literal: [3]int{1, 2, 3} or []int{1, 2, 3}"""
    elements: List[Expression]
    type_: Optional[Type] = None


@dataclass
class MapLiteral(Expression):
    """Map literal: map[string]int{"a": 1, "b": 2}"""
    pairs: List[tuple]
    type_: Optional[Type] = None


@dataclass
class StructLiteral(Expression):
    """Struct literal: MyStruct{field1: value1, field2: value2}"""
    type_: str
    fields: List[tuple]


@dataclass
class TypeCast(Expression):
    """Type conversion/cast: int(x) or uint64(value)"""
    type_: Type
    expr: Expression


@dataclass
class TernaryOp(Expression):
    """Ternary operation: condition ? trueExpr : falseExpr"""
    condition: Expression
    true_expr: Expression
    false_expr: Expression


@dataclass
class MakeLiteral(Expression):
    """Make expression: make([]int, cap) or make(map[string]int)"""
    type_: Type
    len_: Optional[Expression] = None
    cap_: Optional[Expression] = None


@dataclass
class NewLiteral(Expression):
    """New expression: new(MyStruct)"""
    type_: Type


@dataclass
class CompositeLiteral(Expression):
    """Composite literals: T{...}"""
    type_: Type
    elems: List[tuple]


@dataclass
class LambdaExpr(Expression):
    """Lambda/function literal: func(x int) int { return x * 2 }"""
    params: List[Parameter]
    returns: List[Type]
    body: Block


@dataclass
class IsExpr(Expression):
    """Type assertion: value.(Type)"""
    expr: Expression
    type_: Type


@dataclass
class EllipsisExpr(Expression):
    """Ellipsis in function calls: func(args...)"""
    expr: Expression


@dataclass
class ChannelSendExpr(Expression):
    """Channel send: chan <- value"""
    chan: Expression
    value: Expression


@dataclass
class ChannelRecvExpr(Expression):
    """Channel receive: value := <- chan"""
    chan: Expression


# Scope / utility classes
@dataclass
class Scope:
    """Represents a scope for variable/function binding"""
    parent: Optional['Scope'] = None
    variables: dict = None
    functions: dict = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = {}
        if self.functions is None:
            self.functions = {}


@dataclass
class Position:
    """Source code position for error reporting"""
    line: int
    column: int
    file: str


@dataclass
class PositionedNode:
    """ASTNode with position information"""
    node: ASTNode
    pos: Position
