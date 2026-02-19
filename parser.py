from typing import List, Optional, Union
from lexer import Token, TokenType, Lexer

from ast_nodes import *
from ast_nodes import FieldExpr

# Parser
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def current_token(self) -> Optional[Token]:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]
    
    def peek_token(self, offset=1) -> Optional[Token]:
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return None
        return self.tokens[pos]
    
    def advance(self):
        self.pos += 1
    
    def expect(self, token_type: TokenType) -> Token:
        token = self.current_token()
        if not token or token.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {token.type if token else 'EOF'}")
        self.advance()
        return token
    
    def match(self, *token_types: TokenType) -> bool:
        token = self.current_token()
        return token and token.type in token_types
    
    def consume(self, token_type: TokenType) -> bool:
        if self.match(token_type):
            self.advance()
            return True
        return False
    
    def skip_newlines(self):
        """Skip all consecutive newline tokens"""
        while self.consume(TokenType.NEWLINE):
            pass
    
    def skip_statement_terminators(self):
        """Skip newlines and semicolons (statement terminators)"""
        while self.consume(TokenType.NEWLINE) or self.consume(TokenType.SEMICOLON):
            pass
    
    def parse(self) -> Program:
        self.skip_newlines()
        package = self.parse_package()
        imports = self.parse_imports()
        declarations = self.parse_declarations()
        return Program(package, imports, declarations)
    
    def parse_package(self) -> Optional[PackageDecl]:
        if self.consume(TokenType.PACKAGE):
            name = self.expect(TokenType.IDENTIFIER).value
            self.skip_newlines()
            return PackageDecl(name)
        return None
    
    def parse_imports(self) -> List[ImportDecl]:
        imports = []
        while self.match(TokenType.IMPORT):
            self.advance()
            if self.consume(TokenType.LPAREN):
                while not self.match(TokenType.RPAREN):
                    self.skip_newlines()
                    imports.append(self.parse_single_import())
                    self.skip_newlines()
                self.expect(TokenType.RPAREN)
            else:
                imports.append(self.parse_single_import())
            self.skip_newlines()
        return imports
    
    def parse_single_import(self) -> ImportDecl:
        alias = None
        if self.match(TokenType.IDENTIFIER):
            alias = self.current_token().value
            self.advance()
        path = self.expect(TokenType.STRING).value
        return ImportDecl(path, alias)
    
    def parse_declarations(self) -> List:
        declarations = []
        while not self.match(TokenType.EOF):
            self.skip_newlines()
            if self.match(TokenType.FUNC):
                declarations.append(self.parse_func_decl())
            elif self.match(TokenType.VAR):
                var_decl = self.parse_var_decl()
                if isinstance(var_decl, list):
                    declarations.extend(var_decl)
                else:
                    declarations.append(var_decl)
            elif self.match(TokenType.CONST):
                declarations.append(self.parse_const_decl())
            elif self.match(TokenType.TYPE):
                declarations.append(self.parse_type_decl())
            elif self.match(TokenType.STRUCT):
                declarations.append(self.parse_struct_decl())
            elif self.match(TokenType.INTERFACE):
                declarations.append(self.parse_interface_decl())
            else:
                break
            self.skip_newlines()
        return declarations
    
    def parse_func_decl(self) -> FuncDecl:
        self.expect(TokenType.FUNC)
        receiver = None
        self.skip_newlines()  # Handle newlines after 'func' keyword
        
        if self.match(TokenType.LPAREN):
            self.advance()
            if not self.match(TokenType.RPAREN):
                receiver = self.parse_parameter()
            self.expect(TokenType.RPAREN)
        
        name = self.expect(TokenType.IDENTIFIER).value
        self.skip_newlines()  # Handle newlines before parameters
        self.expect(TokenType.LPAREN)
        params = self.parse_parameters()
        self.expect(TokenType.RPAREN)
        self.skip_newlines()  # Handle newlines after parameters
        
        returns = []
        if self.match(TokenType.LPAREN):
            self.advance()
            returns = self.parse_types()
            self.expect(TokenType.RPAREN)
        elif not self.match(TokenType.LBRACE, TokenType.SEMICOLON, TokenType.NEWLINE):
            returns = [self.parse_type()]
        
        body = None
        self.skip_newlines()  # Handle newlines before function body
        if self.match(TokenType.LBRACE):
            body = self.parse_block()
        
        self.skip_newlines()
        return FuncDecl(name, params, returns, body, receiver)
    
    def parse_parameters(self) -> List[Parameter]:
        params = []
        while not self.match(TokenType.RPAREN):
            # Collect identifiers separated by commas
            identifiers = [self.expect(TokenType.IDENTIFIER).value]
            
            # Keep collecting while we see comma followed by identifier
            while self.consume(TokenType.COMMA) and self.match(TokenType.IDENTIFIER):
                identifiers.append(self.current_token().value)
                self.advance()
            
            # At this point we either:
            # 1. Hit end of params (RPAREN) - shouldn't happen, would mean no type
            # 2. Hit a non-identifier after comma - that's the start of the type
            # 3. Exhausted commas - next should be the type
            
            # If we stopped because of a non-identifier token after a comma,
            # we need to back up because that's part of the type
            # Actually, no - if we consumed a comma in the while condition but
            # didn't match IDENTIFIER, the comma is still consumed but we didn't
            # advance past anything after it.
            
            # If there's only one identifier and no comma was consumed,
            # we need to check if this identifier is actually a name or a type
            # For simplicity, assume the pattern is always: name(s) then type
            # So if we have multiple identifiers, all but the last are names, 
            # and we still need to parse the type
            # If we have one identifier, it's a name and we need to parse the type
            
            # Actually, let's use a different strategy:
            # The type is whatever comes after the last name
            # Names are identifiers that are followed by commas or by a type
            # So: parse identifier, if it's followed by a comma, it's a name
            # Keep doing this, then parse the type
            
            # Simpler: After collecting ids with commas, parse a type
            # The type might be a simple identifier (which we see as the current token)
            # or a complex type (array, map, etc.)
            
            type_ = self.parse_type()
            
            # Create parameters for all identifier names with this type
            for name in identifiers:
                params.append(Parameter(name, type_))
            
            # After parsing a parameter group, check  for comma before next group
            if not self.consume(TokenType.COMMA):
                break
        return params
    
    def parse_var_decl(self) -> Union[VarDecl, List[VarDecl]]:
        """Parse var declaration: var x int or var a, b int = 1, 2"""
        self.expect(TokenType.VAR)
        
        # Parse first variable name
        names = [self.expect(TokenType.IDENTIFIER).value]
        
        # Check for multiple variables: var a, b ...
        while self.consume(TokenType.COMMA):
            names.append(self.expect(TokenType.IDENTIFIER).value)
        
        type_ = None
        values = []
        
        # Parse optional type if present
        if self.match(TokenType.IDENTIFIER, TokenType.STAR, TokenType.LBRACKET, TokenType.MAP, TokenType.CHAN, TokenType.FUNC, TokenType.INTERFACE):
            type_ = self.parse_type()
        
        # Parse optional value assignment
        if self.consume(TokenType.ASSIGN):
            values.append(self.parse_expression())
            while self.consume(TokenType.COMMA):
                values.append(self.parse_expression())
        
        self.skip_statement_terminators()
        
        # If multiple variables, create separate VarDecl nodes
        if len(names) > 1:
            var_decls = []
            for i, name in enumerate(names):
                value = values[i] if i < len(values) else (values[0] if values else None)
                var_decls.append(VarDecl(name, type_, value))
            return var_decls
        else:
            return VarDecl(names[0], type_, values[0] if values else None)
    
    def parse_var_decl_stmt(self) -> Union[VarDecl, Block]:
        """Parse var declaration as a statement inside a function block"""
        # Parse first variable name
        names = [self.expect(TokenType.IDENTIFIER).value]
        
        # Check for multiple variables: var a, b ...
        while self.consume(TokenType.COMMA):
            names.append(self.expect(TokenType.IDENTIFIER).value)
        
        type_ = None
        values = []
        
        # Parse optional type if present
        if self.match(TokenType.IDENTIFIER, TokenType.STAR, TokenType.LBRACKET, TokenType.MAP, TokenType.CHAN, TokenType.FUNC, TokenType.INTERFACE):
            type_ = self.parse_type()
        
        # Parse optional value assignment
        if self.consume(TokenType.ASSIGN):
            values.append(self.parse_expression())
            while self.consume(TokenType.COMMA):
                values.append(self.parse_expression())
        
        self.skip_statement_terminators()
        
        # If multiple variables, convert to AssignStmt with short := operator style handling
        if len(names) > 1:
            # Create an assignment statement that assigns multiple values
            targets = [Identifier(name) for name in names]
            # If we have fewer values than targets, use nil for missing ones
            if not values:
                values = [Literal("nil", TokenType.NIL) for _ in names]
            return AssignStmt(targets, values, ":=")
        else:
            return VarDecl(names[0], type_, values[0] if values else None)
    
    def parse_const_decl_stmt(self) -> ConstDecl:
        """Parse const declaration as a statement inside a function block"""
        name = self.expect(TokenType.IDENTIFIER).value
        type_ = None
        
        if self.match(TokenType.IDENTIFIER, TokenType.STAR, TokenType.LBRACKET, TokenType.MAP, TokenType.CHAN):
            type_ = self.parse_type()
        
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.skip_statement_terminators()
        return ConstDecl(name, type_, value)
    
    def parse_const_decl(self) -> ConstDecl:
        self.expect(TokenType.CONST)
        name = self.expect(TokenType.IDENTIFIER).value
        type_ = None
        
        if self.match(TokenType.IDENTIFIER, TokenType.STAR, TokenType.LBRACKET, TokenType.MAP, TokenType.CHAN):
            type_ = self.parse_type()
        
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.skip_statement_terminators()
        return ConstDecl(name, type_, value)
    
    def parse_type_decl(self) -> TypeDecl:
        self.expect(TokenType.TYPE)
        name = self.expect(TokenType.IDENTIFIER).value
        type_ = self.parse_type()
        self.skip_newlines()
        return TypeDecl(name, type_)
    
    def parse_struct_decl(self) -> StructDecl:
        self.expect(TokenType.STRUCT)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LBRACE)
        fields = []
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.IDENTIFIER):
                field_name = self.current_token().value
                self.advance()
                field_type = self.parse_type()
                tag = None
                if self.match(TokenType.STRING):
                    tag = self.current_token().value
                    self.advance()
                fields.append(StructField(field_name, field_type, tag))
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        self.skip_newlines()
        return StructDecl(name, fields)
    
    def parse_interface_decl(self) -> InterfaceDecl:
        self.expect(TokenType.INTERFACE)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LBRACE)
        methods = []
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.IDENTIFIER):
                method_name = self.current_token().value
                self.advance()
                self.expect(TokenType.LPAREN)
                params = self.parse_parameters()
                self.expect(TokenType.RPAREN)
                returns = []
                if self.match(TokenType.LPAREN):
                    self.advance()
                    returns = self.parse_types()
                    self.expect(TokenType.RPAREN)
                elif not self.match(TokenType.RBRACE, TokenType.NEWLINE):
                    returns = [self.parse_type()]
                methods.append(InterfaceMethod(method_name, FuncDecl(method_name, params, returns, None)))
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        self.skip_newlines()
        return InterfaceDecl(name, methods)
    
    def parse_type(self) -> Type:
        if self.consume(TokenType.FUNC):
            # Function type: func(params) returns
            # Params can be just types or name+type pairs
            self.expect(TokenType.LPAREN)
            param_types = []
            while not self.match(TokenType.RPAREN):
                # Parameter can be: "name type" or just "type"
                # Try to detect if there's a name by checking for pattern: IDENTIFIER followed by type indicator
                if self.match(TokenType.IDENTIFIER):
                    next_tok = self.peek_token()
                    if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.STAR, TokenType.LBRACKET, 
                                                       TokenType.MAP, TokenType.CHAN, TokenType.FUNC, TokenType.INTERFACE):
                        # Pattern: name type
                        self.advance()  # skip the name
                        param_types.append(self.parse_type())
                    else:
                        # Just a type identifier
                        param_types.append(self.parse_type())
                else:
                    # Complex type (not starting with simple identifier)
                    param_types.append(self.parse_type())
                
                if not self.consume(TokenType.COMMA):
                    break
            self.expect(TokenType.RPAREN)
            
            return_types = []
            if self.match(TokenType.LPAREN):
                self.advance()
                while not self.match(TokenType.RPAREN):
                    return_types.append(self.parse_type())
                    if not self.consume(TokenType.COMMA):
                        break
                self.expect(TokenType.RPAREN)
            elif not self.match(TokenType.LBRACE, TokenType.COMMA, TokenType.RPAREN, TokenType.NEWLINE, TokenType.SEMICOLON):
                # Single return type without parens
                return_types = [self.parse_type()]
            
            return FuncType(param_types, return_types)
        elif self.consume(TokenType.STAR):
            return PointerType(self.parse_type())
        elif self.consume(TokenType.LBRACKET):
            if self.match(TokenType.RBRACKET):
                self.advance()
                return SliceType(self.parse_type())
            else:
                size = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                return ArrayType(size, self.parse_type())
        elif self.consume(TokenType.MAP):
            self.expect(TokenType.LBRACKET)
            key_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            value_type = self.parse_type()
            return MapType(key_type, value_type)
        elif self.consume(TokenType.INTERFACE):
            # interface{} - empty interface (any type)
            self.expect(TokenType.LBRACE)
            self.expect(TokenType.RBRACE)
            return InterfaceType([])
        elif self.consume(TokenType.CHAN):
            if self.consume(TokenType.ARROW):
                return ChannelType(self.parse_type(), "send")
            else:
                return ChannelType(self.parse_type(), "both")
        elif self.match(TokenType.IDENTIFIER):
            name = self.current_token().value
            self.advance()
            return NamedType(name)
        else:
            raise SyntaxError(f"Expected type, got {self.current_token()}")
    
    def parse_types(self) -> List[Type]:
        types = []
        while not self.match(TokenType.RPAREN):
            types.append(self.parse_type())
            if not self.consume(TokenType.COMMA):
                break
        return types
    
    def parse_block(self) -> Block:
        self.skip_newlines()
        self.expect(TokenType.LBRACE)
        statements = []
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.RBRACE):
                break
            statements.append(self.parse_statement())
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return Block(statements)
    
    def parse_statement(self) -> Statement:
        self.skip_statement_terminators()
        
        if self.consume(TokenType.VAR):
            # Support var declarations inside function blocks
            return self.parse_var_decl_stmt()
        elif self.consume(TokenType.CONST):
            # Support const declarations inside function blocks
            return self.parse_const_decl_stmt()
        elif self.consume(TokenType.RETURN):
            values = []
            if not self.match(TokenType.SEMICOLON, TokenType.NEWLINE, TokenType.RBRACE):
                values.append(self.parse_expression())
                while self.consume(TokenType.COMMA):
                    values.append(self.parse_expression())
            self.skip_statement_terminators()
            return ReturnStmt(values)
        elif self.consume(TokenType.IF):
            return self.parse_if_stmt()
        elif self.consume(TokenType.FOR):
            return self.parse_for_stmt()
        elif self.consume(TokenType.SWITCH):
            return self.parse_switch_stmt()
        elif self.consume(TokenType.DEFER):
            expr = self.parse_expression()
            self.skip_statement_terminators()
            return DeferStmt(expr)
        elif self.consume(TokenType.GO):
            expr = self.parse_expression()
            self.skip_statement_terminators()
            return GoStmt(expr)
        elif self.consume(TokenType.BREAK):
            self.skip_statement_terminators()
            return BreakStmt()
        elif self.consume(TokenType.CONTINUE):
            self.skip_statement_terminators()
            return ContinueStmt()
        elif self.consume(TokenType.FALLTHROUGH):
            self.skip_statement_terminators()
            return FallthroughStmt()
        elif self.match(TokenType.LBRACE):
            return self.parse_block()
        else:
            # Parse as expression or assignment
            expr = self.parse_expression()
            
            # Check for assignment operators
            if self.match(TokenType.WALRUS, TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ, 
                         TokenType.STAREQ, TokenType.SLASHEQ, TokenType.PERCENTEQ):
                op = self.current_token().value
                self.advance()  # Consume operator
                targets = [expr]
                
                # Parse right-hand side
                values = []
                values.append(self.parse_expression())
                while self.consume(TokenType.COMMA):
                    values.append(self.parse_expression())
                
                self.skip_statement_terminators()
                return AssignStmt(targets, values, op)
            # Check for comma (multi-target assignment like a, b := 1, 2)
            elif self.match(TokenType.COMMA):
                # This is multi-target assignment, parse remaining targets
                targets = [expr]
                while self.consume(TokenType.COMMA):
                    targets.append(self.parse_expression())
                
                # Now expect assignment operator
                if not self.match(TokenType.WALRUS, TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ, 
                                 TokenType.STAREQ, TokenType.SLASHEQ, TokenType.PERCENTEQ):
                    raise SyntaxError(f"Expected assignment operator, got {self.current_token()}")
                
                op = self.current_token().value
                self.advance()  # Consume operator
                
                # Parse right-hand side
                values = []
                values.append(self.parse_expression())
                while self.consume(TokenType.COMMA):
                    values.append(self.parse_expression())
                
                self.skip_statement_terminators()
                return AssignStmt(targets, values, op)
            # Check for increment/decrement
            elif isinstance(expr, UnaryOp) and expr.op in ['++', '--']:
                self.skip_statement_terminators()
                return IncDecStmt(expr.operand, expr.op)
            else:
                self.skip_statement_terminators()
                return ExpressionStmt(expr)
    
    def parse_assign_stmt(self) -> AssignStmt:
        """Parse assignment statement with early detection
        
        Handles: x := value, a, b := 1, 2, x = value, x += value, etc.
        """
        # Parse left-hand side (targets)
        targets = []
        targets.append(self.parse_expression())
        
        # Handle multiple targets: a, b := 1, 2
        while self.consume(TokenType.COMMA):
            targets.append(self.parse_expression())
        
        # Expect assignment operator (WALRUS, ASSIGN, +=, etc.)
        if not self.match(TokenType.WALRUS, TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ, 
                          TokenType.STAREQ, TokenType.SLASHEQ, TokenType.PERCENTEQ):
            raise SyntaxError(f"Expected assignment operator, got {self.current_token()}")
        
        # Extract and consume the assignment operator
        op = self.current_token().value
        self.advance()  # CRITICAL: Must consume the WALRUS/ASSIGN token here
        
        # Parse right-hand side (values) after consuming operator
        values = []
        values.append(self.parse_expression())
        
        # Handle multiple values: a, b := 1, 2
        while self.consume(TokenType.COMMA):
            values.append(self.parse_expression())
        
        self.skip_newlines()
        return AssignStmt(targets, values, op)
    
    def parse_if_stmt(self) -> IfStmt:
        # Handle optional init statement: if init; condition { }
        init = None
        self.skip_newlines()  # Handle newlines after 'if' keyword
        
        # Look ahead to see if we have an init statement (check for semicolon)
        # We need to parse carefully to distinguish "if x := 5; x > 0" from "if x > 0"
        
        # Save position to potentially backtrack
        saved_pos = self.pos
        
        # Try to parse as assignment (for init statement)
        # Check if next few tokens match pattern: IDENTIFIER WALRUS
        if self.match(TokenType.IDENTIFIER):
            # Look ahead for := or =
            next_tok = self.peek_token()
            if next_tok and next_tok.type in (TokenType.WALRUS, TokenType.ASSIGN):
                # This looks like an assignment init statement
                init = self.parse_assign_stmt()
                self.consume(TokenType.SEMICOLON)  # Consume the semicolon
                condition = self.parse_expression()
            else:
                # Not an assignment, just a regular condition
                condition = self.parse_expression()
        else:
            # Not starting with identifier, must be condition only
            condition = self.parse_expression()
        
        self.skip_newlines()  # Handle newlines before then block
        then_block = self.parse_block()
        else_block = None
        self.skip_newlines()  # Handle newlines before else
        
        if self.consume(TokenType.ELSE):
            self.skip_newlines()  # Handle newlines after 'else' keyword
            if self.consume(TokenType.IF):
                else_block = self.parse_if_stmt()
            else:
                else_block = self.parse_block()
        
        return IfStmt(init, condition, then_block, else_block)
    
    def parse_for_stmt(self) -> Union[ForStmt, ForRangeStmt]:
        # Handle optional parentheses
        self.skip_newlines()  # Handle newlines after 'for' keyword
        has_parens = self.consume(TokenType.LPAREN)
        
        # Simple case: for { ... } (infinite loop)
        if not has_parens and self.match(TokenType.LBRACE):
            return ForStmt(None, None, None, self.parse_block())
        
        # Try to determine if this is a range loop or C-style loop
        init = None
        condition = None
        post = None
        
        # Parse the first part (could be init or just condition)
        if not self.match(TokenType.SEMICOLON):
            first_expr = self.parse_primary()
            
            # Check for comma (two-variable range loop: for k, v := range)
            if self.match(TokenType.COMMA):
                self.advance()
                second_expr = self.parse_primary()
                if self.consume(TokenType.WALRUS):
                    # This is a range loop: for k, v := range iterable
                    if self.match(TokenType.IDENTIFIER) and self.current_token().value == 'range':
                        self.advance()
                    iterable = self.parse_expression()
                    if has_parens:
                        self.expect(TokenType.RPAREN)
                    body = self.parse_block()
                    key_name = first_expr.name if isinstance(first_expr, Identifier) else str(first_expr)
                    value_name = second_expr.name if isinstance(second_expr, Identifier) else str(second_expr)
                    return ForRangeStmt(key_name, value_name, iterable, body)
            # Check for WALRUS followed by "range" keyword (single-variable range loop)
            elif self.match(TokenType.WALRUS):
                self.advance()
                # Check if next token is "range"
                if self.match(TokenType.IDENTIFIER) and self.current_token().value == 'range':
                    self.advance()
                    iterable = self.parse_expression()
                    if has_parens:
                        self.expect(TokenType.RPAREN)
                    body = self.parse_block()
                    var_name = first_expr.name if isinstance(first_expr, Identifier) else str(first_expr)
                    return ForRangeStmt(var_name, None, iterable, body)
                else:
                    # Regular assignment: for i := 0
                    value = self.parse_expression()
                    init = AssignStmt([first_expr], [value], ":=")
            # Check for other assignment operators
            elif self.match(TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ,
                           TokenType.STAREQ, TokenType.SLASHEQ):
                op = self.current_token().value
                self.advance()
                value = self.parse_expression()
                init = AssignStmt([first_expr], [value], op)
            # Otherwise, treat as start of condition (need to re-parse as full expression)
            elif not self.match(TokenType.SEMICOLON):
                # Reparse as full expression (including the first part)
                # This handles: for i < n { ... }
                saved_pos = self.pos - 1  # Back up one token
                self.pos = saved_pos
                condition = self.parse_expression()
        
        # C-style loop with semicolons: for init; condition; post { ... }
        if init is not None or self.match(TokenType.SEMICOLON):
            self.expect(TokenType.SEMICOLON)
            
            # Parse condition
            if not self.match(TokenType.SEMICOLON):
                condition = self.parse_expression()
            
            self.expect(TokenType.SEMICOLON)
            
            # Parse post
            if not self.match(TokenType.RPAREN, TokenType.LBRACE):
                post_target = self.parse_primary()
                if self.match(TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ,
                            TokenType.STAREQ, TokenType.SLASHEQ):
                    op = self.current_token().value
                    self.advance()
                    post_value = self.parse_expression()
                    post = AssignStmt([post_target], [post_value], op)
                elif self.match(TokenType.INC, TokenType.DEC):
                    op = self.current_token().value
                    self.advance()
                    post = IncDecStmt(post_target, op)
                else:
                    post = ExpressionStmt(post_target)
        
        if has_parens:
            self.expect(TokenType.RPAREN)
        
        self.skip_newlines()  # Handle newlines before for body
        body = self.parse_block()
        return ForStmt(init, condition, post, body)
    
    def parse_switch_stmt(self) -> SwitchStmt:
        # Handle optional init statement: switch init; expr { }
        init = None
        expr = None
        self.skip_newlines()  # Handle newlines after 'switch' keyword
        
        # Check if we have an init statement (look for assignment pattern)
        if not self.match(TokenType.LBRACE):
            # Save position to check for init pattern
            if self.match(TokenType.IDENTIFIER):
                # Look ahead for := or =
                next_tok = self.peek_token()
                if next_tok and next_tok.type in (TokenType.WALRUS, TokenType.ASSIGN):
                    # This looks like an assignment init statement
                    init = self.parse_assign_stmt()
                    if self.consume(TokenType.SEMICOLON):
                        # There's a semicolon, so parse the switch expression
                        if not self.match(TokenType.LBRACE):
                            expr = self.parse_expression()
                    # else: init without expr (expr stays None)
                else:
                    # Not an assignment, just a regular expression
                    expr = self.parse_expression()
            else:
                # Not starting with identifier, parse as expression
                expr = self.parse_expression()
        
        self.skip_newlines()  # Handle newlines before switch body
        self.expect(TokenType.LBRACE)
        cases = []
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.consume(TokenType.CASE):
                values = [self.parse_expression()]
                while self.consume(TokenType.COMMA):
                    values.append(self.parse_expression())
                self.expect(TokenType.COLON)
                statements = []
                while not self.match(TokenType.CASE, TokenType.DEFAULT, TokenType.RBRACE):
                    self.skip_newlines()
                    if not self.match(TokenType.CASE, TokenType.DEFAULT, TokenType.RBRACE):
                        statements.append(self.parse_statement())
                cases.append(CaseClause(values, statements))
            elif self.consume(TokenType.DEFAULT):
                self.expect(TokenType.COLON)
                statements = []
                while not self.match(TokenType.CASE, TokenType.DEFAULT, TokenType.RBRACE):
                    self.skip_newlines()
                    if not self.match(TokenType.CASE, TokenType.DEFAULT, TokenType.RBRACE):
                        statements.append(self.parse_statement())
                cases.append(CaseClause([], statements))
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return SwitchStmt(None, expr, cases)
    
    def parse_expression(self) -> Expression:
        return self.parse_ternary()
    
    def parse_ternary(self) -> Expression:
        expr = self.parse_logical_or()
        if self.consume(TokenType.QUESTION):
            true_expr = self.parse_expression()
            self.expect(TokenType.COLON)
            false_expr = self.parse_expression()
            return TernaryOp(expr, true_expr, false_expr)
        return expr
    
    def parse_logical_or(self) -> Expression:
        expr = self.parse_logical_and()
        while self.match(TokenType.OR):
            op = self.current_token().value
            self.advance()
            right = self.parse_logical_and()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_logical_and(self) -> Expression:
        expr = self.parse_comparison()
        while self.match(TokenType.AND):
            op = self.current_token().value
            self.advance()
            right = self.parse_comparison()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_comparison(self) -> Expression:
        expr = self.parse_bitwise_or()
        while self.match(TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self.current_token().value
            self.advance()
            right = self.parse_bitwise_or()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_bitwise_or(self) -> Expression:
        expr = self.parse_bitwise_xor()
        while self.match(TokenType.PIPE):
            op = self.current_token().value
            self.advance()
            right = self.parse_bitwise_xor()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_bitwise_xor(self) -> Expression:
        expr = self.parse_bitwise_and()
        while self.match(TokenType.CARET):
            op = self.current_token().value
            self.advance()
            right = self.parse_bitwise_and()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_bitwise_and(self) -> Expression:
        expr = self.parse_shift()
        while self.match(TokenType.AMPERSAND):
            op = self.current_token().value
            self.advance()
            right = self.parse_shift()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_shift(self) -> Expression:
        expr = self.parse_additive()
        while self.match(TokenType.LSHIFT, TokenType.RSHIFT):
            op = self.current_token().value
            self.advance()
            right = self.parse_additive()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_additive(self) -> Expression:
        expr = self.parse_multiplicative()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.current_token().value
            self.advance()
            right = self.parse_multiplicative()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_multiplicative(self) -> Expression:
        expr = self.parse_unary()
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT, TokenType.AMPNOT):
            op = self.current_token().value
            self.advance()
            right = self.parse_unary()
            expr = BinaryOp(expr, op, right)
        return expr
    
    def parse_unary(self) -> Expression:
        if self.match(TokenType.PLUS, TokenType.MINUS, TokenType.AMPERSAND, TokenType.STAR, TokenType.CARET, TokenType.INC, TokenType.DEC):
            op = self.current_token().value
            self.advance()
            expr = self.parse_unary()
            return UnaryOp(op, expr)
        return self.parse_postfix()
    
    def parse_postfix(self) -> Expression:
        expr = self.parse_primary()
        
        while True:
            if self.consume(TokenType.LPAREN):
                # Special handling for make() - parse type argument properly
                if isinstance(expr, Identifier) and expr.name == "make":
                    args = []
                    if not self.match(TokenType.RPAREN):
                        # First arg could be a type: []string, [][]int, map[K]V
                        if self.match(TokenType.LBRACKET, TokenType.MAP):
                            # It's a type - parse as type
                            type_info = self.parse_type()
                            args.append(type_info)  # Store as TypeNode placeholder
                        else:
                            args.append(self.parse_expression())
                        # Parse remaining args
                        while self.consume(TokenType.COMMA):
                            args.append(self.parse_expression())
                    self.expect(TokenType.RPAREN)
                    # Convert to MakeLiteral if first arg is a Type
                    if args and isinstance(args[0], Type):
                        len_expr = args[1] if len(args) > 1 else None
                        cap_expr = args[2] if len(args) > 2 else None
                        expr = MakeLiteral(args[0], len_expr, cap_expr)
                    else:
                        expr = CallExpr(expr, args)
                else:
                    args = []
                    while not self.match(TokenType.RPAREN):
                        args.append(self.parse_expression())
                        if not self.consume(TokenType.COMMA):
                            break
                    self.expect(TokenType.RPAREN)
                    expr = CallExpr(expr, args)
            elif self.consume(TokenType.LBRACKET):
                if self.match(TokenType.COLON):
                    start = None
                    self.advance()
                    end = None if self.match(TokenType.RBRACKET) else self.parse_expression()
                    self.expect(TokenType.RBRACKET)
                    expr = SliceExpr(expr, start, end, None)
                else:
                    index = self.parse_expression()
                    if self.consume(TokenType.COLON):
                        end = None if self.match(TokenType.RBRACKET, TokenType.COLON) else self.parse_expression()
                        self.expect(TokenType.RBRACKET)
                        expr = SliceExpr(expr, index, end, None)
                    else:
                        self.expect(TokenType.RBRACKET)
                        expr = IndexExpr(expr, index)
            elif self.consume(TokenType.DOT):
                if self.consume(TokenType.LPAREN):
                    # Type assertion: x.(T) or type switch: x.(type)
                    if self.match(TokenType.TYPE):
                        # Type switch: x.(type)
                        self.advance()
                        self.expect(TokenType.RPAREN)
                        # Return a special identifier to indicate type switch
                        expr = FieldExpr(expr, "(type)")
                    else:
                        # Type assertion: x.(SomeType)
                        type_ = self.parse_type()
                        self.expect(TokenType.RPAREN)
                        expr = TypeCast(expr, type_)
                elif self.match(TokenType.IDENTIFIER):
                    field = self.current_token().value
                    self.advance()
                    expr = FieldExpr(expr, field)
                else:
                    break
            elif self.match(TokenType.INC, TokenType.DEC):
                op = self.current_token().value
                self.advance()
                expr = UnaryOp(op, expr)
            else:
                break
        
        return expr
    
    def parse_primary(self) -> Expression:
        if self.match(TokenType.TRUE, TokenType.FALSE):
            value = self.current_token().value
            self.advance()
            return Literal(value, TokenType.TRUE if value == 'true' else TokenType.FALSE)
        elif self.match(TokenType.NIL):
            self.advance()
            return Literal("nil", TokenType.NIL)
        elif self.match(TokenType.INT, TokenType.FLOAT):
            token = self.current_token()
            self.advance()
            return Literal(token.value, token.type)
        elif self.match(TokenType.STRING):
            value = self.current_token().value
            self.advance()
            return Literal(value, TokenType.STRING)
        elif self.match(TokenType.RUNE):
            value = self.current_token().value
            self.advance()
            return Literal(value, TokenType.RUNE)
        elif self.match(TokenType.FUNC):
            # Anonymous function (lambda/closure)
            self.advance()
            self.expect(TokenType.LPAREN)
            params = self.parse_parameters()
            self.expect(TokenType.RPAREN)
            
            returns = []
            if self.match(TokenType.LPAREN):
                self.advance()
                returns = self.parse_types()
                self.expect(TokenType.RPAREN)
            elif not self.match(TokenType.LBRACE):
                returns = [self.parse_type()]
            
            body = self.parse_block()
            # Use LambdaExpr for anonymous functions
            return LambdaExpr(params, returns, body)
        elif self.match(TokenType.IDENTIFIER):
            name = self.current_token().value
            self.advance()
            return Identifier(name)
        elif self.consume(TokenType.LPAREN):
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        elif self.consume(TokenType.LBRACKET):
            # Could be: [elements...] or [size]type{elements} or [...]type{elements}
            
            # Check for [...] (inferred size array)
            if self.match(TokenType.ELLIPSIS):
                self.advance()  # consume ...
                self.expect(TokenType.RBRACKET)  # expect ]
                
                # Now expect type and braces: [...]int{1, 2, 3}
                if self.match(TokenType.IDENTIFIER, TokenType.LBRACKET, TokenType.STAR,
                             TokenType.MAP, TokenType.CHAN, TokenType.FUNC, TokenType.INTERFACE):
                    elem_type = self.parse_type()
                    if self.consume(TokenType.LBRACE):
                        elements = self.parse_array_elements_with_indices()
                        self.expect(TokenType.RBRACE)
                        # Return ArrayLiteral with inferred size
                        return ArrayLiteral(elements)
                
                raise SyntaxError(f"Expected type and initializer after [...]")
            
            if self.match(TokenType.RBRACKET):
                # Empty slice: []type{...}
                self.advance()
                if self.match(TokenType.IDENTIFIER, TokenType.LBRACKET, TokenType.STAR,
                             TokenType.MAP, TokenType.CHAN, TokenType.FUNC, TokenType.INTERFACE):
                    # It's a typed slice literal: []int{1, 2, 3}
                    elem_type = self.parse_type()
                    if self.consume(TokenType.LBRACE):
                        elements = self.parse_array_elements_with_indices()
                        self.expect(TokenType.RBRACE)
                        return ArrayLiteral(elements)
                # Just empty brackets, return empty array
                return ArrayLiteral([])
            else:
                # Parse first element (could be size or element)
                first = self.parse_expression()
                
                if self.consume(TokenType.RBRACKET):
                    # Check if followed by type and braces: [size]type{...}
                    # The type could be a simple identifier or complex type like [3]int
                    if self.match(TokenType.IDENTIFIER, TokenType.LBRACKET, TokenType.STAR, 
                                 TokenType.MAP, TokenType.CHAN, TokenType.FUNC, TokenType.INTERFACE):
                        # Parse the element type
                        elem_type = self.parse_type()
                        if self.consume(TokenType.LBRACE):
                            # It's a typed array literal - can have indexed elements
                            elements = self.parse_array_elements_with_indices()
                            self.expect(TokenType.RBRACE)
                            return ArrayLiteral(elements)
                    # Just a single-element array [expr]
                    return ArrayLiteral([first])
                
                # Multiple elements: [expr, expr, ...]
                elements = [first]
                while self.consume(TokenType.COMMA):
                    elements.append(self.parse_expression())
                self.expect(TokenType.RBRACKET)
                return ArrayLiteral(elements)
        elif self.consume(TokenType.LBRACE):
            # Could be array literal {1, 2, 3} or map literal {key: value}
            # Need to look ahead to distinguish
            self.skip_statement_terminators()  # Skip leading newlines
            
            if self.match(TokenType.RBRACE):
                # Empty literal {}
                self.advance()
                return ArrayLiteral([])
            
            # Parse first element
            first_expr = self.parse_expression()
            
            # Check what follows
            if self.match(TokenType.COLON):
                # It's a map literal: {key: value, ...}
                self.advance()  # consume :
                first_value = self.parse_expression()
                pairs = [(first_expr, first_value)]
                
                while self.consume(TokenType.COMMA):
                    self.skip_statement_terminators()  # Skip newlines
                    if self.match(TokenType.RBRACE):
                        break
                    key = self.parse_expression()
                    self.expect(TokenType.COLON)
                    value = self.parse_expression()
                    pairs.append((key, value))
                
                self.skip_statement_terminators()  # Skip trailing newlines
                self.expect(TokenType.RBRACE)
                return MapLiteral(pairs)
            else:
                # It's an array literal: {expr, expr, ...}
                elements = [first_expr]
                
                while self.consume(TokenType.COMMA):
                    self.skip_statement_terminators()  # Skip newlines
                    if self.match(TokenType.RBRACE):
                        break
                    elements.append(self.parse_expression())
                
                self.skip_statement_terminators()  # Skip trailing newlines
                self.expect(TokenType.RBRACE)
                return ArrayLiteral(elements)
        elif self.consume(TokenType.MAP):
            # Typed map literal: map[KeyType]ValueType{pairs...}
            # Or map type expression: map[KeyType]ValueType
            self.expect(TokenType.LBRACKET)
            # Parse the key type
            key_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            # Parse the value type
            value_type = self.parse_type()
            
            # Check if there's an initializer
            if self.match(TokenType.LBRACE):
                # Parse the initializer
                self.advance()
                pairs = []
                while not self.match(TokenType.RBRACE):
                    key = self.parse_expression()
                    self.expect(TokenType.COLON)
                    value = self.parse_expression()
                    pairs.append((key, value))
                    if not self.consume(TokenType.COMMA):
                        break
                self.expect(TokenType.RBRACE)
                return MapLiteral(pairs)
            else:
                # No initializer, return as MakeLiteral (type expression)
                # This handles cases like make(map[string]int)
                return MakeLiteral(MapType(key_type, value_type), [])
        else:
            raise SyntaxError(f"Unexpected token: {self.current_token()}")
    
    def parse_array_elements_with_indices(self) -> List[Expression]:
        """
        Parse array elements with optional index specifications.
        Supports: {100, 3: 400, 500} → [100, 0, 0, 400, 500]
        """
        elements = []
        current_index = 0
        
        self.skip_statement_terminators()  # Skip leading newlines
        
        while not self.match(TokenType.RBRACE):
            # Parse the first expression (could be value or index)
            expr = self.parse_expression()
            
            # Check if this is an indexed element: index: value
            if self.match(TokenType.COLON):
                self.advance()  # consume :
                
                # expr is the index, parse the value
                target_index = None
                if isinstance(expr, Literal) and expr.type_ == TokenType.INT:
                    target_index = int(expr.value)
                else:
                    raise SyntaxError(f"Array index must be integer literal, got {type(expr).__name__}")
                
                # Fill gaps with zero values if needed
                while current_index < target_index:
                    elements.append(Literal(value="0", type_=TokenType.INT))
                    current_index += 1
                
                # Parse the actual value
                value = self.parse_expression()
                elements.append(value)
                current_index += 1
            else:
                # Just a regular element
                elements.append(expr)
                current_index += 1
            
            # Check for comma
            if not self.consume(TokenType.COMMA):
                break
            
            self.skip_statement_terminators()  # Skip newlines after comma
        
        return elements


def parse_source(source: str) -> Program:
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()