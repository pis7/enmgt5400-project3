# Generate ASIC File Format Parser

Generate a complete Python parser for the following ASIC file format: $ARGUMENTS

The argument should be one of: **SDC**, **LEF**, **DEF**, **Liberty**, **SDF**, **SPEF**, **Verilog-netlist**, or a custom format description.

## Output Structure

Generate a single Python file following the project's standard parser architecture. The file should be production-ready and follow all coding standards from CLAUDE.md.

## Section 1: File Header

Include at the top of the file:

```python
"""
<Format> file parser for ASIC design workflows.

Parses <format description> files and produces structured Python objects
for downstream analysis and transformation.

Example usage:
    # Command line:
    python <format>_parser.py --input design.ext --format json

    # Python API:
    parser = <Format>Parser()
    result = parser.parse_file(Path("design.ext"))

Example input (first few representative lines of the format):
    <3-5 lines showing key format syntax>

Example parsed output:
    <brief JSON or repr showing what the parser produces>
"""
```

## Section 2: Data Models

Create `@dataclass` classes for each entity in the format. Follow these rules:

- Every field must have a type annotation
- Include a docstring describing the ASIC concept the model represents
- Add `__post_init__` validation for fields with known constraints (e.g., timing values must be non-negative, pin directions must be "input"/"output"/"inout")
- Include a `__repr__` that shows the most important identifying fields
- Add `__all__` at module level exporting all public classes

### Format-Specific Data Models

**SDC**: `ClockConstraint` (name, period, waveform, source), `IODelay` (pin, clock, delay_value, type), `TimingException` (type, from_pins, to_pins), `SDCConstraintSet` (clocks, io_delays, exceptions)

**Liberty**: `LookupTable` (index_1, index_2, values), `TimingArc` (related_pin, timing_type, timing_sense, cell_rise, cell_fall), `Pin` (name, direction, capacitance, timing_arcs), `Cell` (name, area, pins), `LibertyLibrary` (name, cells, time_unit, capacitance_unit)

**LEF**: `LEFLayer` (name, type, pitch, width), `LEFPin` (name, direction, shape, port_geometries), `Obstruction` (layer, rectangles), `Macro` (name, class_type, size, origin, pins, obstructions), `LEFLibrary` (layers, macros, sites)

**DEF**: `Component` (name, cell_name, placement, orientation), `NetConnection` (instance, pin), `Net` (name, connections), `SpecialNet` (name, use, routing), `DEFDesign` (name, units, die_area, rows, components, nets, special_nets)

**SDF**: `DelayValue` (min_val, typ_val, max_val), `IOPath` (input_port, output_port, rise_delay, fall_delay), `TimingCheck` (check_type, port, related_port, value), `SDFCell` (cell_type, instance, io_paths, timing_checks), `SDFFile` (sdf_version, design, cells)

**SPEF**: `ParasiticNode` (name, capacitance), `ParasiticResistor` (node1, node2, resistance), `SPEFNet` (name, total_cap, connections, caps, resistors), `SPEFFile` (design, time_unit, cap_unit, res_unit, nets)

**Verilog Netlist**: `PortConnection` (port_name, net_name), `CellInstance` (instance_name, cell_type, connections), `Wire` (name, width), `Module` (name, ports, wires, instances)

## Section 3: Custom Exception

```python
class ParseError(Exception):
    """Error encountered while parsing an ASIC file format.

    Attributes:
        line_num: Line number where the error occurred (1-indexed).
        line_text: The content of the offending line.
        message: Description of what went wrong.
    """

    def __init__(self, message: str, line_num: int = 0, line_text: str = ""):
        self.line_num = line_num
        self.line_text = line_text
        self.message = message
        super().__init__(f"Line {line_num}: {message}")
```

## Section 4: Parser Class

