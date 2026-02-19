# ASIC Test Patterns Reference

Load this file when generating test suites to get fixture templates and test patterns.

## Sample ASIC File Content Fixtures

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
*I U1:Y O
*I U2:A I
*CAP
1 U1:Y 0.020
2 U2:A 0.030
*RES
1 U1:Y U2:A 2.500
*END
"""
```

## Edge Case Fixtures

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

## Test Class Templates

### TestParsing
```python
class TestParsing:
    def test_parse_returns_correct_type(self, sample_file, parser):
        result = parser.parse_file(sample_file)
        assert isinstance(result, ExpectedTopLevelType)

    def test_parse_extracts_clock_period(self, sample_file, parser):
        result = parser.parse_file(sample_file)
        assert len(result.clocks) == 1
        assert result.clocks[0].period == pytest.approx(2.0)

    @pytest.mark.parametrize("line,expected_name", [
        ("create_clock -name clk -period 2.0 [get_ports clk]", "clk"),
        ("create_clock -period 5.0 [get_ports io_clk]", "io_clk"),
    ])
    def test_parse_clock_name_extracted(self, line, expected_name, parser):
        result = parser.parse_string(line)
        assert result.clocks[0].name == expected_name
```

### TestErrorHandling
```python
class TestErrorHandling:
    def test_strict_mode_raises_with_line_number(self, tmp_path, malformed_sdc):
        f = tmp_path / "bad.sdc"
        f.write_text(malformed_sdc)
        parser = SDCParser(strict=True)
        with pytest.raises(ParseError) as exc_info:
            parser.parse_file(f)
        assert exc_info.value.line_num > 0, "ParseError must include line number"

    def test_lenient_mode_logs_warning(self, tmp_path, malformed_sdc, caplog):
        f = tmp_path / "bad.sdc"
        f.write_text(malformed_sdc)
        parser = SDCParser(strict=False)
        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(f)
        assert any("WARNING" in r.levelname for r in caplog.records)
        assert result is not None, "Lenient mode should return partial results"

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            SDCParser().parse_file(tmp_path / "nonexistent.sdc")

    def test_empty_file_returns_empty_model(self, empty_file):
        result = SDCParser().parse_file(empty_file)
        assert result is not None
        assert len(result.clocks) == 0
```

### TestEdgeCases
```python
class TestEdgeCases:
    def test_windows_line_endings(self, tmp_path, windows_line_endings):
        f = tmp_path / "crlf.sdc"
        f.write_bytes(windows_line_endings.encode())
        result = SDCParser().parse_file(f)
        assert len(result.clocks) >= 1, "Should parse despite CRLF endings"

    def test_backslash_escaped_identifiers(self, tmp_path, backslash_escaped_names):
        f = tmp_path / "escaped.v"
        f.write_text(backslash_escaped_names)
        # Parser must not crash on escaped identifiers
        result = VerilogParser().parse_file(f)
        assert result is not None

    @pytest.mark.slow
    def test_large_file_performance(self, tmp_path):
        """Parser handles 100 k-line files in under 10 seconds."""
        import time
        content = "create_clock -name clk -period 2.0 [get_ports clk]\n" * 100_000
        f = tmp_path / "large.sdc"
        f.write_text(content)
        start = time.perf_counter()
        SDCParser().parse_file(f)
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"Parsing took {elapsed:.1f}s, expected < 10s"
```

### TestNumericPrecision
```python
class TestNumericPrecision:
    def test_timing_value_float_precision(self, sample_file, parser):
        result = parser.parse_file(sample_file)
        assert result.clocks[0].period == pytest.approx(2.0, abs=1e-9)

    def test_negative_slack_allowed(self, tmp_path):
        """Negative timing values (hold violations) must parse without error."""
        content = "set_input_delay -clock clk -min -0.050 [get_ports din]\n"
        f = tmp_path / "neg.sdc"
        f.write_text(content)
        result = SDCParser().parse_file(f)
        assert result.io_delays[0].min_delay == pytest.approx(-0.050, abs=1e-9)
```
