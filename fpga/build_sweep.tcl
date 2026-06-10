# =====================================================================
# build_sweep.tcl — synthesize the ternary MAC array for xc7z010 (EBAZ4205)
# across P in {64, 256, 1024, 4096} and report LUT/FF usage + Fmax.
#
# Run inside the aux-mac Vivado VM:
#   source /tools/Xilinx/Vivado/2023.2/settings64.sh
#   vivado -mode batch -nolog -nojournal -source build_sweep.tcl -tclargs <P> <LOG2P>
#
# Two-part methodology per P:
#   (A) OOC synth of `ternary_mac` (no PS7, no pins) -> pure datapath
#       LUT/FF budget. This is the "does it FIT the fabric" number.
#   (B) Synth `ternary_mac_top` with a tight clock, then run timing to
#       find Fmax (max clock that closes). We binary-narrow the target
#       period; report the achieved Fmax = 1000/(target - WNS) heuristic
#       AND the WNS at a fixed 100 MHz probe so the read-off is honest.
#
# Outputs (in CWD):
#   util_P<P>.rpt      report_utilization for ternary_mac (OOC)
#   timing_P<P>.rpt    report_timing_summary for ternary_mac_top @ probe clk
#   sweep_P<P>.log     condensed machine-readable line
# =====================================================================

set PART  xc7z010clg400-1
set P     [lindex $argv 0]
set LOG2P [lindex $argv 1]
set AW    8
set SUMW  [expr {$AW + 1 + $LOG2P}]
set SRC   [file dirname [file normalize [info script]]]/rtl
set OUT   [pwd]

puts "############################################################"
puts "## ternary MAC array  P=$P  LOG2P=$LOG2P  AW=$AW  SUMW=$SUMW"
puts "## part=$PART"
puts "############################################################"

# ---------------------------------------------------------------------
# (A) OOC synthesis of the bare array -> resource budget
# ---------------------------------------------------------------------
read_verilog -sv $SRC/ternary_mac_array.v
synth_design -top ternary_mac -part $PART -mode out_of_context \
    -generic P=$P -generic AW=$AW -generic LOG2P=$LOG2P -generic SUMW=$SUMW \
    -flatten_hierarchy rebuilt
report_utilization -file $OUT/util_P${P}.rpt
# grab the headline slice numbers
set luts [get_property SLICE_LUTS  [get_cells -hier -quiet]]
puts "## OOC array synth complete for P=$P"
write_checkpoint -force $OUT/array_P${P}.dcp

# ---------------------------------------------------------------------
# (B) Top wrapper with a real clock for Fmax probing.
#     We synth + place + route at a PROBE period and read WNS.
#     Probe period chosen per P so small P gets an aggressive target
#     (find true Fmax) and large P gets a relaxed one (still close).
# ---------------------------------------------------------------------
# pick probe period (ns): aim for a target that the design can plausibly meet,
# so WNS is a small +/- number we can convert to Fmax accurately.
if {$P <= 64}        { set PROBE 4.0 } \
elseif {$P <= 256}   { set PROBE 5.0 } \
elseif {$P <= 1024}  { set PROBE 6.0 } \
else                 { set PROBE 8.0 }

close_project -quiet
read_verilog -sv $SRC/ternary_mac_array.v
read_verilog -sv $SRC/ternary_mac_top.v
synth_design -top ternary_mac_top -part $PART \
    -generic P=$P -generic AW=$AW -generic LOG2P=$LOG2P -generic SUMW=$SUMW \
    -flatten_hierarchy rebuilt
create_clock -name clk -period $PROBE [get_ports clk]
opt_design
place_design
route_design
report_utilization      -file $OUT/util_top_P${P}.rpt
report_timing_summary   -file $OUT/timing_P${P}.rpt

# read WNS off the routed design
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set achieved_period [expr {$PROBE - $wns}]
set fmax_mhz [expr {1000.0 / $achieved_period}]

puts "############################################################"
puts "## RESULT P=$P : probe=${PROBE}ns  WNS=${wns}ns  Fmax=${fmax_mhz} MHz"
puts "############################################################"

# machine-readable summary line
set fh [open $OUT/sweep_P${P}.log w]
puts $fh "P=$P LOG2P=$LOG2P AW=$AW SUMW=$SUMW probe_ns=$PROBE wns_ns=$wns achieved_ns=$achieved_period fmax_mhz=$fmax_mhz"
close $fh
puts "DONE P=$P -> sweep_P${P}.log"
