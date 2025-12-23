#!/usr/bin/env python3
from __future__ import annotations

"""
Generate pytest scaffolds for modules to accelerate coverage work.

The generated file imports the target module, verifies public callables,
and instantiates classes with default constructors. Replace the assertions
with real involvement of the system under test (real fixtures, mocks,
and targeted assertions).
"""

import argparse
import ast
import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FunctionInfo:
    name: str
    docstring: str | None
    is_async: bool
    is_private: bool

@dataclass
class ClassInfo:
    name: str
    docstring: str | None
    methods: list[FunctionInfo]

def analyze_module(file_path: Path) -> (list[ClassInfo], list[FunctionInfo]):
    tree = ast.parse(file_path.read_text())
    classes: list[ClassInfo] = []
    functions: list[FunctionInfo] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(FunctionInfo(
                        name=item.name,
                        docstring=ast.get_docstring(item),
                        is_async=isinstance(item, ast.AsyncFunctionDef),
                        is_private=item.name.startswith('_')
                    ))
            classes.append(ClassInfo(name=node.name, docstring=ast.get_docstring(node), methods=methods))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(FunctionInfo(
                name=node.name,
                docstring=ast.get_docstring(node),
                is_async=isinstance(node, ast.AsyncFunctionDef),
                is_private=node.name.startswith('_')
            ))

    return classes, functions

def generate_function_test_scaffold(func: FunctionInfo, module_alias: str) -> str:
    lines = []
    lines.append('@pytest.mark.unit')
    lines.append(f'def test_{func.name}_is_registered():')
    lines.append(f'    assert hasattr({module_alias}, "{func.name}")')
    lines.append(f'    target = getattr({module_alias}, "{func.name}")')
    lines.append('    assert callable(target)')
    lines.append('    signature = inspect.signature(target)')
    if func.docstring:
        lines.append('    assert target.__doc__ is not None')
    lines.append('    assert signature.parameters is not None')
    lines.append('')

    lines.append('@pytest.mark.unit')
    async_marker = '@pytest.mark.asyncio\n' if func.is_async else ''
    lines.append(f'{async_marker}def test_{func.name}_can_accept_kwargs():')
    lines.append(f'    target = getattr({module_alias}, "{func.name}")')
    lines.append('    kwargs = {}')
    lines.append('    try:')
    call_expr = 'target(**kwargs)'
    if func.is_async:
        call_expr = 'await target(**kwargs)'
    lines.append(f'        result = {call_expr}')
    lines.append('    except TypeError as exc:')
    lines.append("        pytest.skip('Provide realistic args for this callable: ' + str(exc))")
    lines.append('    except Exception as exc:')
    lines.append("        pytest.fail('Unexpected exception during invocation: ' + str(exc))")
    lines.append('    else:')
    lines.append('        assert result is not None')
    lines.append('')

    return '\n'.join(lines)

def generate_class_test_scaffold(cls: ClassInfo, module_alias: str) -> str:
    lines = []
    lines.append(f'class Test{cls.name}:')
    lines.append(f'    """Test suite for {cls.name}."""')
    lines.append('    @pytest.mark.unit')
    lines.append(f'    def test_{cls.name}_constructor(self):')
    lines.append(f'        cls_ref = getattr({module_alias}, "{cls.name}")')
    lines.append('        try:')
    lines.append('            instance = cls_ref()')
    lines.append('        except TypeError as exc:')
    lines.append("            pytest.skip('Provide constructor args for {cls.name}: ' + str(exc))")
    lines.append('        else:')
    lines.append('            assert instance is not None')
    lines.append('')

    for method in [m for m in cls.methods if not m.is_private and m.name != '__init__']:
        lines.append('    @pytest.mark.unit')
        if method.is_async:
            lines.append('    @pytest.mark.asyncio')
        lines.append(f'    def test_{cls.name}_{method.name}_exists(self):')
        lines.append(f'        cls_ref = getattr({module_alias}, "{cls.name}")')
        lines.append('        target = getattr(cls_ref, "{0}")'.format(method.name))
        lines.append('        assert callable(target)')
        lines.append('        assert target.__name__ == "{0}"'.format(method.name))
        lines.append('')

    return '\n'.join(lines)

def generate_test_scaffold(file_path: Path) -> str:
    classes, functions = analyze_module(file_path)
    module_import = '.'.join(file_path.with_suffix('').parts)
    module_alias = module_import.replace('.', '_')

    lines = [
        '"""Generated pytest tests"""',
        '',
        'import pytest',
        'import inspect',
        'import importlib',
        'from pathlib import Path',
        'import sys',
        '',
        'sys.path.insert(0, str(Path(__file__).parent.parent.parent))',
        f'{module_alias} = importlib.import_module("{module_import}")',
        '',
        '# Basic function existence tests',
    ]

    for func in functions:
        if func.is_private:
            continue
        lines.append(generate_function_test_scaffold(func, module_alias))

    lines.append('# Class scaffolds')
    for cls in classes:
        lines.append(generate_class_test_scaffold(cls, module_alias))

    lines.append('')
    lines.append('# Extend these tests with real setup/mocks/measurable assertions. Use the edge_case_generator.py output for richer inputs.')

    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description='Generate pytest scaffold for a module.')
    parser.add_argument('module', type=Path, help='Target module path')
    parser.add_argument('--output', '-o', type=Path, help='Write scaffold to this path')
    args = parser.parse_args()

    content = generate_test_scaffold(args.module)
    output_path = args.output or Path(f"tests/test_{args.module.stem}.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    print(f'Scaffold written to {output_path}')

if __name__ == '__main__':
    main()
