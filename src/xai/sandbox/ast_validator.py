"""
AST Validator for Sandbox Code Execution

Provides pre-execution AST validation to prevent dangerous operations
before code is executed via exec(). This is a critical security boundary
that validates all AST node types against an explicit allowlist.

Security properties:
- Rejects all imports (Import, ImportFrom)
- Rejects nested exec/eval/compile
- Rejects global/nonlocal scope manipulation
- Rejects dangerous function calls (open, __import__, etc.)
- Allowlist-based approach (deny by default)
- Comprehensive logging of all rejections
"""

from __future__ import annotations

import ast
import logging

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Raised when AST validation detects a security violation"""
    pass

class ASTValidator:
    """
    AST validator for sandbox code execution

    Validates Python code AST before execution to prevent dangerous operations.
    Uses allowlist-based approach - every node type must be explicitly allowed.
    """

    # Safe AST node types that are allowed
    # These are the building blocks of safe computation
    ALLOWED_NODE_TYPES = {
        # Literals
        'Constant',      # Python 3.8+: replaces Num, Str, Bytes, NameConstant, Ellipsis
        'Num',           # Numbers (deprecated in 3.8+, kept for compatibility)
        'Str',           # Strings (deprecated in 3.8+, kept for compatibility)
        'Bytes',         # Byte literals (deprecated in 3.8+, kept for compatibility)
        'NameConstant',  # True, False, None (deprecated in 3.8+, kept for compatibility)
        'Ellipsis',      # ... (deprecated in 3.8+, kept for compatibility)
        'JoinedStr',     # f-strings (formatted string literals)
        'FormattedValue',# Formatted values in f-strings

        # Variables
        'Name',          # Variable names
        'Load',          # Load variable context
        'Store',         # Store variable context
        'Del',           # Delete variable context

        # Expressions
        'Expr',          # Expression statement
        'UnaryOp',       # Unary operations (not, +, -)
        'UAdd',          # Unary +
        'USub',          # Unary -
        'Not',           # not
        'Invert',        # ~
        'BinOp',         # Binary operations
        'Add',           # +
        'Sub',           # -
        'Mult',          # *
        'Div',           # /
        'FloorDiv',      # //
        'Mod',           # %
        'Pow',           # **
        'LShift',        # <<
        'RShift',        # >>
        'BitOr',         # |
        'BitXor',        # ^
        'BitAnd',        # &
        'MatMult',       # @ (matrix multiplication)
        'BoolOp',        # Boolean operations (and, or)
        'And',           # and
        'Or',            # or
        'Compare',       # Comparisons
        'Eq',            # ==
        'NotEq',         # !=
        'Lt',            # <
        'LtE',           # <=
        'Gt',            # >
        'GtE',           # >=
        'Is',            # is
        'IsNot',         # is not
        'In',            # in
        'NotIn',         # not in

        # Subscripting
        'Subscript',     # a[b]
        'Index',         # Index (deprecated in 3.9+, kept for compatibility)
        'Slice',         # a[b:c]

        # Attributes
        'Attribute',     # obj.attr

        # Function calls (validated separately for dangerous functions)
        'Call',          # Function calls

        # Collections
        'List',          # [1, 2, 3]
        'Tuple',         # (1, 2, 3)
        'Set',           # {1, 2, 3}
        'Dict',          # {a: b}

        # Comprehensions
        'ListComp',      # [x for x in ...]
        'SetComp',       # {x for x in ...}
        'DictComp',      # {k: v for ...}
        'GeneratorExp',  # (x for x in ...)
        'comprehension', # Comprehension clause

        # Statements
        'Assign',        # a = b
        'AugAssign',     # a += b
        'AnnAssign',     # a: int = b (annotated assignment)
        'Delete',        # del a
        'Pass',          # pass
        'Break',         # break
        'Continue',      # continue
        'Return',        # return

        # Control flow
        'If',            # if/elif/else
        'For',           # for loops
        'While',         # while loops
        'With',          # with statement
        'withitem',      # with context item

        # Function/Class definitions (but not decorators with dangerous calls)
        'FunctionDef',   # def func(): ...
        'Lambda',        # lambda x: x
        'arguments',     # Function arguments
        'arg',           # Single argument
        'keyword',       # Keyword argument

        # Exception handling
        'Try',           # try/except/finally
        'ExceptHandler', # except clause
        'Raise',         # raise
        'Assert',        # assert

        # Module
        'Module',        # Module root
        'Interactive',   # Interactive mode
        'Expression',    # Expression mode

        # Match statement (Python 3.10+)
        'Match',         # match statement
        'match_case',    # case clause
        'MatchValue',    # case pattern: value
        'MatchSingleton',# case pattern: singleton
        'MatchSequence', # case pattern: sequence
        'MatchMapping',  # case pattern: mapping
        'MatchClass',    # case pattern: class
        'MatchStar',     # case pattern: *rest
        'MatchAs',       # case pattern: as
        'MatchOr',       # case pattern: |
    }

    # Explicitly forbidden node types
    # These are NEVER allowed in sandbox code
    FORBIDDEN_NODE_TYPES = {
        'Import',        # import foo
        'ImportFrom',    # from foo import bar
        'Exec',          # exec() (Python 2)
        'Global',        # global x
        'Nonlocal',      # nonlocal x
        'ClassDef',      # class Foo: ... (can be dangerous)
        'AsyncFunctionDef',  # async def (requires event loop access)
        'AsyncFor',      # async for (requires event loop access)
        'AsyncWith',     # async with (requires event loop access)
        'Await',         # await (requires event loop access)
        'Yield',         # yield (generator manipulation)
        'YieldFrom',     # yield from (generator manipulation)
    }

    # Dangerous function names that should never be called
    DANGEROUS_FUNCTIONS = {
        'open',          # File I/O
        '__import__',    # Dynamic imports
        'eval',          # Code execution
        'exec',          # Code execution
        'compile',       # Code compilation
        'execfile',      # File execution (Python 2)
        'input',         # User input (can be dangerous in some contexts)
        'raw_input',     # User input (Python 2)
        'reload',        # Module reloading
        'vars',          # Access to variables
        'locals',        # Access to local scope
        'globals',       # Access to global scope
        'dir',           # Introspection
        'getattr',       # Attribute access bypass
        'setattr',       # Attribute modification bypass
        'delattr',       # Attribute deletion bypass
        'hasattr',       # Attribute checking (can probe for private attrs)
        '__getattribute__', # Low-level attribute access
        '__setattr__',   # Low-level attribute modification
        '__delattr__',   # Low-level attribute deletion
        'breakpoint',    # Debugger access
        'help',          # Interactive help (can access internals)
        'exit',          # Process termination
        'quit',          # Process termination
        'memoryview',    # Direct memory access
        'bytearray',     # Mutable bytes (can be used for attacks)
    }

    def __init__(
        self,
        allowed_functions: set[str] | None = None,
        extra_allowed_nodes: set[str] | None = None,
    ):
        """
        Initialize AST validator

        Args:
            allowed_functions: Set of function names that are explicitly allowed
                              (in addition to safe builtins)
            extra_allowed_nodes: Additional AST node types to allow
        """
        self.allowed_functions = allowed_functions or set()
        self.allowed_nodes = self.ALLOWED_NODE_TYPES.copy()
        if extra_allowed_nodes:
            self.allowed_nodes.update(extra_allowed_nodes)

    def validate(self, code: str, filename: str = '<sandbox>') -> None:
        """
        Validate code AST before execution

        Args:
            code: Python code to validate
            filename: Filename for error messages

        Raises:
            SecurityError: If code contains dangerous operations
            SyntaxError: If code has syntax errors
        """
        # Parse code to AST
        try:
            tree = ast.parse(code, filename=filename, mode='exec')
        except SyntaxError as e:
            logger.warning(
                f"AST validation: syntax error in {filename}",
                extra={
                    'event': 'sandbox.ast_validation_failed',
                    'reason': 'syntax_error',
                    'error': str(e),
                }
            )
            raise

        # Walk AST and validate all nodes
        self._validate_tree(tree, filename)

        logger.debug(
            f"AST validation passed for {filename}",
            extra={'event': 'sandbox.ast_validation_passed', 'code_filename': filename}
        )

    def _validate_tree(self, tree: ast.AST, filename: str) -> None:
        """
        Walk AST tree and validate all nodes

        Args:
            tree: AST tree to validate
            filename: Filename for error messages

        Raises:
            SecurityError: If any node is not allowed
        """
        for node in ast.walk(tree):
            node_type = type(node).__name__

            # Check if node type is explicitly forbidden
            if node_type in self.FORBIDDEN_NODE_TYPES:
                self._reject_node(node, node_type, filename, reason='forbidden_node_type')

            # Check if node type is in allowlist
            if node_type not in self.allowed_nodes:
                self._reject_node(node, node_type, filename, reason='not_in_allowlist')

            # Special validation for function calls
            if isinstance(node, ast.Call):
                self._validate_call(node, filename)

    def _validate_call(self, node: ast.Call, filename: str) -> None:
        """
        Validate function call node

        Args:
            node: Call AST node
            filename: Filename for error messages

        Raises:
            SecurityError: If call is to a dangerous function
        """
        # Extract function name
        func_name = self._get_call_name(node)

        if func_name and func_name in self.DANGEROUS_FUNCTIONS:
            # Check if it's in the allowed functions override
            if func_name not in self.allowed_functions:
                self._reject_call(node, func_name, filename)

        # Check for nested eval/exec/compile calls
        if func_name in {'eval', 'exec', 'compile'}:
            self._reject_call(node, func_name, filename, reason='nested_execution')

    def _get_call_name(self, node: ast.Call) -> str | None:
        """
        Extract function name from Call node

        Args:
            node: Call AST node

        Returns:
            Function name or None if not a simple name
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # For method calls, return the attribute name
            return node.func.attr
        return None

    def _reject_node(
        self,
        node: ast.AST,
        node_type: str,
        filename: str,
        reason: str = 'security_violation'
    ) -> None:
        """
        Reject an AST node and raise SecurityError

        Args:
            node: AST node that was rejected
            node_type: Type name of the node
            filename: Filename for error messages
            reason: Reason for rejection

        Raises:
            SecurityError: Always raised
        """
        line = getattr(node, 'lineno', 'unknown')
        col = getattr(node, 'col_offset', 'unknown')

        error_msg = (
            f"Security violation in {filename} at line {line}, col {col}: "
            f"AST node type '{node_type}' is not allowed in sandbox"
        )

        logger.error(
            f"AST validation rejected: {node_type} at {filename}:{line}:{col}",
            extra={
                'event': 'sandbox.ast_validation_rejected',
                'reason': reason,
                'node_type': node_type,
                'code_filename': filename,
                'line': line,
                'col': col,
            }
        )

        raise SecurityError(error_msg)

    def _reject_call(
        self,
        node: ast.Call,
        func_name: str,
        filename: str,
        reason: str = 'dangerous_function'
    ) -> None:
        """
        Reject a dangerous function call

        Args:
            node: Call AST node
            func_name: Name of the dangerous function
            filename: Filename for error messages
            reason: Reason for rejection

        Raises:
            SecurityError: Always raised
        """
        line = getattr(node, 'lineno', 'unknown')
        col = getattr(node, 'col_offset', 'unknown')

        error_msg = (
            f"Security violation in {filename} at line {line}, col {col}: "
            f"Function '{func_name}()' is not allowed in sandbox"
        )

        logger.error(
            f"AST validation rejected call: {func_name}() at {filename}:{line}:{col}",
            extra={
                'event': 'sandbox.ast_validation_rejected',
                'reason': reason,
                'function': func_name,
                'code_filename': filename,
                'line': line,
                'col': col,
            }
        )

        raise SecurityError(error_msg)

def validate_code(
    code: str,
    filename: str = '<sandbox>',
    allowed_functions: set[str] | None = None
) -> None:
    """
    Convenience function to validate code AST

    Args:
        code: Python code to validate
        filename: Filename for error messages
        allowed_functions: Set of function names that are explicitly allowed

    Raises:
        SecurityError: If code contains dangerous operations
        SyntaxError: If code has syntax errors
    """
    validator = ASTValidator(allowed_functions=allowed_functions)
    validator.validate(code, filename)
