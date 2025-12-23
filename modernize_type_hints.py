#!/usr/bin/env python3
"""
Modernize type hints from Python 3.8 to Python 3.10+ syntax.
Converts Optional[], Union[], List[], Dict[], Tuple[], Set[] to modern syntax.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Set


def has_future_annotations(content: str) -> bool:
    """Check if file already has 'from __future__ import annotations'."""
    return bool(re.search(r'^from __future__ import annotations', content, re.MULTILINE))


def add_future_annotations(content: str) -> str:
    """Add 'from __future__ import annotations' at the top of the file."""
    # Find first non-comment, non-docstring line
    lines = content.split('\n')

    # Skip shebang, docstrings, and comments at the top
    insert_pos = 0
    in_docstring = False
    docstring_delim = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip shebang
        if i == 0 and stripped.startswith('#!'):
            insert_pos = i + 1
            continue

        # Handle docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_delim = '"""' if stripped.startswith('"""') else "'''"
                if stripped.count(docstring_delim) >= 2:
                    # Single line docstring
                    insert_pos = i + 1
                else:
                    in_docstring = True
                continue
        else:
            if docstring_delim in line:
                in_docstring = False
                insert_pos = i + 1
                continue

        # Skip comments
        if stripped.startswith('#'):
            insert_pos = i + 1
            continue

        # Empty lines
        if not stripped:
            if insert_pos == 0:
                insert_pos = i + 1
            continue

        # Found first real line
        break

    # Insert the import
    lines.insert(insert_pos, 'from __future__ import annotations')
    lines.insert(insert_pos + 1, '')

    return '\n'.join(lines)


def modernize_typing_imports(content: str) -> str:
    """
    Modernize typing imports by removing unnecessary ones and keeping needed ones.
    """
    # Types to keep (not replaceable with builtins)
    keep_types = {
        'TypeVar', 'Generic', 'Protocol', 'Callable', 'Any', 'ClassVar',
        'Final', 'Literal', 'TypedDict', 'cast', 'overload', 'Type',
        'TYPE_CHECKING', 'NewType', 'NoReturn', 'ParamSpec', 'Concatenate',
        'TypeAlias', 'TypeGuard', 'Self', 'Never', 'LiteralString', 'Unpack',
        'Awaitable', 'Coroutine', 'AsyncIterator', 'AsyncIterable',
        'AsyncGenerator', 'ContextManager', 'AsyncContextManager', 'NamedTuple'
    }

    # Types to remove (replaceable with builtins)
    remove_types = {
        'Optional', 'Union', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet',
        'Deque', 'DefaultDict', 'OrderedDict', 'Counter', 'ChainMap'
    }

    # Find all 'from typing import ...' lines
    def replace_typing_import(match):
        imports_str = match.group(1)
        # Split by comma and clean up
        imports = [imp.strip() for imp in imports_str.split(',')]

        # Filter: keep necessary types, remove builtin-replaceable types
        kept_imports = []
        for imp in imports:
            # Extract the base type name (handle 'as' aliases)
            base_name = imp.split(' as ')[0].strip()

            # Remove if it's in remove_types
            if base_name in remove_types:
                continue

            # Otherwise keep it
            kept_imports.append(imp)

        if not kept_imports:
            return ''  # Remove the entire import line

        return f"from typing import {', '.join(kept_imports)}"

    # Replace the import lines
    content = re.sub(
        r'^from typing import ([^\n]+)$',
        replace_typing_import,
        content,
        flags=re.MULTILINE
    )

    # Clean up empty lines left by removed imports
    content = re.sub(r'\n\n\n+', '\n\n', content)

    return content


def modernize_type_hints(content: str) -> str:
    """Convert old-style type hints to modern syntax."""

    # Optional[X] -> X | None
    # Handle nested cases with bracket matching
    def replace_optional(text):
        changed = True
        while changed:
            changed = False
            # Find Optional[ and match brackets
            pos = 0
            while True:
                start = text.find('Optional[', pos)
                if start == -1:
                    break

                # Match brackets
                depth = 0
                i = start + 9  # len('Optional[')
                for i in range(start + 9, len(text)):
                    if text[i] == '[':
                        depth += 1
                    elif text[i] == ']':
                        if depth == 0:
                            # Found matching bracket
                            inner = text[start + 9:i]
                            replacement = f"{inner} | None"
                            text = text[:start] + replacement + text[i + 1:]
                            changed = True
                            break
                        depth -= 1
                pos = start + 1

        return text

    content = replace_optional(content)

    # Union[X, Y, ...] -> X | Y | ...
    def replace_union(text):
        changed = True
        while changed:
            changed = False
            pos = 0
            while True:
                start = text.find('Union[', pos)
                if start == -1:
                    break

                # Match brackets
                depth = 0
                for i in range(start + 6, len(text)):  # len('Union[')
                    if text[i] == '[':
                        depth += 1
                    elif text[i] == ']':
                        if depth == 0:
                            # Found matching bracket
                            inner = text[start + 6:i]
                            # Split by comma, respecting nested brackets
                            parts = []
                            current = []
                            bracket_depth = 0
                            for char in inner:
                                if char in '[(':
                                    bracket_depth += 1
                                    current.append(char)
                                elif char in '])':
                                    bracket_depth -= 1
                                    current.append(char)
                                elif char == ',' and bracket_depth == 0:
                                    parts.append(''.join(current).strip())
                                    current = []
                                else:
                                    current.append(char)
                            if current:
                                parts.append(''.join(current).strip())

                            replacement = ' | '.join(parts)
                            text = text[:start] + replacement + text[i + 1:]
                            changed = True
                            break
                        depth -= 1
                pos = start + 1

        return text

    content = replace_union(content)

    # List[X] -> list[X]
    content = re.sub(r'\bList\[', 'list[', content)

    # Dict[K, V] -> dict[K, V]
    content = re.sub(r'\bDict\[', 'dict[', content)

    # Tuple[X, Y] -> tuple[X, Y]
    content = re.sub(r'\bTuple\[', 'tuple[', content)

    # Set[X] -> set[X]
    content = re.sub(r'\bSet\[', 'set[', content)

    # FrozenSet[X] -> frozenset[X]
    content = re.sub(r'\bFrozenSet\[', 'frozenset[', content)

    # Deque[X] -> deque[X]
    content = re.sub(r'\bDeque\[', 'deque[', content)

    # DefaultDict[K, V] -> defaultdict[K, V]
    content = re.sub(r'\bDefaultDict\[', 'defaultdict[', content)

    # OrderedDict[K, V] -> OrderedDict[K, V] (keep as is, it's from collections)
    # Note: OrderedDict is not a builtin, so we don't change it

    # Counter[X] -> Counter[X] (keep as is, it's from collections)

    # ChainMap[K, V] -> ChainMap[K, V] (keep as is, it's from collections)

    return content


def process_file(file_path: Path) -> tuple[bool, str]:
    """
    Process a single Python file to modernize type hints.
    Returns (changed, message).
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # Check if file uses old typing constructs
        needs_update = any([
            'Optional[' in content,
            'Union[' in content,
            'List[' in content,
            'Dict[' in content,
            'Tuple[' in content,
            'Set[' in content,
        ])

        if not needs_update:
            return False, "No old-style type hints found"

        # Add future annotations if not present
        if not has_future_annotations(content):
            content = add_future_annotations(content)

        # Modernize type hints
        content = modernize_type_hints(content)

        # Modernize typing imports
        content = modernize_typing_imports(content)

        # Only write if changed
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True, "Updated"
        else:
            return False, "No changes needed"

    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        # Default: process all Python files in src/xai
        base_path = Path(__file__).parent / 'src' / 'xai'
        paths = list(base_path.rglob('*.py'))

        # Also include test files
        test_path = Path(__file__).parent / 'tests'
        if test_path.exists():
            paths.extend(list(test_path.rglob('*.py')))

        # Include scripts
        scripts_path = Path(__file__).parent / 'scripts'
        if scripts_path.exists():
            paths.extend(list(scripts_path.rglob('*.py')))

        # Include explorer
        explorer_path = Path(__file__).parent / 'explorer'
        if explorer_path.exists():
            paths.extend(list(explorer_path.rglob('*.py')))

    total = len(paths)
    updated = 0
    errors = 0

    print(f"Processing {total} Python files...")

    for file_path in paths:
        if not file_path.is_file():
            continue

        changed, message = process_file(file_path)

        if changed:
            updated += 1
            print(f"✓ {file_path.relative_to(Path.cwd())}: {message}")
        elif 'Error' in message:
            errors += 1
            print(f"✗ {file_path.relative_to(Path.cwd())}: {message}")

    print(f"\n{'='*60}")
    print(f"Total files processed: {total}")
    print(f"Files updated: {updated}")
    print(f"Errors: {errors}")
    print(f"{'='*60}")

    return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
