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
│       ├── gen-asic-parser/
│       │   └── SKILL.md            # Skill 2: ASIC parser scaffolding
│       └── asic-tool-test/
│           └── SKILL.md            # Skill 3: Test suite generation
├── CLAUDE.md                       # Annotated project instructions file
├── main.py                         # Project entry point
├── pyproject.toml                  # Python project configuration
├── README.md                       # This file
├── examples/
│   ├── sdc_parser.py              # Example: SDC constraint parser
│   ├── timing_analyzer.py         # Example: STA timing report analyzer
│   ├── netlist_utils.py           # Example: Verilog netlist utilities
│   ├── sample_design.sdc          # Sample SDC constraints file
│   ├── sample_design.v            # Sample gate-level Verilog netlist
│   └── sample_timing.rpt          # Sample PrimeTime-style timing report
```

---

## Testing the Skills

All skills are invoked from Claude Code with the project root (`enmgt5400-project3/`) as the working directory. The `examples/` folder contains Python ASIC tools and sample data files for testing.

### Prerequisites

1. Claude Code CLI installed and running
2. The `dev-workflow` MCP server from Project 2 configured (see [MCP Server Configuration](#mcp-server-configuration) below) — required for `/review-asic-tool`
3. Open this project directory in Claude Code:
   ```
   cd "C:\Users\parke\OneDrive - Cornell University\Desktop\ENMGT 5400\enmgt5400-project3"
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

### Testing `/gen-asic-parser`

This skill generates a complete parser file for a given ASIC file format. Pass any standard format name:

```
/gen-asic-parser SDC
```

**What to expect**: Claude will generate a full Python file with dataclass models, a `SDCParser` class, custom `ParseError` exception, and an `argparse` CLI entry point — all following the architecture defined in `CLAUDE.md`.

**Other test commands**:
```
/gen-asic-parser Liberty
/gen-asic-parser DEF
/gen-asic-parser SDF
/gen-asic-parser SPEF
/gen-asic-parser Verilog-netlist
```

**Validation**: After generating a parser, you can test it against the sample data files:
```python
# For an SDC parser:
python sdc_parser_generated.py --input examples/sample_design.sdc --format json

# For a Verilog netlist parser:
python verilog_netlist_parser.py --input examples/sample_design.v --format summary
```

### Testing `/asic-tool-test`

This skill generates a pytest test suite with ASIC-domain fixtures and edge cases. Point it at any example module:

```
/asic-tool-test examples/sdc_parser.py
```

**What to expect**: Claude will read the module, then generate a `test_sdc_parser.py` file with realistic SDC content fixtures, edge case fixtures (malformed input, escaped identifiers, Windows line endings), and tests organized by category (parsing correctness, error handling, edge cases, CLI).

**Other test commands**:
```
/asic-tool-test examples/timing_analyzer.py
/asic-tool-test examples/netlist_utils.py
```

**Validation**: Run the generated tests with pytest:
```bash
uv run pytest test_sdc_parser.py -v
uv run pytest test_timing_analyzer.py -v
uv run pytest test_netlist_utils.py -v
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
| 6 | **Behavioral Guardrails** (bonus) | Prevents common ASIC-specific failure modes (e.g., suggesting EDA tool invocation, ignoring escaped identifiers, loading huge files into memory) |

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

### Skill 2: `/gen-asic-parser` — ASIC File Format Parser Scaffolding

**Location**: `.claude/skills/gen-asic-parser/SKILL.md`

**Purpose**: Generates complete, production-ready Python parser boilerplate for any standard ASIC file format.

**How it works**: Given a format name (SDC, Liberty, LEF, DEF, SDF, SPEF, or Verilog-netlist), generates a full parser file with:
- Dataclass models for every entity in the format
- A Parser class with `parse_file()` and `parse_string()` methods
- Custom `ParseError` exception with line number tracking
- Non-strict mode by default (graceful handling of malformed EDA output)
- CLI entry point with argparse

**Example usage**: `/gen-asic-parser Liberty`

**Why this is valuable**: Parser development is the most common task in ASIC tool development. Every new project starts with "I need to parse format X." This skill saves hours of boilerplate and ensures architectural consistency across all parsers.

### Skill 3: `/asic-tool-test` — Test Suite Generation

**Location**: `.claude/skills/asic-tool-test/SKILL.md`

**Purpose**: Generates comprehensive pytest test suites with ASIC-domain-aware fixtures and edge cases.

**How it works**: Reads the target module, then generates:
- Realistic ASIC file content fixtures (valid SDC, Liberty, DEF, SDF, Verilog, SPEF snippets)
- Edge case fixtures (malformed input, escaped identifiers, huge files, Windows line endings)
- Tests organized by category: parsing correctness, error handling, edge cases, numeric precision, CLI, integration
- Parametrized tests for multiple input variations

**Example usage**: `/asic-tool-test src/sdc_parser.py`

**Why this is valuable**: The hardest part of testing ASIC tools is writing realistic test fixtures — you need domain knowledge to create valid SDC or Liberty content. This skill eliminates that bottleneck.

---

## Part 3: External Tool Integration — MCP Server

### Tool: `dev-workflow-server` (from ENMGT 5400 Project 2)

The MCP server from Project 2 is integrated into this Personal AI Infrastructure at two levels:

1. **CLAUDE.md documentation**: The MCP tools are documented in the CLAUDE.md so Claude knows about them in every session, not just when a skill explicitly invokes them
2. **`/review-asic-tool` skill**: This skill explicitly calls both MCP tools (`analyze_code_complexity` and `generate_docstrings`) as part of its four-step code review workflow

### What the MCP Server Does in This PAI

The `dev-workflow-server` provides automated Python code analysis and documentation generation through two tools:

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
        "C:\\Users\\parke\\OneDrive - Cornell University\\Desktop\\ENMGT 5400\\enmgt5400-project2",
        "python",
        "server.py"
      ]
    }
  }
}
```

Documentation for the MCP server implementation can be found in `enmgt5400-project2/README.md`.
