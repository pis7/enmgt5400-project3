<!-- ANNOTATION #1 — Project Identity & Domain Context
WHY THIS SECTION EXISTS: This is the single highest-leverage section in the entire file.
Claude Code reads CLAUDE.md at the start of every session, so without explicit domain
context it would default to generic Python advice. By stating upfront that this project
involves ASIC design flows, EDA tool integration, and specific file formats, every
response Claude generates is automatically ASIC-domain-aware. This eliminates the need
to re-explain the domain in every conversation. The design flow stages and file format
list act as a "vocabulary primer" that grounds Claude in the correct terminology from
the first interaction. -->
# ASIC Tool Development Project

This project contains Python tools for ASIC (Application-Specific Integrated Circuit)
design workflows. The tools parse, analyze, and manipulate data from EDA (Electronic
Design Automation) tool outputs and industry-standard file formats.

## Domain Context

- We write Python utilities that sit between EDA tools in a chip design flow
- Common workflow stages: RTL design → synthesis → place-and-route → timing analysis → signoff
- Our tools read/write industry-standard file formats (listed below)
- Target users are ASIC/FPGA engineers who run these tools from the command line or integrate them into automated EDA flows
- We never invoke EDA tools (Synopsys, Cadence, Siemens, etc.) directly — we only process their input/output files

---

<!-- ANNOTATION #2 — Coding Standards
WHY THIS SECTION EXISTS: Without explicit coding standards, Claude will generate code in
whatever style it considers "default Python." In ASIC tool development, naming conventions
are critical because our code interfaces with EDA tools that use very specific terminology.
For example, a generic assistant might name a variable "component" when the EDA standard
term is "cell," or use "wire" when the correct term is "net." Specifying Google-style
docstrings also ensures consistency with the MCP server's generate_docstrings tool, which
produces Google-style output. The complexity limits (CC ≤ 10, nesting ≤ 4) match the
thresholds enforced by the MCP server's analyze_code_complexity tool, creating a unified
quality standard across manual and automated review. -->
## Coding Standards

- **Python version**: 3.13+ (match statements and modern syntax are acceptable)
- **Docstrings**: Google-style on all public functions and classes
- **Type hints**: Required on all function signatures; use `from __future__ import annotations` for forward references
- **Naming**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - Use standard EDA terminology: cell, net, pin, port, instance, clock domain, setup/hold, fanout, drive strength, slack, skew, transition
- **Complexity limits**:
  - Maximum cyclomatic complexity: 10 per function
  - Maximum nesting depth: 4 levels
  - Maximum function length: 50 lines
- **Path handling**: Always use `pathlib.Path`, never raw `os.path` string manipulation
- **Data modeling**: Use `dataclasses` or `pydantic` models for structured ASIC data (timing arcs, cell libraries, constraint sets, etc.)
- **Logging**: Use the `logging` module with per-module loggers — never bare `print()` for diagnostic output
- **Error messages**: Include file path and line number when reporting parse errors in ASIC files

---

<!-- ANNOTATION #3 — ASIC File Formats Reference
WHY THIS SECTION EXISTS: ASIC file formats are niche and not well-represented in general
LLM training data. Without this reference, Claude is likely to hallucinate incorrect
format details — for example, confusing LEF (library-level physical abstracts) with DEF
(design-level placed/routed data), or producing syntactically invalid SDC commands. By
providing concise descriptions and key syntax patterns for each format, Claude can
generate accurate parsers and transformations. This section also serves as a shared
vocabulary between the developer and Claude, so when a conversation references "Liberty
timing arcs" or "SPEF parasitics," both sides understand exactly what is meant. -->
## ASIC File Formats Reference

| Format | Extension | Description | Key Syntax |
|--------|-----------|-------------|------------|
| **SDC** | `.sdc` | Synopsys Design Constraints — Tcl-based timing constraints | `create_clock`, `set_input_delay`, `set_false_path`, `set_multicycle_path` |
| **Liberty** | `.lib` | Timing/power models for standard cells | Nested group syntax: `library() { cell() { pin() { timing() { } } } }` |
| **LEF** | `.lef` | Library Exchange Format — physical cell abstracts | `MACRO`, `PIN`, `OBS`, `LAYER`, `SITE` keywords with indented blocks |
| **DEF** | `.def` | Design Exchange Format — placed and routed design | `COMPONENTS`, `NETS`, `SPECIALNETS`, `ROWS`, `TRACKS` sections |
| **SDF** | `.sdf` | Standard Delay Format — annotated timing delays | `(IOPATH ...)`, `(INTERCONNECT ...)`, `(SETUP ...)`, `(HOLD ...)` |
| **SPEF** | `.spef` | Standard Parasitic Exchange Format — RC parasitics | `*D_NET`, `*CONN`, `*CAP`, `*RES` sections per net |
| **Verilog Netlist** | `.v` | Gate-level netlist (post-synthesis) | `module`, `wire`, `assign`, cell instantiation: `NAND2X1 U1 (.A(n1), .B(n2), .Y(n3));` |

### Format-Specific Gotchas
- **SDC**: Commands can span multiple lines with backslash continuation; comments start with `#`
- **Liberty**: Values can be quoted or unquoted; lookup tables use comma-separated floats in quoted strings
- **LEF/DEF**: Statements are terminated by semicolons; names may contain brackets (e.g., `BUS[0]`)
- **SDF**: Parenthesized S-expression-like syntax; timing values are triplets `(min:typ:max)`
- **Verilog**: Identifiers may be backslash-escaped (e.g., `\some/name `); the trailing space is part of the escape

