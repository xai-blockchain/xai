"""
Comprehensive Unit Tests for AST Validator

Tests the AST validation security boundary that prevents dangerous
operations before code execution via exec().
"""

import pytest

from xai.sandbox.ast_validator import ASTValidator, SecurityError, validate_code


class TestASTValidatorBasics:
    """Test basic AST validator functionality"""

    def test_safe_code_passes(self):
        """Simple safe code should pass validation"""
        validator = ASTValidator()

        code = """
x = 1 + 2
y = x * 3
result = x + y
"""
        # Should not raise
        validator.validate(code)

    def test_arithmetic_operations_allowed(self):
        """All arithmetic operations should be allowed"""
        validator = ASTValidator()

        code = """
a = 10 + 5
b = 10 - 5
c = 10 * 5
d = 10 / 5
e = 10 // 5
f = 10 % 5
g = 10 ** 5
h = -a
i = +a
"""
        validator.validate(code)

    def test_comparisons_allowed(self):
        """All comparison operations should be allowed"""
        validator = ASTValidator()

        code = """
a = 1 == 2
b = 1 != 2
c = 1 < 2
d = 1 <= 2
e = 1 > 2
f = 1 >= 2
g = 1 is None
h = 1 is not None
i = 1 in [1, 2, 3]
j = 1 not in [1, 2, 3]
"""
        validator.validate(code)

    def test_boolean_operations_allowed(self):
        """Boolean operations should be allowed"""
        validator = ASTValidator()

        code = """
a = True and False
b = True or False
c = not True
"""
        validator.validate(code)

    def test_collections_allowed(self):
        """Lists, tuples, sets, dicts should be allowed"""
        validator = ASTValidator()

        code = """
lst = [1, 2, 3]
tpl = (1, 2, 3)
st = {1, 2, 3}
dct = {'a': 1, 'b': 2}
"""
        validator.validate(code)

    def test_comprehensions_allowed(self):
        """List/set/dict comprehensions should be allowed"""
        validator = ASTValidator()

        code = """
lst = [x * 2 for x in range(10)]
st = {x * 2 for x in range(10)}
dct = {x: x * 2 for x in range(10)}
gen = (x * 2 for x in range(10))
"""
        validator.validate(code)

    def test_control_flow_allowed(self):
        """If/for/while should be allowed"""
        validator = ASTValidator()

        code = """
if True:
    x = 1
elif False:
    x = 2
else:
    x = 3

for i in range(10):
    print(i)

while x < 10:
    x += 1
    if x > 5:
        break
    if x == 3:
        continue
"""
        validator.validate(code)

    def test_functions_allowed(self):
        """Function definitions should be allowed"""
        validator = ASTValidator()

        code = """
def add(a, b):
    return a + b

def greet(name="World"):
    return f"Hello {name}"

result = add(1, 2)
msg = greet()
"""
        validator.validate(code)

    def test_lambda_allowed(self):
        """Lambda functions should be allowed"""
        validator = ASTValidator()

        code = """
double = lambda x: x * 2
result = double(5)
"""
        validator.validate(code)

    def test_exception_handling_allowed(self):
        """Try/except/finally should be allowed"""
        validator = ASTValidator()

        code = """
try:
    x = 1 / 0
except ZeroDivisionError:
    x = 0
except Exception as e:
    x = -1
finally:
    pass

assert x == 0
raise ValueError("test")
"""
        validator.validate(code)


class TestImportRejection:
    """Test that all import statements are rejected"""

    def test_import_rejected(self):
        """Import statement should be rejected"""
        validator = ASTValidator()

        code = "import os"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "Import" in str(exc_info.value)
        assert "not allowed" in str(exc_info.value)

    def test_from_import_rejected(self):
        """From import statement should be rejected"""
        validator = ASTValidator()

        code = "from os import path"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "ImportFrom" in str(exc_info.value)
        assert "not allowed" in str(exc_info.value)

    def test_import_as_rejected(self):
        """Import as should be rejected"""
        validator = ASTValidator()

        code = "import json as j"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "Import" in str(exc_info.value)

    def test_nested_import_rejected(self):
        """Import inside function should be rejected"""
        validator = ASTValidator()

        code = """
def dangerous():
    import os
    return os.listdir('/')
"""

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "Import" in str(exc_info.value)


