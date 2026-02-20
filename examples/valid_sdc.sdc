# ============================================================
# SDC constraints for sample_design
# Clock frequency: 500 MHz (2.0 ns period)
# ============================================================

# Primary clock
create_clock -name clk_core -period 2.0 -waveform {0 1.0} [get_ports clk]

# PLL-generated divided clock
create_clock -name clk_slow -period 8.0 -waveform {0 4.0} [get_pins pll_inst/clk_div4]

# External interface clock
create_clock -name clk_io -period 5.0 -waveform {0 2.5} [get_ports io_clk]

# Input delays (relative to clk_core)
set_input_delay -clock clk_core -max 0.8 [get_ports data_in]
set_input_delay -clock clk_core -min 0.1 [get_ports data_in]
set_input_delay -clock clk_core -max 0.6 [get_ports addr_in]
set_input_delay -clock clk_io -max 1.5 [get_ports io_data_in]

# Output delays
set_output_delay -clock clk_core -max 0.5 [get_ports data_out]
set_output_delay -clock clk_io -max 2.0 [get_ports io_data_out]

# False paths between asynchronous clock domains
set_false_path -from [get_clocks {clk_core}] -to [get_clocks {clk_io}]
set_false_path -from [get_clocks {clk_io}] -to [get_clocks {clk_core}]

# Multicycle path for slow divider logic
set_multicycle_path -setup 4 \
    -from [get_clocks {clk_core}] \
    -to [get_clocks {clk_slow}]

# Max delay constraint on async reset path
set_max_delay 1.5 -from [get_clocks {clk_core}] -to [get_clocks {clk_slow}]

# Clock groups
set_clock_groups -asynchronous \
    -group {clk_core clk_slow} \
    -group {clk_io}

# Clock uncertainty
set_clock_uncertainty 0.05 [get_clocks clk_core]
set_clock_uncertainty 0.10 [get_clocks clk_io]
set_clock_uncertainty 0.08 [get_clocks clk_slow]
