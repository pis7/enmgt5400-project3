---
name: review-asic-tool
description: Performs a comprehensive code review of Python ASIC tools using MCP complexity analysis and docstring generation, plus ASIC-domain-specific quality checks. Use when reviewing Python code that parses or processes EDA file formats, or when the user asks for a code review of ASIC tooling.
argument-hint: <file-or-directory-path>
disable-model-invocation: true
---

Perform a comprehensive code review of the following Python ASIC tool: $ARGUMENTS

Follow these four steps in order.

## Step 1: Complexity Analysis (MCP Tool)

Use the `analyze_code_complexity` MCP tool to analyze the target file or directory path provided.

Examine the returned JSON metrics and flag any of the following quality issues:
- Functions with **cyclomatic complexity > 10** — flag as "needs refactoring"
- Functions **longer than 50 lines** — flag as "too long, consider splitting"
- Functions with **nesting depth > 4** — flag as "too deeply nested"
- Functions or classes **missing docstrings** — collect these for Step 2
- Classes with **more than 10 methods** — flag as "consider decomposition"

If the MCP tool is unavailable or returns an error, fall back to reading the file and performing a manual review of the same metrics.

## Step 2: Documentation Coverage (MCP Tool)

For any functions identified in Step 1 as missing docstrings, use the `generate_docstrings` MCP tool to generate and insert Google-style docstrings.

Report:
- How many functions were missing docstrings before this step
- Which specific functions had docstrings generated
- The docstring coverage percentage (before and after)

If the MCP tool is unavailable, manually write Google-style docstrings for the undocumented functions instead.

## Step 3: ASIC-Domain-Specific Review

Review the code against these ASIC tool development best practices:

### EDA Terminology
- Are variable names, class names, and function names using standard ASIC/EDA terminology?
- Expected terms: cell, net, pin, port, instance, clock domain, setup, hold, fanout, drive strength, slack, skew, transition
- Flag any generic names that should use domain-specific terms (e.g., "component" should be "cell", "connection" should be "net")

### File Format Handling
- If the tool parses ASIC files (SDC, LEF, DEF, Liberty, SDF, SPEF, Verilog netlists):
  - Does it handle malformed input gracefully (log + skip vs. crash)?
  - Does it report line numbers in error messages?
  - Does it handle vendor-specific extensions or non-conformant output?
  - Does it support backslash-escaped Verilog identifiers?

### Scalability
- Can the tool handle large files (millions of lines) without loading everything into memory?
- Are there streaming or incremental parsing patterns where appropriate?
- Are data structures efficient for the expected data sizes?

### Units & Precision
- Are timing values explicitly documented with units (ns or ps)?
- Are capacitance/resistance units clear (fF, pF, ohms)?
- Is `pytest.approx()` or equivalent used when comparing floating-point timing values?

### CLI Interface
- Does the tool use `argparse` with clear help text?
- Is it suitable for integration into EDA shell scripts and automated flows?
- Does it support common flags: `--input`, `--output`, `--verbose`, `--strict`?

### Logging & Diagnostics
- Does it use the `logging` module with per-module loggers (not `print()`)?
- Are log levels appropriate (DEBUG for parsing details, WARNING for skipped entries, ERROR for failures)?

## Step 4: Summary Report

Present the findings in this structured format:

### Overall Health Score
Rate as one of: **Excellent** | **Good** | **Needs Improvement** | **Critical**

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
- Scalability assessment: [good/concerns noted]
- Unit documentation: [clear/unclear/missing]
- CLI quality: [production-ready/needs work/missing]

### Prioritized Recommendations
List specific improvements ordered by impact. Each recommendation must reference the exact function or class name and line number.