---

<!-- ANNOTATION #4 — Preferred Libraries & Parser Architecture
WHY THIS SECTION EXISTS: This section serves two purposes. First, listing preferred
libraries prevents Claude from suggesting inappropriate dependencies — for instance,
a generic assistant might suggest pandas for tabular EDA data, but ASIC files often
contain millions of timing paths and need memory-efficient streaming approaches. Second,
the parser architecture pattern ensures that every file-format parser in the project
follows a consistent structure. When a new engineer (or Claude) generates a parser for
a new format, it automatically matches the existing codebase architecture. This makes
the project maintainable as the number of supported formats grows. -->
## Preferred Libraries & Patterns

### Libraries
- `argparse` — CLI interfaces (our tools are invoked from shell scripts in EDA flows)
- `re` — Lightweight parsing for line-oriented formats (SDC, SDF, SPEF)
- `pyparsing` — Grammar-based parsing for nested/hierarchical formats (Liberty, LEF/DEF)
- `dataclasses` — Data models for ASIC constructs
- `pydantic` — Complex models requiring runtime validation
- `json` / `csv` — Tool output interchange formats
- `logging` — Diagnostics with per-module loggers
- `pathlib` — All file path handling
- `ast` — Python source analysis (matches our MCP server approach)
- `pytest` — Testing, with fixtures for sample ASIC file snippets

### Standard Parser Architecture

All file-format parsers in this project should follow this structure:

```
1. Data models       — @dataclass for each parsed entity (e.g., Cell, Net, TimingArc)
                       with __post_init__ validation and descriptive __repr__
2. Parser class      — <Format>Parser with:
                       • parse_file(path: Path) -> <TopLevelModel>
                       • parse_string(content: str) -> <TopLevelModel>
                       • _parse_line(line: str, line_num: int) for line-oriented formats
3. Error handling    — Custom ParseError(Exception) with line_num, line_text, message
                       • strict=False (default): log warning, skip malformed entry
                       • strict=True: raise ParseError immediately
4. CLI entry point   — if __name__ == "__main__" with argparse:
                       --input, --output, --format (json/summary), --strict, --verbose
5. Round-trip        — write() or dump() method where applicable
```

---

<!-- ANNOTATION #5 — MCP Server Integration
WHY THIS SECTION EXISTS: This section is essential for Part 3 of the project (external
tool integration). By documenting the MCP server's tools, their exact names, and their
parameters here in CLAUDE.md, Claude Code knows these tools exist in every session. This
means slash commands like /review-asic-tool that reference MCP tools will work correctly —
Claude will call analyze_code_complexity and generate_docstrings via MCP rather than trying
to reimplement that analysis logic itself. Without this section, Claude would have no way
to know that these tools are available and would fall back on manual AST inspection, which
duplicates functionality that already exists in the MCP server. -->
## MCP Server Integration

This project uses the `dev-workflow-server` MCP server from ENMGT 5400 Project 2.

### Available MCP Tools

| Tool | Signature | Description |
|------|-----------|-------------|
| `analyze_code_complexity` | `(file_path: str)` | Returns JSON with cyclomatic complexity, nesting depth, line counts, class/function metrics, and docstring presence for a Python file or directory |
| `generate_docstrings` | `(file_path: str, function_name?: str)` | Generates and inserts Google-style docstrings; can target a single function, a whole file, or a directory |

### Available MCP Prompts

| Prompt | Signature | Description |
|--------|-----------|-------------|
| `code_review_assistant` | `(file_path: str)` | Returns a structured multi-step code review template that chains the two tools above |

### Server Configuration

- **Server name**: `dev-workflow`
- **Run command**: `uv run --directory "<path-to-enmgt5400-project2>" python server.py`
- **Transport**: stdio
- **Allowed directory**: Configured via `ALLOWED_DIRECTORY` in the server's `.env` file

---

<!-- ANNOTATION #6 (BONUS) — Behavioral Guardrails
WHY THIS SECTION EXISTS: This is a "behavioral guardrails" pattern recommended by
Anthropic for CLAUDE.md files. These short directives prevent common failure modes
specific to the ASIC domain. For example, without the "never suggest running EDA tools"
rule, Claude might try to invoke Synopsys Design Compiler or Cadence Innovus when
asked to "run timing analysis." The large-file and escaped-identifier reminders address
real-world edge cases that cause tools to fail silently in production — issues that a
generic coding assistant would never anticipate. Each guardrail addresses a specific
failure mode encountered in practice. -->
## Important Reminders

- **No EDA tool invocation**: Never suggest running EDA tools directly (Synopsys, Cadence, Siemens, etc.) — we only write Python tools that process their input/output files
- **Malformed input**: Always include error handling for malformed input files — real EDA tool outputs are frequently non-conformant or contain vendor-specific extensions
- **Timing units**: Be explicit about units — timing values are in nanoseconds (ns) or picoseconds (ps); capacitance in femtofarads (fF) or picofarads (pF)
- **Escaped identifiers**: Verilog backslash-escaped identifiers (e.g., `\bus[0] `) include a trailing space — parsers must handle this correctly
- **Scalability**: ASIC files can be extremely large (millions of lines) — always consider streaming/incremental parsing; never load entire files into memory unless the file size is bounded
- **Cross-platform**: Tools must work on both Linux (EDA server) and Windows (development) — use `pathlib.Path` and avoid OS-specific path separators
