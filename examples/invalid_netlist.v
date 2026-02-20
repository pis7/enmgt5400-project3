// Gate-level netlist for sample_design — INTENTIONALLY INVALID
// Errors introduced for validate-asic-file skill testing:
//   Port io_clk in module declaration has no direction (input/output/inout)
//   Wire n_undeclared is used in U3 but never declared
//   Instance U6 mixes named and positional port connections
//   endmodule is missing — module block is never closed

module sample_design (clk, rst_n, data_in, data_out, io_clk);
  input  clk;
  input  rst_n;
  input  [7:0] data_in;
  output [7:0] data_out;
  // ERROR: io_clk is listed in the port list but has no direction declaration

  wire n1;
  wire n2;
  wire addr_valid;
  wire pipeline_en;
  wire n4;
  wire n5;
  wire n6;
  // ERROR: n_undeclared is used below but never declared here

  NAND2X1 U1 (.A(data_in[0]), .B(data_in[1]), .Y(n1));
  NAND2X1 U2 (.A(data_in[2]), .B(data_in[3]), .Y(n2));

  // ERROR: n_undeclared is not declared as a wire or port
  NOR2X1  U3 (.A(n1), .B(n2), .Y(n_undeclared));

  AND2X1  U4 (.A(n_undeclared), .B(rst_n), .Y(pipeline_en));

  // ERROR: U6 mixes named connections (.A, .B) with a positional connection (n4)
  // Named and positional styles must not be mixed in the same instance
  NAND2X1 U6 (.A(data_in[1]), .B(pipeline_en), n4);

  AOI21X1 U7 (.A0(data_in[2]), .A1(data_in[3]), .B0(n1), .Y(n5));
  OAI21X1 U8 (.A0(n4), .A1(n5), .B0(rst_n), .Y(n6));

  DFFX1 out_reg_0 (.D(n6), .CK(clk), .Q(data_out[0]));
  DFFX1 out_reg_1 (.D(n6), .CK(clk), .Q(data_out[1]));

  // ERROR: endmodule is missing — the module block is never terminated