```python
class <Format>Parser:
    """Parser for <format> files used in ASIC design flows.

    Supports both strict and lenient parsing modes. In lenient mode (default),
    malformed entries are logged as warnings and skipped — this is the right
    default because real EDA tool output is frequently non-conformant.

    Args:
        strict: If True, raise ParseError on any parse error.
                If False (default), log warnings and skip malformed entries.
    """

    def __init__(self, strict: bool = False):
        ...

    def parse_file(self, path: Path) -> <TopLevelModel>:
        """Parse a <format> file from disk.

        Uses line-by-line reading for large file support.

        Args:
            path: Path to the input file.

        Returns:
            Parsed <TopLevelModel> containing all extracted data.

        Raises:
            FileNotFoundError: If the input file does not exist.
            ParseError: If strict mode is enabled and a parse error occurs.
        """
        ...

    def parse_string(self, content: str) -> <TopLevelModel>:
        """Parse <format> content from a string.

        Useful for testing and for processing content already in memory.

        Args:
            content: The full text content to parse.

        Returns:
            Parsed <TopLevelModel> containing all extracted data.
        """
        ...
```

### Parsing Strategy by Format

- **SDC**: Line-oriented. Use `re` to match Tcl commands. Handle backslash line continuation and `#` comments. Commands: `create_clock`, `set_input_delay`, `set_output_delay`, `set_false_path`, `set_multicycle_path`, `set_max_delay`, `set_clock_groups`.
- **Liberty**: Hierarchical nested groups. Use a state machine or `pyparsing` grammar. Track brace depth. Handle quoted string values and lookup table arrays.
- **LEF**: Section-oriented with semicolon-terminated statements. Use a state machine tracking current MACRO/PIN/OBS context. Handle `END <name>` delimiters.
- **DEF**: Section-oriented with semicolon-terminated statements. Sections delimited by keywords like `COMPONENTS ... END COMPONENTS`. Handle large NETS sections with streaming.
- **SDF**: S-expression-like parenthesized syntax. Use recursive descent or `pyparsing`. Handle `(min:typ:max)` delay triplets.
- **SPEF**: Line-oriented with section headers (`*D_NET`, `*CONN`, `*CAP`, `*RES`). Use `re` for structured lines. Handle hierarchical instance names with `/` separator.
- **Verilog Netlist**: Statement-oriented (semicolon-terminated). Use a state machine for `module`/`endmodule` blocks. Handle backslash-escaped identifiers with trailing space. Handle port connections by name `.port(net)` and by position.

## Section 5: CLI Entry Point

```python
if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser(
        description="Parse <format> files from ASIC design flows."
    )
    arg_parser.add_argument("-i", "--input", required=True, type=Path,
                            help="Input <format> file path")
    arg_parser.add_argument("-o", "--output", type=Path, default=None,
                            help="Output file path (default: stdout)")
    arg_parser.add_argument("--format", choices=["json", "summary"],
                            default="summary",
                            help="Output format (default: summary)")
    arg_parser.add_argument("--strict", action="store_true",
                            help="Enable strict parsing (raise on errors)")
    arg_parser.add_argument("-v", "--verbose", action="store_true",
                            help="Enable debug logging")

    args = arg_parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    parser = <Format>Parser(strict=args.strict)
    result = parser.parse_file(args.input)

    # Output handling: json serialization or summary format
    # Write to --output file or stdout
```

## Important Guidelines

- Use `re` for simple line-oriented formats (SDC, SDF, SPEF)
- Use `pyparsing` or a state machine for nested/hierarchical formats (Liberty, LEF/DEF)
- For Verilog netlists, use a state machine — the grammar is complex but the gate-level subset is predictable
- Always handle backslash-escaped identifiers: `\name ` (trailing space is significant)
- Support both Unix (`\n`) and Windows (`\r\n`) line endings
- Use `pathlib.Path`, never raw string path manipulation
- Include `__all__` to define the module's public API
- Add `from __future__ import annotations` at the top for forward reference support
- Log at DEBUG level during parsing for troubleshooting; WARNING for skipped entries; ERROR for unrecoverable issues