class TestDangerousFunctionRejection:
    """Test that dangerous functions are rejected"""

    def test_open_rejected(self):
        """open() should be rejected"""
        validator = ASTValidator()

        code = "f = open('/etc/passwd', 'r')"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "open()" in str(exc_info.value)
        assert "not allowed" in str(exc_info.value)

    def test_eval_rejected(self):
        """eval() should be rejected"""
        validator = ASTValidator()

        code = "result = eval('1 + 1')"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "eval()" in str(exc_info.value)

    def test_exec_rejected(self):
        """exec() should be rejected"""
        validator = ASTValidator()

        code = "exec('print(1)')"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "exec()" in str(exc_info.value)

    def test_compile_rejected(self):
        """compile() should be rejected"""
        validator = ASTValidator()

        code = "code = compile('1 + 1', '<string>', 'eval')"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "compile()" in str(exc_info.value)

    def test___import___rejected(self):
        """__import__() should be rejected"""
        validator = ASTValidator()

        code = "os = __import__('os')"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "__import__()" in str(exc_info.value)

    def test_getattr_rejected(self):
        """getattr() should be rejected"""
        validator = ASTValidator()

        code = "attr = getattr(obj, 'dangerous')"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "getattr()" in str(exc_info.value)

    def test_setattr_rejected(self):
        """setattr() should be rejected"""
        validator = ASTValidator()

        code = "setattr(obj, 'dangerous', True)"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "setattr()" in str(exc_info.value)

    def test_delattr_rejected(self):
        """delattr() should be rejected"""
        validator = ASTValidator()

        code = "delattr(obj, 'dangerous')"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "delattr()" in str(exc_info.value)

    def test_globals_rejected(self):
        """globals() should be rejected"""
        validator = ASTValidator()

        code = "g = globals()"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "globals()" in str(exc_info.value)

    def test_locals_rejected(self):
        """locals() should be rejected"""
        validator = ASTValidator()

        code = "l = locals()"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "locals()" in str(exc_info.value)

    def test_vars_rejected(self):
        """vars() should be rejected"""
        validator = ASTValidator()

        code = "v = vars()"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "vars()" in str(exc_info.value)

    def test_dir_rejected(self):
        """dir() should be rejected"""
        validator = ASTValidator()

        code = "d = dir()"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "dir()" in str(exc_info.value)

    def test_breakpoint_rejected(self):
        """breakpoint() should be rejected"""
        validator = ASTValidator()

        code = "breakpoint()"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "breakpoint()" in str(exc_info.value)

    def test_exit_rejected(self):
        """exit() should be rejected"""
        validator = ASTValidator()

        code = "exit(0)"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "exit()" in str(exc_info.value)

    def test_quit_rejected(self):
        """quit() should be rejected"""
        validator = ASTValidator()

        code = "quit()"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "quit()" in str(exc_info.value)


class TestForbiddenNodeTypes:
    """Test that forbidden node types are rejected"""

    def test_global_rejected(self):
        """global statement should be rejected"""
        validator = ASTValidator()

        code = """
x = 1
def func():
    global x
    x = 2
"""

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "Global" in str(exc_info.value)

    def test_nonlocal_rejected(self):
        """nonlocal statement should be rejected"""
        validator = ASTValidator()

        code = """
def outer():
    x = 1
    def inner():
        nonlocal x
        x = 2
"""

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "Nonlocal" in str(exc_info.value)

    def test_class_rejected(self):
        """Class definitions should be rejected"""
        validator = ASTValidator()

        code = """
class MyClass:
    pass
"""

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "ClassDef" in str(exc_info.value)

    def test_async_function_rejected(self):
        """Async function definitions should be rejected"""
        validator = ASTValidator()

        code = """
async def async_func():
    return 1
"""

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "AsyncFunctionDef" in str(exc_info.value)

    def test_async_for_rejected(self):
        """Async for loops should be rejected"""
        validator = ASTValidator()

        code = """
async def func():
    async for item in async_iter:
        pass
"""

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        # Will be rejected at AsyncFunctionDef level first
        assert "Async" in str(exc_info.value)

    def test_yield_rejected(self):
        """Yield expressions should be rejected"""
        validator = ASTValidator()

        code = """
def gen():
    yield 1
    yield 2
"""

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "Yield" in str(exc_info.value)

    def test_yield_from_rejected(self):
        """Yield from should be rejected"""
        validator = ASTValidator()

        code = """
def gen():
    yield from range(10)
"""

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "YieldFrom" in str(exc_info.value)


class TestAllowedFunctions:
    """Test that allowed functions override works"""

    def test_allowed_functions_parameter(self):
        """Allowed functions parameter should work"""
        # Without allowing 'open', it should fail
        validator1 = ASTValidator()

        code = "f = open('test.txt')"

        with pytest.raises(SecurityError):
            validator1.validate(code)

        # With allowing 'open', it should pass
        validator2 = ASTValidator(allowed_functions={'open'})
        validator2.validate(code)  # Should not raise

    def test_safe_builtins_allowed_by_default(self):
        """Safe builtins should be allowed by default"""
        validator = ASTValidator(allowed_functions={'abs', 'len', 'max', 'min'})

        code = """
a = abs(-5)
b = len([1, 2, 3])
c = max(1, 2, 3)
d = min(1, 2, 3)
"""

        validator.validate(code)


