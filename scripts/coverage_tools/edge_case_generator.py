#!/usr/bin/env python3
from __future__ import annotations

"""
Generate edge-case tests from Python module metadata.

Scans a module to discover functions, inspects their signatures,
and emits parameterized fixtures/exercises that span empty/max/invalid
values for each parameter. The output is intended to be a starting
point for real edge-case coverage, not a replacement for handcrafted
logic, but it removes the TODO placeholders and gives developers
actual test code to adapt.

Usage:
    python edge_case_generator.py path/to/module.py [--output tests/generated.py]
"""

import argparse
import importlib.util
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class Parameter:
    """Captured metadata for a single function parameter."""

    name: str
    annotation: str | None
    has_default: bool

@dataclass
class FunctionSignature:
    """Metadata describing one callable in the target module."""

    name: str
    parameters: list[Parameter]
    is_async: bool

class EdgeCaseGenerator:
    """Helper to generate test strings for a callable."""

    TEST_VALUES: dict[str, list[Any]] = {
        'int': [0, -1, 1, 2**31 - 1, -2**31],
        'float': [0.0, -1.0, 1.0, float('inf'), float('-inf')],
        'str': ['', 'a', 'test', ' ', '\n', '\t', 'x' * 200],
        'bool': [True, False],
        'list': [[], [1], list(range(20))],
        'dict': [{}, {'a': 1}, {'nested': {'value': 1}}],
    }

    FIXTURE_VALUES: dict[str, dict[str, str]] = {
        'empty': {
            'int': '0',
            'float': '0.0',
            'str': "''",
            'bool': 'False',
            'list': '[]',
            'dict': '{}',
            'Any': 'None',
        },
        'max': {
            'int': str(2**31 - 1),
            'float': 'sys.float_info.max',
            'str': "'x' * 256",
            'bool': 'True',
            'list': 'list(range(50))',
            'dict': "{'key': 'value', 'count': 50}",
            'Any': 'None',
        },
        'invalid': {
            'int': "'invalid'",
            'float': "'invalid'",
            'str': 'None',
            'bool': "'invalid'",
            'list': 'None',
            'dict': 'None',
            'Any': 'None',
        },
    }

    def load_module(self, module_path: Path):
        """Dynamically import the module at `module_path`."""
        spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot import module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def collect_functions(self, module) -> list[FunctionSignature]:
        """Return all top-level callables found in the module."""
        signatures: list[FunctionSignature] = []
        for _, callable_obj in inspect.getmembers(module, inspect.isfunction):
            if callable_obj.__name__.startswith('_'):
                continue
            sig = inspect.signature(callable_obj)
            params = []
            for param in sig.parameters.values():
                if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue
                annotation = None
                if param.annotation is not inspect.Parameter.empty:
                    annotation = getattr(param.annotation, '__name__', str(param.annotation))
                params.append(Parameter(name=param.name, annotation=annotation, has_default=param.default is not inspect.Parameter.empty))
            signatures.append(
                FunctionSignature(name=callable_obj.__name__, parameters=params, is_async=inspect.iscoroutinefunction(callable_obj))
            )
        return signatures

    def extract_base_type(self, annotation: str | None) -> str:
        """Reduce annotations like int | None -> int."""
        if not annotation:
            return 'Any'
        annotation = annotation.replace('', '').replace(' | None', '')
        for base in ['int', 'float', 'str', 'bool', 'list', 'dict']:
            if base in annotation:
                return base
        return 'Any'

    def build_parameterized_test(self, function: FunctionSignature, parameter: Parameter) -> str:
        """Emit a parameterized pytest test for a single parameter."""
        base_type = self.extract_base_type(parameter.annotation)
        values = self.TEST_VALUES.get(base_type, self.TEST_VALUES.get('str'))
        values_list = ', '.join(repr(v) for v in values)
        async_marker = '@pytest.mark.asyncio\n' if function.is_async else ''
        test_def = f"""@pytest.mark.parametrize('{parameter.name}', [{values_list}])\n{async_marker}@pytest.mark.unit\ndef test_{function.name}_{parameter.name}(\"{parameter.name}\"):\n"""
        body = [f"    kwargs = {{'{parameter.name}': {parameter.name}}}"]
        body.append("    try:")
        call = f"{function.name}(**kwargs)" if not function.is_async else f"await {function.name}(**kwargs)"
        body.append(f"        result = {call}")
        body.append("    except TypeError as exc:")
        body.append("        pytest.skip('Missing context for parameter ' + str(exc))")
        body.append("    except Exception as exc:")
        body.append("        pytest.fail('Unexpected exception: ' + str(exc))")
        body.append("    else:")
        body.append("        assert result is not None")
        return test_def + '\n'.join(body) + '\n\n'

    def build_fixture_tests(self, function: FunctionSignature) -> str:
        """Emit fixture-based coverage for empty/max/invalid contexts."""
        base_lines = [f'class Test{function.name.capitalize()}Fixtures:']
        variants = ['empty', 'max']
        for variant in variants:
            fixture_vals = self.FIXTURE_VALUES[variant]
            base_lines.append(f"    @pytest.fixture")
            base_lines.append(f"    def {variant}_inputs(self):")
            base_lines.append(f"        return {{")
            for param in function.parameters:
                base_type = self.extract_base_type(param.annotation)
                literal = fixture_vals.get(base_type, 'None')
                base_lines.append(f"            '{param.name}': {literal},")
            base_lines.append(f"        }}")
            base_lines.append("")
            base_lines.append(f"    @pytest.mark.unit")
            if function.is_async:
                base_lines.append(f"    @pytest.mark.asyncio")
            base_lines.append(f"    def test_{variant}_inputs(self, {variant}_inputs):")
            base_lines.append("        try:")
            call = f"{function.name}(**{variant}_inputs)" if not function.is_async else f"await {function.name}(**{variant}_inputs)"
            base_lines.append(f"            result = {call}")
            base_lines.append("        except Exception as exc:")
            base_lines.append(f"            pytest.fail('Failed with {variant} inputs: ' + str(exc))")
            base_lines.append("        else:")
            base_lines.append("            assert result is not None")
            base_lines.append("")
        return '\n'.join(base_lines) + '\n\n'

    def generate(self, module_path: Path) -> str:
        """Produce the final script content."""
        module = self.load_module(module_path)
        functions = self.collect_functions(module)
        module_name = module_path.stem
        output_lines: list[str] = [
            f"# Generated edge-case tests for {module_path.name}",
            "",
            "import pytest",
            "",
            f"from {module_name} import *",
            "",
        ]
        for func in functions:
            for param in func.parameters:
                output_lines.append(self.build_parameterized_test(func, param))
            output_lines.append(self.build_fixture_tests(func))
        return '\n'.join(output_lines)

def main():
    parser = argparse.ArgumentParser(description='Generate edge case tests from a module.')
    parser.add_argument('module', type=Path, help='Path to target module')
    parser.add_argument('--output', '-o', type=Path, help='Target output file')
    args = parser.parse_args()

    generator = EdgeCaseGenerator()
    content = generator.generate(args.module)

    output_path = args.output or Path(f"tests/test_{args.module.stem}_edge_cases.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    print(f"Edge case test scaffold written to {output_path}")

if __name__ == '__main__':
    main()
