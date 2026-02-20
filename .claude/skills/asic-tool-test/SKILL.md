---
name: asic-tool-test
description: Generates a pytest test framework skeleton for Python ASIC tools. Produces complete fixtures and infrastructure, plus test method stubs with docstrings describing what to test — but leaves the test bodies empty for the user to implement. Use when scaffolding tests for code that parses or processes ASIC design files.
argument-hint: <python-file-path>
disable-model-invocation: true
---

Generate a pytest test framework skeleton for the following Python ASIC tool or module: $ARGUMENTS

**Read the target file first.** Generate only what applies to its actual functionality — do not invent stubs for things that don't exist in the code.

Do not generate a huge number of stubs — focus on the most important test cases that cover the core functionality, edge cases, and error handling. The goal is to reduce the amount of time the model needs to spend on this task while still providing a useful scaffold for the user to fill in.

Consult [test-patterns.md](test-patterns.md) for fixture templates and stub patterns before generating code.

## Required Output

Generate `test_<module_name>.py` alongside the target file.

The file has two parts:
1. **Infrastructure** — complete and ready to use: imports, conftest-style fixtures, helper constants
2. **Test stubs** — grouped into test classes with one method per test case; each method has a descriptive docstring and a `pass` body

### File header

```python
# Add to pyproject.toml:
# [tool.pytest.ini_options]
# markers = ["slow: marks tests as slow (deselect with '-m \"not slow\"')"]
# testpaths = ["tests"]
```

### Fixtures (complete — do not stub these)

- Use `tmp_path` for all file I/O — never write to the source tree
- Every fixture needs a docstring
- Include inline comments in sample ASIC content explaining each line
- Generate only fixtures relevant to the module being tested — consult [test-patterns.md](test-patterns.md) for sample content

### Test stubs

Group stubs into classes: `TestParsing`, `TestErrorHandling`, `TestEdgeCases`, `TestNumericPrecision`, `TestCLI`, `TestIntegration` — include only classes relevant to the module.

Each test method must:
- Have a descriptive name: `test_<category>_<what>_<condition>`
- Have a docstring with three parts:
  1. One-sentence summary of what the test verifies
  2. **Given**: the preconditions / setup needed
  3. **Then**: the specific assertion(s) to make (be concrete — name the expected value or behavior)
- Have `pass` as its only body statement

### Decorators on stubs

Apply the decorator above the `def`, just like a real test, so the user only needs to add the body:
- `@pytest.mark.slow` on performance/large-file stubs
- `@pytest.mark.parametrize(...)` on stubs that should test multiple input variations — include realistic parameter values in the decorator even though the body is `pass`
