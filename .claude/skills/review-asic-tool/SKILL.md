---
name: review-asic-tool
description: Performs a comprehensive code review of Python ASIC tools using MCP complexity analysis and docstring generation, plus ASIC-domain-specific quality checks. Use when reviewing Python code that parses or processes EDA file formats, or when the user asks for a code review of ASIC tooling.
argument-hint: <file-or-directory-path>
disable-model-invocation: true
---

Perform a comprehensive code review of the following Python ASIC tool: $ARGUMENTS

Follow these four steps in order.

## Step 1: Complexity Analysis (MCP Tool)

Call the `analyze_code_complexity` MCP tool. The MCP server's allowed directory is the parent folder (one level above this project). Resolve `$ARGUMENTS` to an absolute path using the current working directory, then pass that absolute path to the tool — e.g., if CWD is `/path/to/project3` and argument is `examples/sdc_parser.py`, pass `/path/to/project3/examples/sdc_parser.py`.

Examine the returned JSON and flag:
- Cyclomatic complexity > 10 → "needs refactoring"
- Function body > 50 lines → "too long, consider splitting"
- Nesting depth > 4 → "too deeply nested"
- Missing docstrings → collect names for Step 2
- Class with > 10 methods → "consider decomposition"

**Do not read the file manually.** Only fall back to manual review if the MCP tool returns an explicit error (e.g., path outside allowed directory or server unavailable).

## Step 2: Documentation Coverage (MCP Tool)

For each function flagged as missing a docstring in Step 1, call `generate_docstrings` with the same absolute path used in Step 1. Do not call it for functions that already have docstrings.

Report: how many functions were undocumented before, which were documented, and the coverage percentage before and after.

**Do not write docstrings manually** unless the MCP tool is unavailable.

## Step 3: ASIC-Domain Review

Review the code for these ASIC-specific quality issues:

- **EDA naming**: Are names using standard EDA terms (cell, net, pin, port, instance, clock domain, setup, hold, fanout, slack, skew, transition)? Flag generic substitutes like "component" (should be "cell") or "connection" (should be "net").
- **Error handling**: If parsing ASIC files (SDC, LEF, DEF, Liberty, SDF, SPEF, Verilog), does it handle malformed input gracefully? Report line numbers in errors? Handle backslash-escaped identifiers?
- **Scalability**: Can it process million-line files without loading everything into memory? Are streaming/incremental patterns used where needed?
- **Units**: Are timing values documented with explicit units (ns/ps)? Capacitance (fF/pF)?
- **CLI**: Does it use `argparse`? Suitable for EDA shell script integration?
- **Logging**: Uses `logging` module with per-module loggers, not `print()`?

## Step 4: Summary Report

### Overall Health Score
**Excellent** | **Good** | **Needs Improvement** | **Critical**

### Metrics Summary
| Metric | Value |
|--------|-------|
| Total functions | |
| Total classes | |
| Total lines of code | |
| Average cyclomatic complexity | |
| Max cyclomatic complexity | |
| Max nesting depth | |
| Docstring coverage (before) | |
| Docstring coverage (after) | |

### ASIC-Specific Findings
- EDA naming compliance: [pass/needs work]
- File format error handling: [robust/adequate/missing]
- Scalability: [good/concerns noted]
- Unit documentation: [clear/unclear/missing]
- CLI quality: [production-ready/needs work/missing]

### Prioritized Recommendations
Ordered by impact. Each item must reference the exact function or class name and line number.
