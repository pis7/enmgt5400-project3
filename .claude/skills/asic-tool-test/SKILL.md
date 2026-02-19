---
name: asic-tool-test
description: Generates comprehensive pytest test suites for Python ASIC tools, with realistic EDA file format fixtures and domain-specific edge cases. Use when writing tests for code that parses or processes ASIC design files.
argument-hint: <python-file-path>
disable-model-invocation: true
---

Generate a comprehensive `pytest` test suite for the following Python ASIC tool or module: $ARGUMENTS

**Read the target file first.** Generate only what applies to its actual functionality — do not invent tests for things that don't exist in the code.

Consult [test-patterns.md](test-patterns.md) for fixture templates and test category patterns before generating code.

## Required Output

Generate `test_<module_name>.py` alongside the target file (or in `tests/` if that directory exists).

### File header

Include this `pyproject.toml` snippet as a comment at the top of the test file:

```python
# Add to pyproject.toml:
# [tool.pytest.ini_options]
# markers = ["slow: marks tests as slow (deselect with '-m \"not slow\"')"]
# testpaths = ["tests"]
```

### Fixtures

- Use `tmp_path` for all file I/O — never write to the source tree
- Every fixture needs a docstring
- Include inline comments in sample ASIC content explaining each line
- Generate only fixtures relevant to the module being tested — consult [test-patterns.md](test-patterns.md) for sample content

### Test classes

Group tests by: `TestParsing`, `TestErrorHandling`, `TestEdgeCases`, `TestNumericPrecision`, `TestCLI`, `TestIntegration` — include only classes relevant to the module.

### Naming

`test_<category>_<what>_<condition>` — e.g. `test_parse_clock_period_extracted`, `test_error_strict_raises_on_malformed`, `test_edge_windows_line_endings`.

## Rules

- `pytest.approx()` for all floating-point comparisons (timing values, capacitances)
- `caplog` fixture to assert log levels in lenient-mode tests
- `@pytest.mark.slow` on performance/large-file tests
- `@pytest.mark.parametrize` for testing multiple input variations of the same logic
- Descriptive assertion messages: `assert len(x) == 3, f"Expected 3, got {len(x)}"`
- Every test must be independent — no shared mutable state