class TestComplexAttackScenarios:
    """Test complex attack scenarios"""

    def test_nested_dangerous_calls(self):
        """Nested dangerous function calls should be rejected"""
        validator = ASTValidator()

        code = "result = eval(compile('1 + 1', '<string>', 'eval'))"

        with pytest.raises(SecurityError):
            validator.validate(code)

    def test_obfuscated_import(self):
        """Obfuscated imports should be rejected"""
        validator = ASTValidator()

        code = "__import__('os').system('ls')"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "__import__()" in str(exc_info.value)

    def test_multiple_violations(self):
        """Code with multiple violations should reject on first one"""
        validator = ASTValidator()

        code = """
import os
eval('1 + 1')
exec('print(1)')
"""

        # Should reject on first violation (import)
        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "Import" in str(exc_info.value)

    def test_dangerous_in_comprehension(self):
        """Dangerous functions in comprehensions should be rejected"""
        validator = ASTValidator()

        code = "[eval(str(x)) for x in range(10)]"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "eval()" in str(exc_info.value)

    def test_dangerous_in_lambda(self):
        """Dangerous functions in lambda should be rejected"""
        validator = ASTValidator()

        code = "f = lambda x: eval(x)"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(code)

        assert "eval()" in str(exc_info.value)


class TestSyntaxErrors:
    """Test syntax error handling"""

    def test_syntax_error_raised(self):
        """Invalid syntax should raise SyntaxError"""
        validator = ASTValidator()

        code = "def invalid syntax here"

        with pytest.raises(SyntaxError):
            validator.validate(code)

    def test_incomplete_code_rejected(self):
        """Incomplete code should raise SyntaxError"""
        validator = ASTValidator()

        code = "if True:"

        with pytest.raises(SyntaxError):
            validator.validate(code)


class TestConvenienceFunction:
    """Test the convenience validate_code function"""

    def test_validate_code_function(self):
        """validate_code convenience function should work"""
        code = "x = 1 + 2"
        validate_code(code)  # Should not raise

    def test_validate_code_with_filename(self):
        """validate_code should accept filename parameter"""
        code = "x = 1 + 2"
        validate_code(code, filename='<test>')  # Should not raise

    def test_validate_code_with_allowed_functions(self):
        """validate_code should accept allowed_functions parameter"""
        code = "f = open('test.txt')"

        # Should fail without allowing
        with pytest.raises(SecurityError):
            validate_code(code)

        # Should pass with allowing
        validate_code(code, allowed_functions={'open'})


class TestLogging:
    """Test that rejections are logged properly"""

    def test_rejection_logged(self, caplog):
        """Rejections should be logged"""
        import logging
        caplog.set_level(logging.ERROR)

        validator = ASTValidator()
        code = "import os"

        with pytest.raises(SecurityError):
            validator.validate(code)

        # Check that rejection was logged
        assert any("AST validation rejected" in record.message for record in caplog.records)
        assert any("Import" in record.message for record in caplog.records)

    def test_success_logged(self, caplog):
        """Successful validation should be logged at debug level"""
        import logging
        caplog.set_level(logging.DEBUG)

        validator = ASTValidator()
        code = "x = 1 + 2"

        validator.validate(code)

        # Check that success was logged
        assert any("AST validation passed" in record.message for record in caplog.records)


class TestEdgeCases:
    """Test edge cases and corner cases"""

    def test_empty_code(self):
        """Empty code should pass"""
        validator = ASTValidator()
        validator.validate("")

    def test_only_comments(self):
        """Code with only comments should pass"""
        validator = ASTValidator()

        code = """
# This is a comment
# Another comment
"""
        validator.validate(code)

    def test_only_docstring(self):
        """Code with only docstring should pass"""
        validator = ASTValidator()

        code = '"""This is a docstring"""'
        validator.validate(code)

    def test_very_long_code(self):
        """Very long code should be validated"""
        validator = ASTValidator()

        # Generate long but safe code
        code = "\n".join([f"x{i} = {i} + {i}" for i in range(1000)])
        validator.validate(code)

    def test_deeply_nested_code(self):
        """Deeply nested code should be validated"""
        validator = ASTValidator()

        code = """
if True:
    if True:
        if True:
            if True:
                if True:
                    x = 1
"""
        validator.validate(code)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
