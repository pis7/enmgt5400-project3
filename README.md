# ENMGT 5400 Project 3: Claude Code Customization for ASIC Tool Development

## Domain: Python Tool Development for ASICs

I chose this domain because my primary professional and academic interest is in developing Python tools that support ASIC (Application-Specific Integrated Circuit) design workflows. These tools sit between EDA (Electronic Design Automation) tools in the chip design flow, parsing and transforming industry-standard file formats like SDC, Liberty, LEF/DEF, SDF, and Verilog netlists. AI assistance is particularly valuable here because these file formats are niche, poorly documented, and poorly represented in LLM training data — a well-configured AI assistant with explicit domain context dramatically reduces the time spent on parser development, test writing, and code review.

## Project Structure

```
enmgt5400-project3/
├── .claude/
│   └── skills/
│       ├── review-asic-tool/
│       │   └── SKILL.md            # Skill 1: Code review with MCP integration
│       ├── validate-asic-file/
│       │   ├── SKILL.md            # Skill 2: ASIC file format validator
│       │   └── format-rules.md     # Format-specific validity rules reference
│       └── asic-tool-test/
│           └── SKILL.md            # Skill 3: Test suite generation
├── CLAUDE.md                       # Annotated project instructions file
├── main.py                         # Project entry point
├── pyproject.toml                  # Python project configuration
├── README.md                       # This file
├── examples/
│   ├── sdc_parser.py              # Example: SDC constraint parser (for review/test skills)
│   ├── timing_analyzer.py         # Example: STA timing report analyzer
│   ├── netlist_utils.py           # Example: Verilog netlist utilities
│   ├── sample_timing.rpt          # Sample PrimeTime-style timing report
│   ├── valid_sdc.sdc              # Valid SDC — passes validation
│   ├── invalid_sdc.sdc            # Invalid SDC — 4 deliberate errors
│   ├── valid_liberty.lib          # Valid Liberty snippet
│   ├── invalid_liberty.lib        # Invalid Liberty — unbalanced braces, table mismatch
│   ├── valid_lef.lef              # Valid LEF with two macros
│   ├── invalid_lef.lef            # Invalid LEF — missing ORIGIN, bad CLASS, unclosed MACRO
│   ├── valid_def.def              # Valid DEF with placed components and nets
│   ├── invalid_def.def            # Invalid DEF — count mismatch, float coords, missing END
│   ├── valid_sdf.sdf              # Valid SDF with cell delays and timing checks
│   ├── invalid_sdf.sdf            # Invalid SDF — missing TIMESCALE, units in triplets
│   ├── valid_spef.spef            # Valid SPEF with RC parasitics for 3 nets
│   ├── invalid_spef.spef          # Invalid SPEF — missing *END, non-numeric cap, bad *RES
│   ├── valid_netlist.v            # Valid gate-level Verilog netlist
│   └── invalid_netlist.v          # Invalid Verilog — missing endmodule, undeclared wire
```

---

## Part 1: Annotated CLAUDE.md

The `CLAUDE.md` file is structured around six sections, each annotated with HTML comments (`<!-- ANNOTATION #N: ... -->`) that explain the rationale behind the design choices. The annotations are invisible to Claude Code during normal operation but fully readable when reviewing the raw file.

### Annotation Summary

| # | Section | Rationale |
|---|---------|-----------|
| 1 | **Project Identity & Domain Context** | Highest-leverage section — establishes ASIC domain awareness from the first interaction, eliminating the need to re-explain the domain in every conversation |
| 2 | **Coding Standards** | Enforces ASIC-specific naming conventions (EDA terminology) and complexity limits that match the MCP server's thresholds |
| 3 | **ASIC File Formats Reference** | Compensates for LLM knowledge gaps about niche formats; prevents hallucinated format details and syntax errors |
| 4 | **Preferred Libraries & Parser Architecture** | Prevents inappropriate dependency suggestions; ensures every parser follows the same consistent architecture |
| 5 | **MCP Server Integration** | Documents the MCP tools so skills can invoke them correctly; Claude knows these tools exist in every session |
| 6 | **Behavioral Guardrails** | Prevents common ASIC-specific failure modes (e.g., suggesting EDA tool invocation, ignoring escaped identifiers, loading huge files into memory) |

