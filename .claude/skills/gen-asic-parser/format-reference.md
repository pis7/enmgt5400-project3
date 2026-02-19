# ASIC Format Reference

Load this file when generating a parser to get format-specific data models and parsing strategies.

## Data Models by Format

### SDC
- `ClockConstraint(name, period, waveform, source)` — period must be > 0
- `IODelay(pin, clock, delay_value, delay_type, min_delay, max_delay)`
- `TimingException(exception_type, from_list, to_list, value)`
- `SDCConstraintSet(clocks, io_delays, exceptions, raw_commands)`

### Liberty
- `LookupTable(index_1, index_2, values)` — values is list[list[float]]
- `TimingArc(related_pin, timing_type, timing_sense, cell_rise, cell_fall)` — each is a LookupTable
- `Pin(name, direction, capacitance, timing_arcs)` — direction in {"input","output","inout"}
- `Cell(name, area, pins)` — area in µm²
- `LibertyLibrary(name, cells, time_unit, capacitance_unit)`

### LEF
- `LEFLayer(name, layer_type, pitch, width)` — layer_type in {"ROUTING","CUT","MASTERSLICE"}
- `LEFPin(name, direction, shape, port_geometries)`
- `Obstruction(layer, rectangles)` — rectangles is list[tuple[float,float,float,float]]
- `Macro(name, class_type, size, origin, pins, obstructions)` — size is (width, height)
- `LEFLibrary(version, layers, macros, sites)`

### DEF
- `Component(name, cell_name, placement_status, x, y, orientation)`
- `NetConnection(instance_name, pin_name)`
- `Net(name, connections)` — connections is list[NetConnection]
- `SpecialNet(name, use, routing_points)` — use in {"POWER","GROUND","CLOCK"}
- `DEFDesign(name, units, die_area, rows, tracks, components, nets, special_nets)`

### SDF
- `DelayValue(min_val, typ_val, max_val)` — all floats, may be None for unspecified
- `IOPath(input_port, output_port, rise_delay, fall_delay)` — each delay is DelayValue
- `TimingCheck(check_type, port, related_port, value)` — check_type in {"SETUP","HOLD","RECOVERY","REMOVAL"}
- `SDFCell(cell_type, instance, io_paths, timing_checks)`
- `SDFFile(sdf_version, design, voltage, process, temperature, cells)`

### SPEF
- `ParasiticNode(name, capacitance)` — capacitance in fF
- `ParasiticResistor(node1, node2, resistance)` — resistance in ohms
- `SPEFNet(name, total_cap, driver_cell, connections, caps, resistors)`
- `SPEFFile(design, time_unit, cap_unit, res_unit, inductance_unit, nets)`

### Verilog Netlist
- `PortConnection(port_name, net_name)`
- `CellInstance(instance_name, cell_type, connections)` — connections is list[PortConnection]
- `Wire(name, width)` — width=1 for scalar
- `Module(name, ports, wires, instances)`

## Parsing Strategies by Format

| Format | Approach | Key Gotchas |
|--------|----------|-------------|
| SDC | Line-oriented; `re` per command | Backslash line continuation (`\` + newline); `#` comments; `[get_ports ...]` Tcl syntax |
| Liberty | Hierarchical brace-delimited groups | Track brace depth; quoted lookup table arrays `"0.1, 0.2, 0.3"`; values can be unquoted |
| LEF | Section-oriented; semicolon-terminated | `END <name>` delimiters close blocks; `MACRO`/`PIN`/`OBS` context stack |
| DEF | Section-oriented; semicolon-terminated | `COMPONENTS N ;` ... `END COMPONENTS`; very large NETS sections need streaming |
| SDF | S-expression parenthesized | `(min:typ:max)` triplets; recursive paren nesting; `TIMESCALE` affects unit |
| SPEF | Line-oriented; section headers | `*D_NET name cap ;` starts a net; `/` separator in hierarchical instance names |
| Verilog netlist | Statement-oriented; semicolon-terminated | Backslash-escaped IDs have trailing space: `\bus[0] `; named port map `.port(net)` |
