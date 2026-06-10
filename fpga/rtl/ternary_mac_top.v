// =====================================================================
// ternary_mac_top.v — self-contained synthesis wrapper for ternary_mac.
//
// Why a wrapper: a P-wide parallel ternary_mac has P*AW + P*2 input bits
// (e.g. P=4096, AW=8 -> 40960 inputs) which cannot map to physical pins.
// To MEASURE the datapath (Fmax + LUT/FF), we drive the array from on-chip
// LFSRs and reduce the wide dot-product output to a single registered XOR
// "signature" bit. This:
//   - keeps register-to-register timing through the FULL adder tree on the
//     critical path (so Fmax is the real datapath number),
//   - lets the design close I/O to {clk, rst, sig} (synthesizable standalone),
//   - does NOT let the tool optimize the array away (the signature depends
//     on every tree output, and the LFSRs are real sequential logic).
//
// For the pure resource budget we ALSO synthesize ternary_mac out-of-context
// (see build_array.tcl, OOC flow). This top is primarily for timing/Fmax and
// a sanity end-to-end fit. Resource numbers from this top INCLUDE the small
// LFSR/signature overhead (a few hundred LUTs), which we subtract out in the
// report read-off.
// =====================================================================
`timescale 1ns/1ps
`default_nettype none

module ternary_mac_top #(
    parameter P     = 64,
    parameter AW    = 8,
    parameter LOG2P = 6,
    parameter SUMW  = AW + 1 + 6
)(
    input  wire clk,
    input  wire rst,
    output reg  sig          // registered 1-bit signature of the dot output
);
    // ---- pseudo-random activation + weight generators ----
    // One 32-bit LFSR feeds a sliding window; we tap distinct bits per lane.
    reg [31:0] lfsr_a;
    reg [31:0] lfsr_w;
    wire fb_a = lfsr_a[31] ^ lfsr_a[21] ^ lfsr_a[1] ^ lfsr_a[0];
    wire fb_w = lfsr_w[31] ^ lfsr_w[21] ^ lfsr_w[1] ^ lfsr_w[0];
    always @(posedge clk) begin
        if (rst) begin
            lfsr_a <= 32'hACE1_2345;
            lfsr_w <= 32'h1357_BD9F;
        end else begin
            lfsr_a <= {lfsr_a[30:0], fb_a};
            lfsr_w <= {lfsr_w[30:0], fb_w};
        end
    end

    // Build packed input vectors. Each lane gets a rotated copy of the LFSR
    // so lanes differ; cheap and synthesizable. (Combinational fanout from
    // 2 small registers — negligible area vs the P-lane array.)
    wire signed [P*AW-1:0] a_vec;
    wire        [P*2-1:0]  w_vec;
    genvar i;
    generate
        for (i = 0; i < P; i = i + 1) begin : GEN_IN
            // activation = byte-slice of LFSR rotated by i
            wire [31:0] ra = (lfsr_a << (i % 7)) | (lfsr_a >> (32 - (i % 7)));
            assign a_vec[i*AW +: AW] = ra[AW-1:0];
            // weight {nz,sign} from two LFSR bits rotated by i
            wire [31:0] rw = (lfsr_w << (i % 11)) | (lfsr_w >> (32 - (i % 11)));
            assign w_vec[i*2 +: 2] = rw[1:0];
        end
    endgenerate

    reg in_valid;
    always @(posedge clk) in_valid <= ~rst;

    wire                   out_valid;
    wire signed [SUMW-1:0] dot;

    ternary_mac #(.P(P), .AW(AW), .LOG2P(LOG2P), .SUMW(SUMW)) u_mac (
        .clk(clk), .rst(rst), .in_valid(in_valid),
        .a_vec(a_vec), .w_vec(w_vec),
        .out_valid(out_valid), .dot(dot)
    );

    // collapse the dot output to 1 registered bit so the top has tiny I/O
    always @(posedge clk) begin
        if (rst) sig <= 1'b0;
        else if (out_valid) sig <= ^dot;   // XOR-reduce -> depends on all bits
    end
endmodule

`default_nettype wire
