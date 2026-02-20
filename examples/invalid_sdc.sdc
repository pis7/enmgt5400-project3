# ============================================================
# SDC constraints for sample_design — INTENTIONALLY INVALID
# Errors introduced for validate-asic-file skill testing:
#   Line 9:  create_clock missing -period (REQUIRED argument)
#   Line 14: set_input_delay references undefined clock "clk_undefined"
#   Line 18: set_multicycle_path -setup 1 (must be >= 2)
#   Line 22: set_max_delay with negative value (must be > 0)
#   Line 27: trailing space after backslash continuation (REQUIRED: no whitespace after \)
# ============================================================

# ERROR: -period is missing — create_clock has no period argument
create_clock -name clk_core -waveform {0 1.0} [get_ports clk]

create_clock -name clk_io -period 5.0 -waveform {0 2.5} [get_ports io_clk]

# ERROR: "clk_undefined" was never created with create_clock
set_input_delay -clock clk_undefined -max 0.8 [get_ports data_in]
set_output_delay -clock clk_io -max 2.0 [get_ports io_data_out]

# ERROR: -setup 1 is the default; must be >= 2 to be a multicycle path
set_multicycle_path -setup 1 \
    -from [get_clocks {clk_core}] \
    -to [get_clocks {clk_io}]

# ERROR: negative delay value — set_max_delay requires a value > 0
set_max_delay -0.5 -from [get_clocks {clk_core}] -to [get_clocks {clk_io}]

# WARNING: set_clock_uncertainty missing for clk_io
set_clock_uncertainty 0.05 [get_clocks clk_core]

# ERROR: trailing space after backslash continuation (space shown as · below)
set_clock_groups -asynchronous \
    -group {clk_core} \
    -group {clk_io}
