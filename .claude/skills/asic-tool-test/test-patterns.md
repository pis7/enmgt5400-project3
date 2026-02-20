# ASIC Test Patterns Reference

Load this file when generating test skeletons to get fixture templates and stub patterns.
Fixtures are generated complete. Test methods are generated as stubs (docstring + `pass`).

---

## Sample ASIC File Content Fixtures (generate complete)

Use these as starting points. Trim to only what is relevant to the module under test.

### SDC (`sample_sdc`)
```python
@pytest.fixture
def sample_sdc() -> str:
    """Minimal SDC with one clock, input/output delays, and a false path."""
    return """\
# Primary clock: 500 MHz
create_clock -name clk -period 2.0 -waveform {0 1.0} [get_ports clk]
# Input delay relative to clk
set_input_delay -clock clk -max 0.5 [get_ports data_in]
# Output delay relative to clk
set_output_delay -clock clk -max 0.3 [get_ports data_out]
# Asynchronous domain crossing — no timing check needed
set_false_path -from [get_clocks {clk}] -to [get_clocks {clk_io}]
"""
```

### Liberty snippet (`sample_liberty`)
```python
@pytest.fixture
def sample_liberty() -> str:
    """One Liberty cell (NAND2X1) with a single timing arc and lookup table."""
    return """\
library (sample_lib) {
  time_unit : "1ns";
  capacitive_load_unit (1, ff);
  cell (NAND2X1) {
    area : 2.0;
    pin (A) { direction : input; capacitance : 0.01; }
    pin (Y) {
      direction : output;
      timing () {
        related_pin : "A";
        timing_type : combinational;
        timing_sense : negative_unate;
        cell_rise (scalar) { values ("0.1"); }
        cell_fall (scalar) { values ("0.08"); }
      }
    }
  }
}
"""
```

### Verilog netlist (`sample_verilog`)
```python
@pytest.fixture
def sample_verilog() -> str:
    """Gate-level netlist: one module with 3 cell instances."""
    return """\
module top (clk, a, b, y);
  input clk;
  input a;
  input b;
  output y;
  wire n1;
  wire n2;
  NAND2X1 U1 (.A(a), .B(b), .Y(n1));   // NAND gate
  INVX1   U2 (.A(n1), .Y(n2));           // inverter
  DFFX1   U3 (.D(n2), .CK(clk), .Q(y)); // flip-flop
endmodule
"""
```

### SDF snippet (`sample_sdf`)
```python
@pytest.fixture
def sample_sdf() -> str:
    """SDF with one cell, one IOPATH, and a SETUP check."""
    return """\
(DELAYFILE
  (SDFVERSION "3.0")
  (DESIGN "top")
  (TIMESCALE 1ns)
  (CELL
    (CELLTYPE "NAND2X1")
    (INSTANCE U1)
    (DELAY
      (ABSOLUTE
        (IOPATH A Y (0.10:0.12:0.15) (0.08:0.10:0.13))
      )
    )
    (TIMINGCHECK
      (SETUP D (posedge CK) (0.05:0.06:0.07))
    )
  )
)
"""
```

### SPEF snippet (`sample_spef`)
```python
@pytest.fixture
def sample_spef() -> str:
    """SPEF with one net and a simple RC pi-model."""
    return """\
*SPEF "IEEE 1481-1998"
*DESIGN "top"
*T_UNIT 1 NS
*C_UNIT 1 FF
*R_UNIT 1 OHM
*D_NET n1 0.050
*CONN
*D U1:Y
*L U2:A
*CAP
1 U1:Y 0.020
2 U2:A 0.030
*RES
1 U1:Y U2:A 2.500
*END
"""
```

## Edge Case Fixtures (generate complete)

```python
@pytest.fixture
def malformed_sdc() -> str:
    """SDC with a syntax error: create_clock missing -period."""
    return "create_clock [get_ports clk]\n"  # missing -period argument

@pytest.fixture
def windows_line_endings(sample_sdc) -> str:
    """Valid SDC content with Windows-style CRLF line endings."""
    return sample_sdc.replace("\n", "\r\n")

@pytest.fixture
def backslash_escaped_names() -> str:
    """Verilog netlist with backslash-escaped identifiers (trailing space required)."""
    return """\
module top ();
  wire \\bus[0] ;   // escaped identifier — trailing space before semicolon
  INVX1 \\U/inst  (.A(\\bus[0] ), .Y(out));
endmodule
"""

@pytest.fixture
def empty_file(tmp_path) -> Path:
    """An empty file (0 bytes) for boundary testing."""
    f = tmp_path / "empty.sdc"
    f.write_text("")
    return f

@pytest.fixture
def sample_file(tmp_path, sample_sdc) -> Path:
    """Write sample SDC content to a temp file and return its path."""
    f = tmp_path / "design.sdc"
    f.write_text(sample_sdc)
    return f
```

---

## Test Stub Templates (generate with docstring + `pass`)

Every test method follows this pattern:
```python
def test_<category>_<what>_<condition>(self, <fixtures>):
    """<One-sentence summary of what is verified.>

    Given: <preconditions and setup>
    Then:  <concrete assertion — name the expected value or behavior>
    """
    pass
```

