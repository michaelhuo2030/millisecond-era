// =====================================================================
// ternary_mac_throughput_tb.v — UTILIZATION / THROUGHPUT testbench.
//
// Closes ADR blocker #2 (the "P x utilization" absolute-speed anchor) at
// the SIMULATION level, locally, no FPGA board / no Vivado VM. Fmax + P
// already came from real Vivado synthesis (ADR 1.4); UTILIZATION is a
// cycle-count / dataflow property that a functional cycle-accurate sim
// captures exactly. iverilog + vvp runnable on the main mac.
//
// What it does (batch=1, the hardest case for a streaming MAC):
//   - Treats one ternary `ternary_mac` (P lanes) as the array's reduction
//     engine. A layer matmul Y[M,N] = X[M,K] . W[K,N] is decomposed into
//     P-wide dot-product chunks: each chunk is one P-lane vector presented
//     to the MAC. #chunks = M * N * ceil(K/P).
//   - Streams chunks back-to-back asserting in_valid CONTINUOUSLY (no gaps),
//     with REALISTIC sparse ternary weights (~2/3 zeros => skip) + int8
//     activations.
//   - MEASURES:
//       * Initiation interval II  = cycles between successive accepted
//         inputs AND between successive out_valid pulses (II=1 => fully
//         pipelined, 100% lane-fill; II>1 => stalls).
//       * total_cycles  to drain the whole layer's worth of chunks.
//       * ideal_cycles  = #chunks  (one P-wide vector / cycle at II=1).
//       * effective util = ideal_cycles / total_cycles (incl. pipeline
//         fill+drain overhead, which is the only honest loss at batch=1).
//       * MACs/cycle achieved = (P * #chunks) / total_cycles.
//
// Honest scope: this is the ARRAY DATAPATH utilization. A real system adds
// memory/feeding bandwidth + SFU/attention/norm bubbles this does NOT model.
// The point of blocker #2 is exactly the datapath half: does the pipeline
// actually sustain II=1 under a continuous realistic stream, or does it
// stall? (It cannot stall — there is no backpressure path in the RTL — but
// we MEASURE it rather than assert it, and quantify fill/drain overhead.)
// =====================================================================
`timescale 1ns/1ps

module ternary_mac_throughput_tb;
    // ---- match the synthesized P=512 max-fit config (LOG2P=9) ----
    // (also runnable at P=64 by overriding; we report whatever is built)
    localparam P     = 512;
    localparam AW    = 8;
    localparam LOG2P = 9;
    localparam SUMW  = AW + 1 + LOG2P;   // 18

    // pipeline latency: pp reg (1) + LOG2P reductions, exposed via valid_sr.
    // out_valid = valid_sr[LOG2P]; valid_sr has LOG2P+1 stages fed by in_valid.
    // First out_valid appears LOG2P+1 cycles after first in_valid.
    localparam LAT = LOG2P + 1;

    // ---- realistic layer geometry (a transformer-ish dense layer) ----
    // We pick a layer whose K spans several P-chunks so the streaming is
    // non-trivial, and M*N gives thousands of dot products = thousands of
    // back-to-back chunks => II is measured over a long steady-state run.
    //   K = 2048  (hidden dim)   => K_CHUNKS = ceil(2048/512) = 4
    //   M = 8     (a few tokens of context in this micro-layer)
    //   N = 64    (output features sampled)
    // total chunks = M * N * K_CHUNKS = 8 * 64 * 4 = 2048 P-wide vectors.
    localparam K        = 2048;
    localparam K_CHUNKS = (K + P - 1) / P;   // 4
    localparam M        = 8;
    localparam N        = 64;
    localparam N_CHUNKS = M * N * K_CHUNKS;   // 2048 streamed vectors

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

    always #5 clk = ~clk;   // 100 MHz sim clock (clock period irrelevant to II)

    // ---- measurement state ----
    integer fed            = 0;   // # in_valid cycles asserted (accepted inputs)
    integer got            = 0;   // # out_valid pulses observed
    integer first_in_cy    = -1;  // cycle of first in_valid
    integer last_in_cy     = -1;  // cycle of last  in_valid
    integer first_out_cy   = -1;  // cycle of first out_valid
    integer last_out_cy    = -1;  // cycle of last  out_valid
    integer prev_out_cy    = -1;  // for inter-out-valid gap (II_out) check
    integer max_out_gap    = 0;   // worst gap between consecutive out_valid
    integer out_gap_viol   = 0;   // # of gaps > 1 (stall events on output side)
    integer cycle          = 0;   // free-running cycle counter (post-reset)

    integer s;

    // count cycles after reset deasserts
    always @(posedge clk) if (!rst) cycle <= cycle + 1;

    // ---- output-side observation: runs every cycle, independent of feeder ----
    always @(posedge clk) begin
        if (!rst && out_valid) begin
            got = got + 1;
            if (first_out_cy < 0) first_out_cy = cycle;
            last_out_cy = cycle;
            if (prev_out_cy >= 0) begin
                if ((cycle - prev_out_cy) > max_out_gap)
                    max_out_gap = (cycle - prev_out_cy);
                if ((cycle - prev_out_cy) > 1)
                    out_gap_viol = out_gap_viol + 1;
            end
            prev_out_cy = cycle;
        end
    end

    // ---- feeder: stream N_CHUNKS P-wide vectors back-to-back, no gaps ----
    integer chunk;
    initial begin
        a_vec = 0; w_vec = 0; in_valid = 0;
        repeat (4) @(posedge clk);
        rst = 0;
        @(negedge clk);   // align stimulus to negedge so it's stable at posedge

        for (chunk = 0; chunk < N_CHUNKS; chunk = chunk + 1) begin
            // realistic stimulus: int8 activations, SPARSE ternary weights.
            // ~2/3 zeros (skip), ~1/6 +1, ~1/6 -1 — typical post-train ternary
            // weight sparsity. The MAC processes ALL P lanes every cycle
            // regardless of zeros (skip is a lane-internal mask, not a cycle
            // saving) — so sparsity does NOT change II; we feed it anyway to be
            // a realistic workload, not to game the number.
            for (s = 0; s < P; s = s + 1) begin
                a_vec[s*AW +: AW] = $random;            // int8 activation
                case ($random % 6)
                    0:       w_vec[s*2 +: 2] = 2'b10;   // +1  (1/6)
                    1:       w_vec[s*2 +: 2] = 2'b11;   // -1  (1/6)
                    default: w_vec[s*2 +: 2] = 2'b00;   //  0  (4/6 = sparse)
                endcase
            end
            in_valid = 1;
            // record feed cycles. 'cycle' increments on posedge; we set
            // in_valid on negedge so at the upcoming posedge it is sampled
            // and 'cycle' will be the cycle index of THIS accepted input.
            @(posedge clk);
            fed = fed + 1;
            if (first_in_cy < 0) first_in_cy = cycle;
            last_in_cy = cycle;
            @(negedge clk);
        end
        in_valid = 0;   // stop feeding; let the pipe drain

        // wait long enough for the last input to propagate out + margin
        repeat (LAT + 8) @(posedge clk);

        // ============ REPORT ============
        $display("=====================================================");
        $display("THROUGHPUT / UTILIZATION  (batch=1, continuous stream)");
        $display("  config: P=%0d AW=%0d LOG2P=%0d SUMW=%0d  pipeline LAT=%0d",
                 P, AW, LOG2P, SUMW, LAT);
        $display("  layer : K=%0d (K_CHUNKS=%0d)  M=%0d  N=%0d",
                 K, K_CHUNKS, M, N);
        $display("  -> total P-wide chunks streamed = %0d", N_CHUNKS);
        $display("-----------------------------------------------------");
        $display("  inputs fed (in_valid cycles)    = %0d", fed);
        $display("  outputs got (out_valid pulses)  = %0d", got);
        $display("  first_in cycle  = %0d   last_in cycle  = %0d", first_in_cy, last_in_cy);
        $display("  first_out cycle = %0d   last_out cycle = %0d", first_out_cy, last_out_cy);
        $display("-----------------------------------------------------");

        // ----- INPUT-side II: cycles between successive accepted inputs -----
        // span_in = last_in - first_in; over (fed-1) intervals.
        // II_in = span / (fed-1).  Continuous feed => span = fed-1 => II=1.0
        if (fed > 1) begin
            $display("  INPUT  II = %0d / %0d = %0d.%03d cyc/input",
                     (last_in_cy - first_in_cy), (fed - 1),
                     (last_in_cy - first_in_cy) / (fed - 1),
                     (((last_in_cy - first_in_cy) * 1000) / (fed - 1)) % 1000);
        end

        // ----- OUTPUT-side II: cycles between successive out_valid pulses ----
        if (got > 1) begin
            $display("  OUTPUT II = %0d / %0d = %0d.%03d cyc/output (max gap=%0d, stalls>1=%0d)",
                     (last_out_cy - first_out_cy), (got - 1),
                     (last_out_cy - first_out_cy) / (got - 1),
                     (((last_out_cy - first_out_cy) * 1000) / (got - 1)) % 1000,
                     max_out_gap, out_gap_viol);
        end

        $display("-----------------------------------------------------");
        // ----- TOTAL CYCLES vs IDEAL -----
        // ideal = N_CHUNKS cycles (one P-wide vector / cycle at II=1, the
        //         minimum to PUSH all the work in). total = first_in .. last_out
        //         inclusive = work + pipeline fill + drain (LAT cycles).
        // We report BOTH the steady-state util (ignoring fill/drain) and the
        // end-to-end util (charging fill/drain), since at batch=1 the only
        // honest loss is the one-time pipe fill+drain.
        begin : RPT
            integer total_cycles;     // first accepted input .. last out_valid
            integer ideal_cycles;     // N_CHUNKS
            integer util_e3;          // end-to-end util * 1000
            integer macs_per_cyc_e3;  // (P*N_CHUNKS)/total * 1000  -- vs peak P
            total_cycles = (last_out_cy - first_in_cy) + 1;
            ideal_cycles = N_CHUNKS;
            util_e3      = (ideal_cycles * 1000) / total_cycles;
            macs_per_cyc_e3 = (P * ideal_cycles * 1000) / total_cycles;
            $display("  ideal_cycles (#chunks)          = %0d", ideal_cycles);
            $display("  total_cycles (in..last_out)     = %0d", total_cycles);
            $display("  pipeline fill+drain overhead    = %0d cycles (= LAT)", total_cycles - ideal_cycles);
            $display("  EFFECTIVE UTIL (end-to-end)     = %0d.%01d%%  (ideal/total)",
                     util_e3 / 10, util_e3 % 10);
            $display("  STEADY-STATE UTIL (II=1 region) = %0d.%01d%%  (1/II_out)",
                     ((got - 1) * 1000) / (last_out_cy - first_out_cy) / 10,
                     (((got - 1) * 1000) / (last_out_cy - first_out_cy)) % 10);
            $display("  MACs/cycle achieved             = %0d.%03d  (peak = P = %0d)",
                     macs_per_cyc_e3 / 1000, macs_per_cyc_e3 % 1000, P);
        end

        $display("-----------------------------------------------------");
        // ----- PASS/FAIL -----
        if (got != fed)
            $display("RESULT: FAIL — output count (%0d) != input count (%0d)", got, fed);
        else if (out_gap_viol != 0)
            $display("RESULT: FAIL — %0d output stalls (gap>1) — pipeline NOT II=1", out_gap_viol);
        else if (fed != N_CHUNKS)
            $display("RESULT: FAIL — fed %0d != N_CHUNKS %0d", fed, N_CHUNKS);
        else
            $display("RESULT: PASS — II=1 sustained, no stalls, all %0d chunks retired", N_CHUNKS);
        $display("=====================================================");
        $finish;
    end
endmodule
