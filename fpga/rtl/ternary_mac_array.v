// =====================================================================
// ternary_mac_array.v  —  SPIKA-style ternary MAC array (multiplier-free)
//
// Elephant #3 (FPGA): turn the digital-speed ESTIMATE into MEASURED
// hardware bounds. This RTL is synthesized on xc7z010 (EBAZ4205) at
// increasing P to read off:
//   (1) max parallelism P that fits the fabric  -> LUT/FF budget
//   (2) Fmax of the pipelined datapath          -> timing closure
//
// Datapath, per lane (NO multiplier — that is the whole point of ternary):
//   ternary weight w in {-1, 0, +1}, encoded as 2 bits {nz, sign}:
//       2'b00 -> 0   (skip)
//       2'b10 -> +1  (pass  +a)
//       2'b11 -> -1  (pass  -a)
//   partial product pp = nz ? (sign ? -a : +a) : 0
//   => one conditional 2's-complement negate + a mask. Pure LUT logic.
//
// P partial products are summed by a BALANCED, FULLY-PIPELINED adder
// tree (one registered stage per level, depth = ceil(log2 P)). Throughput
// = 1 P-wide vector / clock once the pipe is full; latency = log2(P)+1.
//
// Bit growth: a sum of P terms each <= 2^AW grows by ceil(log2 P) bits,
// so the running sum width is AW+1 (signed pp) + LOG2P. We size every
// tree node to that exact width (SUMW) — not a fat fixed 32b — so the
// LUT/FF measurement reflects the real ternary datapath, not slack.
//
// Synthesizable for xc7z010clg400-1. Power-of-two P only.
// =====================================================================
`timescale 1ns/1ps
`default_nettype none

// ---------------------------------------------------------------------
// One ternary lane: conditional negate / skip. No multiplier.
// ---------------------------------------------------------------------
module ternary_lane #(
    parameter AW = 8                 // signed activation width
)(
    input  wire signed [AW-1:0] a,   // activation
    input  wire        [1:0]    w,   // ternary weight {nz, sign}
    output wire signed [AW:0]   pp   // partial product (one extra bit for -a)
);
    wire nz   = w[1];
    wire sign = w[0];
    wire signed [AW:0] a_ext = {a[AW-1], a};   // sign-extend AW -> AW+1
    wire signed [AW:0] a_neg = -a_ext;         // 2's-comp negate
    assign pp = nz ? (sign ? a_neg : a_ext) : {(AW+1){1'b0}};
endmodule

// ---------------------------------------------------------------------
// Pipelined balanced adder tree over P lanes.
//   - P must be a power of two.
//   - LOG2P registered reduction stages (1 add per node per stage).
//   - Node width grows by 1 bit per level, capped at SUMW (the exact
//     worst-case width AW+1+LOG2P), so we don't pay for unused bits.
//   - Implemented with a single flat register vector per level via a
//     generate loop, so the synthesizer maps it to real fabric adders/FFs
//     rather than a giant 2D reg array (which inflates FF count).
// ---------------------------------------------------------------------
module ternary_mac #(
    parameter P     = 64,                 // lanes (power of two)
    parameter AW    = 8,                  // activation width
    parameter LOG2P = 6,                  // = log2(P)
    parameter SUMW  = AW + 1 + 6          // worst-case sum width (= AW+1+LOG2P)
)(
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    in_valid,
    input  wire signed [P*AW-1:0]  a_vec,   // packed activations
    input  wire        [P*2-1:0]   w_vec,   // packed ternary weights
    output wire                    out_valid,
    output wire signed [SUMW-1:0]  dot      // sum of this P-wide vector
);
    // ---- partial products (combinational, multiplier-free) ----
    wire signed [AW:0] pp [0:P-1];
    genvar i;
    generate
        for (i = 0; i < P; i = i + 1) begin : LANES
            ternary_lane #(.AW(AW)) u_lane (
                .a (a_vec[i*AW +: AW]),
                .w (w_vec[i*2  +: 2]),
                .pp(pp[i])
            );
        end
    endgenerate

    // ---- pipelined balanced adder tree ----
    // level[0] : P nodes (registered partial products)
    // level[k] : P>>k nodes
    // We flatten each level into one wide reg vector of width (P>>k)*SUMW.
    // Generated stage-by-stage so unused levels collapse to nothing.

    // valid pipeline: pp register (1) + LOG2P reductions
    reg [LOG2P:0] valid_sr;
    always @(posedge clk) begin
        if (rst) valid_sr <= 0;
        else     valid_sr <= {valid_sr[LOG2P-1:0], in_valid};
    end
    assign out_valid = valid_sr[LOG2P];

    // Level 0: register the P partial products, sign-extended to SUMW.
    reg signed [P*SUMW-1:0] lvl0;
    integer j0;
    always @(posedge clk) begin
        for (j0 = 0; j0 < P; j0 = j0 + 1)
            lvl0[j0*SUMW +: SUMW] <= {{(SUMW-(AW+1)){pp[j0][AW]}}, pp[j0]};
    end

    // Chained reduction levels. Each declared as its own reg vector and
    // reduced from the previous one. We expose them via a generate so the
    // tool sees independent pipeline registers.
    //
    // To keep this fully parameterized for arbitrary LOG2P we build a
    // worst-case (LOG2P up to 12 => P up to 4096) chain with conditional
    // generate. Levels beyond LOG2P are simply not generated.

    // We carry the running reduced vector through "wires" between stages,
    // realized as registers inside the genvar block.
    wire signed [SUMW-1:0] node_final;

    // Generic recursive-style reduction via a flat array of level vectors.
    // Verilog-2001: emulate with a big reg and a generate ladder.
    genvar lv, nd;
    // storage for up to 13 levels (index 0..12); width of level lv = (P>>lv)*SUMW
    // We can't size a packed array by a per-index expression in a 2D reg,
    // so declare the max-width vector per level and only use the low part.
    generate
        // level registers 1..LOG2P
        for (lv = 1; lv <= LOG2P; lv = lv + 1) begin : LEVELS
            localparam integer NODES = (P >> lv);
            reg signed [NODES*SUMW-1:0] lvl;
            integer k;
            always @(posedge clk) begin
                for (k = 0; k < NODES; k = k + 1) begin
                    if (lv == 1)
                        // reduce from lvl0
                        lvl[k*SUMW +: SUMW] <=
                            $signed(lvl0[(2*k)  *SUMW +: SUMW]) +
                            $signed(lvl0[(2*k+1)*SUMW +: SUMW]);
                    else
                        // reduce from previous level
                        lvl[k*SUMW +: SUMW] <=
                            $signed(LEVELS[lv-1].lvl[(2*k)  *SUMW +: SUMW]) +
                            $signed(LEVELS[lv-1].lvl[(2*k+1)*SUMW +: SUMW]);
                end
            end
        end
    endgenerate

    assign node_final = LEVELS[LOG2P].lvl[0 +: SUMW];
    assign dot        = node_final;

endmodule

`default_nettype wire
