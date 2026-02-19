---
name: gen-asic-parser
description: Generates a complete, production-ready Python parser for ASIC file formats (SDC, LEF, DEF, Liberty, SDF, SPEF, Verilog-netlist). Use when creating a new parser for an EDA file format or when the user needs to parse ASIC design files.
argument-hint: <format-name>
disable-model-invocation: true
---

Generate a complete Python parser for the following ASIC file format: $ARGUMENTS

Supported formats: **SDC**, **LEF**, **DEF**, **Liberty**, **SDF**, **SPEF**, **Verilog-netlist**.

Consult [format-reference.md](format-reference.md) for format-specific data models and parsing strategies before generating code.

## Required Output Structure

Generate a single production-ready Python file with these five sections in order:

1. **Module docstring** — description, CLI example, 3–5 lines of representative input syntax, example parsed output repr
2. **Data models** — `@dataclass` per entity; type-annotated fields; `__post_init__` validation; descriptive `__repr__`; `__all__` export list
3. **`ParseError` exception** — with `line_num: int`, `line_text: str`, `message: str` attributes
4. **Parser class** — `<Format>Parser(strict=False)` with `parse_file(path: Path)` and `parse_string(content: str)`; line-by-line reading for large-file support; `strict=False` logs warnings and skips malformed entries (real EDA output is frequently non-conformant)
5. **CLI entry point** — `if __name__ == "__main__"` with `argparse`: `--input/-i` (required), `--output/-o`, `--format` (json/summary), `--strict`, `--verbose/-v`

## Coding Rules

- `from __future__ import annotations` at top
- `pathlib.Path` for all paths — never `os.path`
- `re` for line-oriented formats (SDC, SDF, SPEF); `pyparsing` or state machine for hierarchical formats (Liberty, LEF, DEF)
- Backslash-escaped identifiers (`\name ` — trailing space is part of the token) must be handled
- Both `\n` and `\r\n` line endings must work
- `logging` with a per-module logger — no `print()`
- DEBUG for parse details, WARNING for skipped entries, ERROR for failures
- `__all__` listing all public classes
