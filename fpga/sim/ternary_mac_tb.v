// =====================================================================
// ternary_mac_tb.v — cycle-accurate correctness check for ternary_mac.
// Drives random P-wide vectors, compares the pipelined dot output against
// a behavioral reference dot product. iverilog-runnable on the main mac.
// =====================================================================
`timescale 1ns/1ps

module ternary_mac_tb;
    localparam P     = 64;
    localparam AW    = 8;
    localparam LOG2P = 6;
    localparam SUMW  = AW + 1 + LOG2P;   // 15

    reg clk = 0, rst = 1, in_valid = 0;
    reg  signed [P*AW-1:0] a_vec;
    reg         [P*2-1:0]  w_vec;
    wire                   out_valid;
    wire signed [SUMW-1:0] dot;

    ternary_mac #(.P(P), .AW(AW), .LOG2P(LOG2P), .SUMW(SUMW)) dut (
        .clk(clk), .rst(rst), .in_valid(in_valid),
        .a_vec(a_vec), .w_vec(w_vec),
        .out_valid(out_valid), .dot(dot)
    );

    always #5 clk = ~clk;   // 100 MHz sim clock

    // reference dot product for a given (a_vec, w_vec)
    function signed [SUMW-1:0] ref_dot;
        input signed [P*AW-1:0] av;
        input        [P*2-1:0]  wv;
        integer k;
        reg signed [SUMW-1:0] acc;
        reg signed [AW-1:0]   a;
        reg        [1:0]      w;
        begin
            acc = 0;
            for (k = 0; k < P; k = k + 1) begin
                a = av[k*AW +: AW];
                w = wv[k*2 +: 2];
                if (w[1]) acc = w[0] ? (acc - a) : (acc + a); // -1 : +1
                // w[1]==0 -> skip
            end
            ref_dot = acc;
        end
    endfunction

    // store expected results in a small pipeline to match DUT latency
    localparam LAT = LOG2P + 2;   // valid_sr depth + pp reg + out reg
    reg signed [SUMW-1:0] exp_pipe [0:LAT-1];
    integer p;

    integer trial, errors = 0, checks = 0;
    integer s;

    initial begin
        // seed
        a_vec = 0; w_vec = 0;
        for (p = 0; p < LAT; p = p + 1) exp_pipe[p] = 0;
        repeat (4) @(posedge clk);
        rst = 0;

        for (trial = 0; trial < 2000; trial = trial + 1) begin
            @(negedge clk);
            // random inputs
            for (s = 0; s < P; s = s + 1) begin
                a_vec[s*AW +: AW] = $random;
                // weight: ~1/3 each of 0,+1,-1
                case ($random % 3)
                    0: w_vec[s*2 +: 2] = 2'b00; // 0
                    1: w_vec[s*2 +: 2] = 2'b10; // +1
                    default: w_vec[s*2 +: 2] = 2'b11; // -1
                endcase
            end
            in_valid = 1;
            // shift expected pipeline; new expected enters at head
            for (p = LAT-1; p > 0; p = p - 1) exp_pipe[p] = exp_pipe[p-1];
            exp_pipe[0] = ref_dot(a_vec, w_vec);

            @(posedge clk);
            // check output against the matured expected
            if (out_valid && trial > LAT) begin
                checks = checks + 1;
                if (dot !== exp_pipe[LAT-1]) begin
                    errors = errors + 1;
                    if (errors <= 10)
                        $display("MISMATCH trial=%0d dot=%0d exp=%0d",
                                 trial, dot, exp_pipe[LAT-1]);
                end
            end
        end

        $display("=====================================================");
        $display("ternary_mac TB: P=%0d AW=%0d  checks=%0d  errors=%0d",
                 P, AW, checks, errors);
        if (errors == 0) $display("RESULT: PASS (pipelined dot == reference)");
        else             $display("RESULT: FAIL");
        $display("=====================================================");
        $finish;
    end
endmodule
