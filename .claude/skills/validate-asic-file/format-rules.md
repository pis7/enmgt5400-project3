# ASIC File Format Validation Rules

Rules applied by the `/validate-asic-file` skill. Each section covers one format.
Labels: **REQUIRED** = ERROR on violation (file is invalid); **RECOMMENDED** = WARNING on violation.

---

## SDC (Synopsys Design Constraints)

### Structural Rules
- **REQUIRED**: Every `create_clock` must include `-period` with a positive numeric value (ns)
- **REQUIRED**: `-period` value must be > 0
- **REQUIRED**: `set_input_delay` and `set_output_delay` must include `-clock <name>`
- **REQUIRED**: `set_multicycle_path -setup N` requires N ≥ 2; N = 0 or N = 1 is an error
- **REQUIRED**: `set_false_path` must include at least one of `-from`, `-to`, or `-through`
- **REQUIRED**: `set_max_delay` and `set_min_delay` delay values must be > 0
- **REQUIRED**: Backslash line continuation (`\`) must be the last character on the line — no trailing whitespace after `\`
- **REQUIRED**: All `-clock <name>` references must name a clock previously declared with `create_clock` (no forward references)
- **RECOMMENDED**: Every `create_clock` should include an explicit `-waveform` definition
- **RECOMMENDED**: `set_clock_uncertainty` should appear for each defined clock
- **RECOMMENDED**: Asynchronous clock domain crossings should be covered by `set_clock_groups -asynchronous` or `set_false_path`
- **RECOMMENDED**: For each port/clock pair, `set_input_delay -max` should be ≥ `set_input_delay -min`

### Common Errors
- Clock period of 0.0 or negative
- Referencing a clock before it is defined
- `set_multicycle_path 1` — redundant and usually a typo for a larger multiplier
- Missing `-clock` on `set_input_delay` applied to a non-combinational path

---

## Liberty (.lib / .liberty)

### Structural Rules
- **REQUIRED**: File must begin with `library (<name>) {` at the top level
- **REQUIRED**: Opening and closing braces `{ }` must be balanced (every `{` has a matching `}`)
- **REQUIRED**: Each `cell` group must contain at least one `pin` group
- **REQUIRED**: Each `pin` group must include a `direction` attribute (`input`, `output`, `inout`, or `internal`)
- **REQUIRED**: Each `timing` group must include `timing_type` and at least one delay table (`cell_rise`, `cell_fall`, `rise_transition`, or `fall_transition`)
- **REQUIRED**: Delay table index dimensions (`index_1` length × `index_2` length) must match the number of rows and columns in the `values` table
- **REQUIRED**: `cell_leakage_power` must be a non-negative numeric value
- **REQUIRED**: Numeric attributes must contain actual numbers (not bare strings)
- **RECOMMENDED**: Each `cell` should include a `cell_leakage_power` attribute
- **RECOMMENDED**: Each output `pin` should have a `max_capacitance` attribute
- **RECOMMENDED**: `timing_sense` should be present on every `timing` group

### Common Errors
- Unbalanced braces (most frequent Liberty error)
- Index table dimension mismatch (3 index points but 4 data rows)
- Non-numeric leakage power value
- Missing `timing_type` in a `timing` group

---

## LEF (Library Exchange Format)

### Structural Rules
- **REQUIRED**: File must contain a `VERSION` statement before any `MACRO` definitions
- **REQUIRED**: Every `MACRO <name>` block must end with `END <name>` (names must match exactly)
- **REQUIRED**: Every `MACRO` must include `CLASS`, `ORIGIN`, `SIZE`, and `SYMMETRY` statements
- **REQUIRED**: Every `PIN <name>` within a MACRO must end with `END <name>`
- **REQUIRED**: Every `OBS` block must end with `END`
- **REQUIRED**: `CLASS` value must be one of the standard LEF class keywords: `CORE`, `CORE FEEDTHRU`, `CORE TIEHIGH`, `CORE TIELOW`, `CORE WELLTAP`, `PAD`, `PAD INPUT`, `PAD OUTPUT`, `PAD INOUT`, `PAD POWER`, `ENDCAP`, `BLOCK`, `COVER`, `RING`, `SPACER`, `ANTENNA`
- **REQUIRED**: `SIZE <width> BY <height>` values must be positive floating-point numbers
- **REQUIRED**: `LAYER` references inside `PORT` geometries must name layers defined in the same file or a referenced tech LEF
- **RECOMMENDED**: Every output `PIN` should include a `DIRECTION OUTPUT` or `DIRECTION INOUT` statement
- **RECOMMENDED**: `ANTENNA*` attributes should appear on output pins for advanced nodes

### Common Errors
- Missing `END <name>` for a MACRO or PIN
- `ORIGIN` or `SIZE` omitted from a MACRO
- Unknown `CLASS` keyword (e.g., `CELL` instead of `CORE`)
- `LAYER` referenced before its definition in the file

---

## DEF (Design Exchange Format)

### Structural Rules
- **REQUIRED**: File must begin with `VERSION` followed by `DESIGN <name>`
- **REQUIRED**: File must end with `END DESIGN`
- **REQUIRED**: Every section (`COMPONENTS`, `NETS`, `SPECIALNETS`, `PINS`, `ROWS`, `TRACKS`) must end with `END <SECTIONNAME>`
- **REQUIRED**: `COMPONENTS N ;` declared count must equal the actual number of component entries
- **REQUIRED**: `NETS N ;` declared count must equal the actual number of net entries
- **REQUIRED**: Each component entry must specify: instance name, cell reference, placement status (`PLACED`, `FIXED`, `COVER`, or `UNPLACED`), and integer coordinates if placed
- **REQUIRED**: Coordinates must be integers (DEF uses database units, not floating point)
- **REQUIRED**: Net connections must reference instance/pin pairs present in `COMPONENTS` or `PINS`
- **RECOMMENDED**: `UNITS DISTANCE MICRONS <N>` should appear after VERSION
- **RECOMMENDED**: `SPECIALNETS` power/ground nets should include explicit route geometries

### Common Errors
- Section count mismatch (declared N but defined M entries)
- Non-integer coordinates (floating-point values in placement)
- Missing `END DESIGN`
- Missing `END <SECTION>` for any open section

---

## SDF (Standard Delay Format)

### Structural Rules
- **REQUIRED**: File must begin with `(DELAYFILE`
- **REQUIRED**: `(DELAYFILE ...)` must contain `(SDFVERSION ...)` and `(TIMESCALE ...)` before any `(CELL ...)` blocks
- **REQUIRED**: `(TIMESCALE ...)` value must be a recognized unit: `1ps`, `10ps`, `100ps`, `1ns`, `10ns`, `100ns`, `1us`
- **REQUIRED**: Every opening `(` must have a matching `)`
- **REQUIRED**: Every `(CELL ...)` block must contain `(CELLTYPE ...)` and at least one delay construct
- **REQUIRED**: Timing values must be in triplet form `(min:typ:max)` or a single bare number; each field must be numeric or empty (bare `:` separator is allowed for unspecified values)
- **REQUIRED**: Timing units must NOT appear inside triplets — values are bare numbers scaled by the `TIMESCALE`; e.g., `(0.1:0.2:0.3)` is correct; `(0.1ns:0.2ns:0.3ns)` is an error
- **REQUIRED**: `(IOPATH <in> <out> <rise> <fall>)` must have exactly 2 delay arguments
- **REQUIRED**: `(SETUP <data> <clock> <delay>)` and `(HOLD ...)` must have exactly 1 delay argument
- **RECOMMENDED**: `(DESIGN ...)` and `(DATE ...)` header fields should be present
- **RECOMMENDED**: All timing values should use consistent triplet notation throughout the file

### Common Errors
- Missing `(TIMESCALE ...)`
- Unbalanced parentheses
- Units inside timing triplet values (e.g., `1.2ns` instead of `1.2`)
- `IOPATH` with 1 or 3+ delay arguments instead of exactly 2
- Negative timing values (flag as warning — may be intentional for hold)

---

## SPEF (Standard Parasitic Exchange Format)

### Structural Rules
- **REQUIRED**: File must begin with the `*SPEF` keyword on the first line
- **REQUIRED**: Header section must include all of: `*DESIGN`, `*DATE`, `*VENDOR`, `*PROGRAM`, `*VERSION`, `*DESIGN_FLOW`, `*DIVIDER`, `*DELIMITER`, `*BUS_DELIMITER`, `*T_UNIT`, `*C_UNIT`, `*R_UNIT`, `*L_UNIT`
- **REQUIRED**: Every `*D_NET <name> <cap>` block must end with `*END`
- **REQUIRED**: Every `*D_NET` block must contain `*CONN`, `*CAP`, and `*RES` subsections in that order
- **REQUIRED**: `*CONN` entries: driver pins use `*D <pin>`, load pins use `*L <pin>`
- **REQUIRED**: `*CAP` entry format: `<index> <node> <value>` — capacitance must be numeric and ≥ 0
- **REQUIRED**: `*RES` entry format: `<index> <node1> <node2> <value>` — resistance must be numeric and > 0
- **REQUIRED**: Node names in `*CAP` and `*RES` must be consistent with names declared in `*CONN`
- **RECOMMENDED**: A `*NAME_MAP` section should be used when net/instance names are long
- **RECOMMENDED**: `*THRESHOLD` should declare the precision level

### Common Errors
- Missing `*END` after a `*D_NET` block
- Missing required header fields
- Non-numeric capacitance or resistance value
- Incorrect field count in `*CAP` or `*RES` entries

---

## Verilog Netlist (.v / .vg)

### Structural Rules
- **REQUIRED**: Every `module <name> (...)` must end with `endmodule`
- **REQUIRED**: All ports listed in the module port list must have explicit `input`, `output`, or `inout` direction declarations in the module body
- **REQUIRED**: All `wire` signals used in cell instance port connections must be declared (either as a port or with an explicit `wire` statement)
- **REQUIRED**: Port connections must use named style (`.port(signal)`) consistently — do not mix named and positional connections within the same instance
- **REQUIRED**: Each cell instance must follow the format: `<CELL_TYPE> <INSTANCE_NAME> (<port_list>);`
- **REQUIRED**: No `defparam` statements — flat gate-level netlists must not use hierarchical parameter overrides
- **RECOMMENDED**: All `input` ports should be driven (connected to at least one instance output)
- **RECOMMENDED**: All `output` ports should be read (connected to at least one instance input)
- **RECOMMENDED**: All `wire` signals should be declared explicitly — do not rely on implicit net creation
- **RECOMMENDED**: Backslash-escaped identifiers (e.g., `\bus[0] `) must include a trailing space before the next token

### Common Errors
- Missing `endmodule`
- Undeclared wire used as a cell pin signal
- Port in module declaration not given a direction
- Mixed named and positional port connections in the same instance
- Backslash-escaped identifier missing the required trailing space
