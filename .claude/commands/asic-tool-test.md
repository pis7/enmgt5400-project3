# Generate ASIC Tool Test Suite

Generate a comprehensive `pytest` test suite for the following Python ASIC tool or module: $ARGUMENTS

Read the target file first to understand its functionality, then generate a complete test file.

## Test File Structure

Generate a test file named `test_<module_name>.py` in the same directory as the target module (or in a `tests/` directory if one exists).

## Section 1: Imports and Configuration

```python
"""Tests for <module_name>.

Tests cover parsing correctness, error handling, edge cases, and CLI behavior
for ASIC design file processing.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

# Import the module under test
from <module_name> import <relevant classes and functions>
```

Include a suggested `pyproject.toml` addition as a comment at the top:

```python
# Add to pyproject.toml:
# [tool.pytest.ini_options]
# markers = [
#     "slow: marks tests as slow (deselect with '-m \"not slow\"')",
# ]
# testpaths = ["tests"]
```

## Section 2: Fixtures

Generate pytest fixtures for ASIC-domain test data. Every fixture must have a docstring explaining what it provides.

### Sample File Content Fixtures

Create fixtures with realistic but minimal (5-20 lines) ASIC file content as multi-line strings. Include inline comments explaining what each line represents. Generate only the fixtures relevant to the module being tested:

- **`sample_sdc`**: A minimal SDC file with `create_clock` (defining a 10ns clock), `set_input_delay`, `set_output_delay`, and `set_false_path` commands
- **`sample_liberty_snippet`**: A Liberty cell entry with a pin, timing arc, and a small lookup table
- **`sample_def_snippet`**: A DEF file with COMPONENTS (2-3 placed cells), NETS (2-3 routed nets), and SPECIALNETS (VDD/VSS)
- **`sample_sdf_snippet`**: An SDF file with IOPATH and SETUP/HOLD timing check entries
- **`sample_verilog_netlist`**: A small gate-level netlist with 3-4 cell instances (NAND, NOR, INV, etc.)
- **`sample_spef_snippet`**: A SPEF file with one net and its RC parasitic tree

### Temporary File Fixtures

Using `tmp_path`:
- **`sample_file`**: Write the relevant sample content to a temp file and return its path
- **`sample_directory`**: Create a temp directory with multiple sample files for directory-mode testing
- **`empty_file`**: An empty file (0 bytes)

### Edge Case Fixtures

- **`malformed_content`**: Content with syntax errors (missing arguments, unclosed braces, invalid values)
- **`windows_line_endings`**: Same valid content but with `\r\n` line endings
- **`backslash_escaped_names`**: Content with Verilog escaped identifiers like `\some/weird:name `
- **`huge_content`**: A parametrized fixture that generates a large synthetic file (e.g., 100,000 lines of repetitive valid entries) for performance testing — mark with `@pytest.mark.slow`
- **`unicode_comments`**: Content with Unicode characters in comments (common in Asian design teams)
- **`long_lines`**: Content with lines exceeding 10,000 characters (some EDA tools produce these)

## Section 3: Test Categories

### Parsing Correctness Tests (`class TestParsing`)

Test that valid input produces expected data model instances:

```python
def test_parse_returns_correct_type(self, sample_file):
    """Parser returns the expected top-level model type."""

def test_parse_extracts_<key_field>(self, sample_file):
    """Parser correctly extracts <key field> from input."""
    # Example: clock period, delay value, cell name, net name, etc.

def test_parse_count_<entities>(self, sample_file):
    """Parser finds the expected number of <entities> in sample input."""

def test_parse_<specific_construct>(self, sample_file):
    """Parser correctly handles <specific construct> syntax."""
    # Example: multi-line continuation, nested groups, escaped identifiers

def test_parse_round_trip(self, sample_file):
    """Parse -> serialize -> parse produces identical results."""
    # Only if the module has a write/dump method
```

Use `@pytest.mark.parametrize` where testing multiple input variations:
```python
@pytest.mark.parametrize("input_line,expected", [
    ("create_clock -period 10 [get_ports clk]", ClockConstraint(period=10.0, ...)),
    ("set_false_path -from [get_clocks clkA] -to [get_clocks clkB]", ...),
])
def test_parse_sdc_commands(self, input_line, expected):
    ...
```

### Error Handling Tests (`class TestErrorHandling`)