### What Makes This CLAUDE.md Effective

1. **Domain grounding**: Every response is ASIC-aware without needing per-conversation context-setting
2. **Consistent output**: Coding standards + parser architecture pattern = uniform code across all generated files
3. **Format accuracy**: The file formats reference section prevents the most common category of errors (incorrect syntax generation for niche formats)
4. **Tool integration**: MCP server documentation enables seamless skill-to-tool chaining
5. **Guardrails that prevent real failures**: Each behavioral rule addresses a specific failure mode encountered in ASIC tool development

---

## Part 2: Claude Code Skills

Skills follow the [Agent Skills](https://agentskills.io) open standard and are stored as `SKILL.md` files in `.claude/skills/<skill-name>/` directories. Each skill includes YAML frontmatter (`---` delimiters) that configures the skill name, description, argument hints, and invocation control. All three skills use `disable-model-invocation: true` so they are only triggered manually via `/skill-name`, not automatically by Claude.

### Skill 1: `/review-asic-tool` — Code Review with MCP Integration

**Location**: `.claude/skills/review-asic-tool/SKILL.md`

**Purpose**: Performs a comprehensive four-step code review of Python ASIC tools.

**How it works**:
1. Calls the MCP `analyze_code_complexity` tool to get quantitative metrics
2. Calls the MCP `generate_docstrings` tool to fill documentation gaps
3. Performs ASIC-domain-specific quality checks (EDA naming, format handling, scalability, units, CLI)
4. Produces a structured summary report with a health score and prioritized recommendations

**Example usage**: `/review-asic-tool sdc_parser.py`

**This skill is the primary MCP integration point** — it demonstrates both MCP tools working together in a domain-specific workflow.

### Skill 2: `/validate-asic-file` — ASIC File Format Validator

**Location**: `.claude/skills/validate-asic-file/SKILL.md`
**Rules reference**: `.claude/skills/validate-asic-file/format-rules.md`

**Purpose**: Validates any ASIC design file against format-specific structural and syntax rules, reporting errors and warnings with line numbers and a clear VALID / VALID WITH WARNINGS / INVALID verdict.

**How it works**:
1. Detects the format from the file extension (SDC, Liberty, LEF, DEF, SDF, SPEF, Verilog Netlist)
2. Loads the format-specific rules from `format-rules.md` (a separate reference file — not loaded for every invocation)
3. Reads the file and checks every REQUIRED rule (errors) and RECOMMENDED rule (warnings)
4. Produces a structured validation report with line-numbered findings

**Example usage**: `/validate-asic-file examples/valid_sdc.sdc`

**Why this is valuable**: EDA tool error messages are notoriously cryptic — a synthesis tool may fail 10 minutes into a run because of a malformed SDC constraint written hours earlier. Pre-flight validation catches these issues immediately, with clear human-readable error messages and line numbers, before any EDA tool is invoked.

### Skill 3: `/asic-tool-test` — Test Framework Skeleton Generation

**Location**: `.claude/skills/asic-tool-test/SKILL.md`

**Purpose**: Generates a pytest test framework skeleton for a Python ASIC tool — complete fixtures and infrastructure, plus stub test methods with Given/Then descriptions that the user fills in.

**How it works**: Reads the target module, then generates a `test_<module>.py` file with two layers:
1. **Complete infrastructure**: realistic ASIC file content fixtures (SDC, Liberty, Verilog, SDF, SPEF), edge case fixtures (malformed input, CRLF endings, backslash-escaped identifiers, empty files), `tmp_path` file helpers — all fully implemented and ready to use
2. **Test stubs**: one method per test case, organized into `TestParsing`, `TestErrorHandling`, `TestEdgeCases`, `TestNumericPrecision`, and `TestCLI` classes — each stub has the correct signature, the right fixtures as parameters, a Given/Then docstring describing exactly what to assert, and `pass` as the body for you to implement

**Example usage**: `/asic-tool-test examples/sdc_parser.py`

**Why this is valuable**: The hardest part of testing ASIC tools is writing realistic test fixtures and knowing which edge cases to cover — you need EDA domain knowledge to create valid SDC or Liberty content and to identify format-specific gotchas. This skill eliminates that design work, leaving only the implementation of the assertions themselves.

---

## Part 3: External Tool Integration — MCP Server

### Tool: `dev-workflow-server` (from ENMGT 5400 Project 2)

The MCP server from Project 2 is integrated into this Personal AI Infrastructure at two levels:

1. **CLAUDE.md documentation**: The MCP tools are documented in the CLAUDE.md so Claude knows about them in every session, not just when a skill explicitly invokes them
2. **`/review-asic-tool` skill**: This skill explicitly calls both MCP tools (`analyze_code_complexity` and `generate_docstrings`) as part of its four-step code review workflow

### What the MCP Server Does in This PAI

The `dev-workflow` MCP server created for Project 2 provides automated Python code analysis and documentation generation through two tools:

- **`analyze_code_complexity`**: Performs static analysis via Python's `ast` module to extract cyclomatic complexity, nesting depth, line counts, and docstring coverage metrics. In this PAI, it powers Step 1 of the `/review-asic-tool` skill, providing quantitative data that the ASIC-domain review layer then interprets against ASIC-specific quality thresholds.

- **`generate_docstrings`**: Generates Google-style docstrings using deterministic AST-based inference and inserts them directly into source files. In this PAI, it powers Step 2 of the `/review-asic-tool` skill, automatically filling documentation gaps identified during complexity analysis.

### Personal Value

The combination of automated code metrics (MCP) + ASIC-domain code review (skill) + consistent documentation generation (MCP) creates a workflow that catches quality issues specific to ASIC tools that a generic linter would miss: incorrect EDA terminology, missing unit documentation on timing values, scalability risks from non-streaming parsers, and inadequate error handling for malformed EDA output. This saves significant time during code review and ensures that Python tools intended for use in chip design flows meet the reliability standards required in that domain.

### MCP Server Configuration

The server is located in `enmgt5400-project2/` and configured for Claude Code with:

```json
{
  "mcpServers": {
    "dev-workflow": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "../enmgt5400-project2",
        "python",
        "server.py"
      ]
    }
  }
}
```

---

## Testing the Skills

All skills are invoked from Claude Code with the project root (`enmgt5400-project3/`) as the working directory. The `examples/` folder contains Python ASIC tools and sample data files for testing.

### Prerequisites

1. Claude Code CLI installed and running
2. The `dev-workflow` MCP server from Project 2 configured (see [MCP Server Configuration](#mcp-server-configuration) below) — required for `/review-asic-tool`
3. Open this project directory in Claude Code:
   ```
   cd enmgt5400-project3
   claude
   ```

### Testing `/review-asic-tool`

This skill performs a four-step code review using the MCP server's analysis tools plus ASIC-domain checks. Run it against any of the example Python files:

```
/review-asic-tool examples/sdc_parser.py
```

**What to expect**: Claude will call `analyze_code_complexity` (MCP), flag quality issues, call `generate_docstrings` (MCP) for undocumented functions, review ASIC-specific practices, and produce a structured report with a health score.

**Other test commands**:
```
/review-asic-tool examples/timing_analyzer.py
/review-asic-tool examples/netlist_utils.py
/review-asic-tool examples/                      # review the entire directory
```

**Known issues the skill should find**:
- `sdc_parser.py`: Uses `open()` instead of `pathlib`, `print()` instead of `logging` in `print_summary`, CLI uses raw `sys.argv` instead of `argparse`, missing type hints on parser methods
- `timing_analyzer.py`: Uses `os.path` instead of `pathlib`, several functions lack docstrings, no `argparse` CLI
- `netlist_utils.py`: Multiple undocumented functions, `parse_netlist` is ~60 lines with moderate complexity, hardcoded fanout port heuristic

### Testing `/validate-asic-file`

This skill validates any ASIC design file against format-specific structural and syntax rules. Pass the path to any file in `examples/`:

```
/validate-asic-file examples/valid_sdc.sdc
```

**What to expect**: Claude detects the format from the extension, loads the rules from `format-rules.md`, reads the file, checks every rule, and produces a structured report with a VALID / VALID WITH WARNINGS / INVALID verdict and line-numbered findings.

**Test the valid files (should produce VALID or VALID WITH WARNINGS)**:
```
/validate-asic-file examples/valid_sdc.sdc
/validate-asic-file examples/valid_liberty.lib
/validate-asic-file examples/valid_lef.lef
/validate-asic-file examples/valid_def.def
/validate-asic-file examples/valid_sdf.sdf
/validate-asic-file examples/valid_spef.spef
/validate-asic-file examples/valid_netlist.v
```

**Test the invalid files (should produce INVALID with specific errors)**:
```
/validate-asic-file examples/invalid_sdc.sdc
/validate-asic-file examples/invalid_liberty.lib
/validate-asic-file examples/invalid_lef.lef
/validate-asic-file examples/invalid_def.def
/validate-asic-file examples/invalid_sdf.sdf
/validate-asic-file examples/invalid_spef.spef
/validate-asic-file examples/invalid_netlist.v
```

**Known errors the skill should find in each invalid file**:
- `invalid_sdc.sdc`: missing `-period` on `create_clock`, undefined clock reference, `set_multicycle_path -setup 1`, negative `set_max_delay`
- `invalid_liberty.lib`: non-numeric `cell_leakage_power`, 3×3 index with 4-row table, unbalanced braces
- `invalid_lef.lef`: unknown `CLASS CELL`, missing `ORIGIN`, unclosed `MACRO BUFX2`, undefined layer `M3`
- `invalid_def.def`: count mismatch (declared 5, defined 3), float coordinate `2240.5`, missing `END NETS`, missing `END DESIGN`
- `invalid_sdf.sdf`: missing `(TIMESCALE ...)`, units inside timing triplets, `IOPATH` with 3 delay args, unbalanced parentheses
- `invalid_spef.spef`: missing `*L_UNIT` header, `*D_NET` block without `*END`, non-numeric capacitance, malformed `*RES` entry
- `invalid_netlist.v`: undirected port `io_clk`, undeclared wire `n_undeclared`, mixed named/positional connections in `U6`, missing `endmodule`

### Testing `/asic-tool-test`

This skill generates a pytest test framework skeleton for an ASIC tool module. Point it at any example module:

```
/asic-tool-test examples/sdc_parser.py
```

**What to expect**: Claude reads the module and generates `test_sdc_parser.py` with:
- Complete, ready-to-use fixtures (realistic SDC/Liberty/Verilog/etc. content, edge case inputs, `tmp_path` file helpers)
- Test classes organized by category (`TestParsing`, `TestErrorHandling`, `TestEdgeCases`, `TestNumericPrecision`, `TestCLI`)
- Stub test methods — each has a descriptive docstring explaining exactly what to test (Given/Then), a correct signature with the right fixtures, and `pass` as the body for you to implement

**Other test commands**:
```
/asic-tool-test examples/timing_analyzer.py
/asic-tool-test examples/netlist_utils.py
```

**After generation**: Fill in the `pass` bodies using the Given/Then descriptions as your guide, then run:
```bash
uv run pytest test_sdc_parser.py -v
```

Documentation for the MCP server implementation can be found in `enmgt5400-project2/README.md`.