### TestParsing stubs
```python
class TestParsing:
    def test_parse_returns_correct_type(self, sample_file, parser):
        """Verify parse_file returns an instance of the correct top-level dataclass.

        Given: a valid SDC file written to tmp_path
        Then:  isinstance(result, <TopLevelClass>) is True
        """
        pass

    def test_parse_extracts_clock_count(self, sample_file, parser):
        """Verify the correct number of clocks is parsed from the file.

        Given: sample_file contains exactly one create_clock statement
        Then:  len(result.clocks) == 1
        """
        pass

    def test_parse_extracts_clock_period(self, sample_file, parser):
        """Verify the clock period value is correctly extracted.

        Given: sample_file defines clk with -period 2.0
        Then:  result.clocks[0].period == pytest.approx(2.0)
        """
        pass

    @pytest.mark.parametrize("period,name", [
        (2.0, "clk"),
        (5.0, "clk_io"),
        (8.0, "clk_slow"),
    ])
    def test_parse_multiple_clock_periods(self, tmp_path, parser, period, name):
        """Verify period and name are correctly extracted for various create_clock inputs.

        Given: a single-line SDC string with -period <period> and -name <name>
        Then:  result.clocks[0].period == pytest.approx(period)
               result.clocks[0].name == name
        """
        pass

    def test_parse_string_equivalent_to_parse_file(self, sample_sdc, sample_file, parser):
        """Verify parse_string and parse_file produce identical results.

        Given: sample_sdc string and sample_file contain the same content
        Then:  parse_string(sample_sdc) equals parse_file(sample_file) in all fields
        """
        pass
```

### TestErrorHandling stubs
```python
class TestErrorHandling:
    def test_strict_mode_raises_parse_error(self, tmp_path, malformed_sdc):
        """Verify strict mode raises ParseError on malformed input.

        Given: a file containing malformed_sdc (create_clock missing -period)
               and a parser created with strict=True
        Then:  parser.parse_file raises ParseError
        """
        pass

    def test_strict_mode_error_includes_line_number(self, tmp_path, malformed_sdc):
        """Verify the raised ParseError includes a non-zero line number.

        Given: same setup as test_strict_mode_raises_parse_error
        Then:  exc_info.value.line_num > 0
        """
        pass

    def test_lenient_mode_logs_warning(self, tmp_path, malformed_sdc, caplog):
        """Verify lenient mode logs a WARNING and returns partial results instead of raising.

        Given: a file containing malformed_sdc and a parser with strict=False
        Then:  at least one WARNING record is emitted
               result is not None
        """
        pass

    def test_file_not_found_raises(self, tmp_path):
        """Verify FileNotFoundError is raised for a non-existent path.

        Given: a path that does not exist on disk
        Then:  parser.parse_file raises FileNotFoundError
        """
        pass

    def test_empty_file_returns_empty_model(self, empty_file):
        """Verify an empty file returns a valid but empty top-level model.

        Given: a zero-byte file
        Then:  result is not None and all collection fields have length 0
        """
        pass
```

### TestEdgeCases stubs
```python
class TestEdgeCases:
    def test_windows_line_endings_parsed_correctly(self, tmp_path, windows_line_endings):
        """Verify the parser handles CRLF line endings without error.

        Given: valid SDC content with \\r\\n line endings written to a temp file
        Then:  result is not None and contains the expected clock
        """
        pass

    def test_backslash_escaped_identifiers(self, tmp_path, backslash_escaped_names):
        """Verify backslash-escaped Verilog identifiers are preserved including trailing space.

        Given: a Verilog netlist with \\bus[0]  (note trailing space in source)
        Then:  the parsed identifier is exactly '\\bus[0] ' (with trailing space)
        """
        pass

    def test_inline_comments_ignored(self, tmp_path):
        """Verify that # comments in SDC (or ; comments in SDF) do not affect parsed output.

        Given: a file where every data line has a trailing comment
        Then:  result is identical to parsing the same file without comments
        """
        pass

    @pytest.mark.slow
    def test_large_file_completes_within_time_limit(self, tmp_path):
        """Verify the parser handles 100 k-line files in under 10 seconds.

        Given: a file with 100 000 identical valid lines written to tmp_path
        Then:  time.perf_counter() elapsed < 10.0 seconds
        """
        pass
```

### TestNumericPrecision stubs
```python
class TestNumericPrecision:
    def test_timing_value_float_precision(self, sample_file, parser):
        """Verify floating-point timing values are preserved to nanosecond precision.

        Given: sample_file with a clock period of 2.0 ns
        Then:  result.clocks[0].period == pytest.approx(2.0, abs=1e-9)
        """
        pass

    def test_negative_delay_allowed(self, tmp_path):
        """Verify negative timing values (e.g., hold margins) parse without error.

        Given: a file with set_input_delay -min -0.050 [get_ports din]
        Then:  the parsed min_delay value == pytest.approx(-0.050, abs=1e-9)
        """
        pass
```

### TestCLI stubs
```python
class TestCLI:
    def test_cli_json_output_is_valid(self, tmp_path, sample_file, capsys):
        """Verify --format json produces valid JSON on stdout.

        Given: sample_file passed to the CLI with --format json
        Then:  json.loads(captured stdout) succeeds without raising
        """
        pass

    def test_cli_missing_input_exits_nonzero(self, tmp_path, capsys):
        """Verify the CLI exits with a non-zero code when --input is missing.

        Given: CLI invoked without --input argument
        Then:  SystemExit is raised with code != 0
        """
        pass

    def test_cli_strict_flag_propagates(self, tmp_path, malformed_sdc, capsys):
        """Verify --strict causes the CLI to exit non-zero on malformed input.

        Given: malformed_sdc written to a file, CLI invoked with --strict
        Then:  SystemExit raised with code != 0
        """
        pass
```