```python
def test_strict_mode_raises_on_malformed_input(self, malformed_content, tmp_path):
    """Strict mode raises ParseError with correct line number."""
    # Assert that ParseError is raised
    # Assert that the line_num attribute is correct
    # Assert that the error message is descriptive

def test_lenient_mode_skips_malformed_entries(self, malformed_content, tmp_path, caplog):
    """Lenient mode logs warning and continues parsing."""
    # Assert that no exception is raised
    # Assert that a WARNING was logged
    # Assert that valid entries were still parsed

def test_file_not_found_raises(self, tmp_path):
    """Attempting to parse a nonexistent file raises FileNotFoundError."""

def test_empty_file_returns_empty_model(self, empty_file):
    """Parsing an empty file returns an empty but valid model."""

def test_wrong_extension_rejected(self, tmp_path):
    """Parser rejects files with unexpected extensions (if applicable)."""
```

### Edge Case Tests (`class TestEdgeCases`)

```python
def test_windows_line_endings(self, windows_line_endings, tmp_path):
    """Parser handles \\r\\n line endings correctly."""

def test_backslash_escaped_identifiers(self, backslash_escaped_names, tmp_path):
    """Parser correctly handles Verilog backslash-escaped identifiers."""

def test_unicode_in_comments(self, unicode_comments, tmp_path):
    """Parser handles Unicode characters in comments without errors."""

def test_long_lines(self, long_lines, tmp_path):
    """Parser handles lines exceeding 10,000 characters."""

def test_only_comments_and_whitespace(self, tmp_path):
    """Parser handles files containing only comments and blank lines."""

@pytest.mark.slow
def test_large_file_performance(self, huge_content, tmp_path):
    """Parser handles 100k+ line files without excessive memory or time."""
    import time
    start = time.perf_counter()
    result = parser.parse_file(large_file)
    elapsed = time.perf_counter() - start
    assert elapsed < 10.0, f"Parsing took {elapsed:.1f}s, expected < 10s"
```

### Numeric Precision Tests (`class TestNumericPrecision`)

For parsers that handle timing/physical values:

```python
def test_timing_value_precision(self, sample_file):
    """Timing values are parsed with sufficient floating-point precision."""
    # Use pytest.approx() for comparisons
    assert result.delay == pytest.approx(0.123, abs=1e-6)

def test_min_typ_max_triplet(self, sample_file):
    """SDF-style (min:typ:max) triplets are parsed into all three fields."""

def test_negative_timing_values(self, tmp_path):
    """Negative delay values (e.g., hold violations) are handled correctly."""
```

### CLI Tests (`class TestCLI`) — if the module has a CLI entry point

```python
def test_cli_help_exits_cleanly(self):
    """--help flag exits with code 0."""
    result = subprocess.run([sys.executable, module_path, "--help"],
                           capture_output=True, text=True)
    assert result.returncode == 0

def test_cli_valid_input(self, sample_file):
    """CLI with valid input file produces expected output."""

def test_cli_missing_input(self):
    """CLI with missing input file produces clean error message."""

def test_cli_strict_flag(self, malformed_content, tmp_path):
    """--strict flag causes CLI to exit with non-zero code on parse errors."""

def test_cli_json_output(self, sample_file):
    """--format json produces valid JSON output."""
    # Parse the stdout as JSON and verify structure

def test_cli_output_file(self, sample_file, tmp_path):
    """--output writes to the specified file instead of stdout."""
```

### Integration Tests (`class TestIntegration`) — if applicable

```python
def test_full_pipeline(self, sample_file):
    """Full pipeline: read file -> parse -> transform -> validate output."""

def test_multiple_files_in_directory(self, sample_directory):
    """Parser handles a directory of files (if directory mode is supported)."""
```

## Section 4: Test Naming and Organization

- Name pattern: `test_<category>_<what>_<condition>`
  - Example: `test_parse_sdc_clock_period_extracted`
  - Example: `test_error_strict_mode_raises_on_malformed`
  - Example: `test_edge_backslash_escaped_identifiers`
- Group related tests in classes: `class TestParsing:`, `class TestErrorHandling:`, etc.
- Every test must be independent — no shared mutable state between tests
- Fixtures should use `tmp_path` for any file I/O — never write to the source tree
- Include descriptive assertion messages: `assert len(result.cells) == 3, f"Expected 3 cells, got {len(result.cells)}"`

## Important Guidelines

- Read the target module FIRST before generating tests — test what actually exists, not what you assume
- Generate only test categories relevant to the module's actual functionality
- Sample ASIC file content must be syntactically realistic — use actual format syntax, not placeholders
- Every fixture must include inline comments explaining what the sample data represents
- Use `pytest.approx()` for all floating-point comparisons (timing values, capacitances, etc.)
- Mark slow tests with `@pytest.mark.slow`
- Use `caplog` fixture to verify logging behavior in lenient mode
- Use `tmp_path` for all temporary file creation — never write to the project directory during tests
