#!/bin/bash
# Phase 47.7.10 W6 — Black-Magic Empirical Sweep
# Tests NeuroSim-simulatable subset of R3 mitigations: pipeline + speedUp + SRAM buffer
# Output: blackmagic_sweep_results.csv

set -e

BUILD_DIR="/path/to/neurosim"
NEUROSIM_DIR="$BUILD_DIR/Inference_pytorch/NeuroSIM"
NETWORKS_DIR="$BUILD_DIR/networks"

RESULTS="$BUILD_DIR/blackmagic_sweep_results.csv"

echo "config,pathway,pipeline,speedUpDegree,globalBufferType,bufferCoreSize,chipArea_mm2,arrayArea_mm2,memUtil_pct,macroDensity_Mb_per_mm2,note" > $RESULTS

cd $NEUROSIM_DIR
[ -f Param.cpp.orig ] || cp Param.cpp Param.cpp.orig

run_config() {
  local pathway=$1
  local config_name=$2
  local pipeline=$3
  local speedUpDegree=$4
  local globalBufferType=$5  # "true" SRAM / "false" register file
  local bufferCoreSize=$6
  local note=$7

  cp Param.cpp.orig Param.cpp
  # Set Mid SKU CIM config baseline: 22nm 4-bit 256sub 16mux 32lvl par
  sed -i '' "s|^	technode = .*|	technode = 22;|" Param.cpp
  sed -i '' "s|^	wireWidth = .*|	wireWidth = 40;|" Param.cpp
  sed -i '' "s|^	featuresize = .*|	featuresize = 40e-9;|" Param.cpp
  sed -i '' "s|^	cellBit = .*|	cellBit = 4;|" Param.cpp
  sed -i '' "s|^	numRowSubArray = .*|	numRowSubArray = 256;|" Param.cpp
  sed -i '' "s|^	numColSubArray = .*|	numColSubArray = 256;|" Param.cpp
  sed -i '' "s|^	numColMuxed = .*|	numColMuxed = 16;|" Param.cpp
  sed -i '' "s|^	levelOutput = .*|	levelOutput = 32;|" Param.cpp
  sed -i '' "s|^	operationmode = .*|	operationmode = 2;|" Param.cpp

  # Black-magic specific params
  sed -i '' "s|^	pipeline = .*|	pipeline = $pipeline;|" Param.cpp
  sed -i '' "s|^	speedUpDegree = .*|	speedUpDegree = $speedUpDegree;|" Param.cpp
  sed -i '' "s|^	globalBufferType = .*|	globalBufferType = $globalBufferType;|" Param.cpp
  sed -i '' "s|^	tileBufferType = .*|	tileBufferType = $globalBufferType;|" Param.cpp
  sed -i '' "s|^	globalBufferCoreSizeRow = .*|	globalBufferCoreSizeRow = $bufferCoreSize;|" Param.cpp
  sed -i '' "s|^	globalBufferCoreSizeCol = .*|	globalBufferCoreSizeCol = $bufferCoreSize;|" Param.cpp

  rm -f Param.o main
  make > /tmp/neurosim_v13_blackmagic_${config_name}.log 2>&1

  OUTPUT=$(./main "$NETWORKS_DIR/NetWork_Qwen35_9B_block.csv" 8 8 2>&1)

  CHIPAREA=$(echo "$OUTPUT" | grep "ChipArea : " | tail -1 | awk '{print $3}')
  ARRAYAREA=$(echo "$OUTPUT" | grep "Total Synaptic Array Area on chip:" | tail -1 | awk '{print $7}')
  MEMUTIL=$(echo "$OUTPUT" | grep "Memory Utilization of Whole Chip:" | awk '{print $6}')

  # Qwen3.5-9B block = 177.2M params × 8 bits = 1417.6 Mb
  MACRO_DENSITY=$(echo "scale=4; 1417.6 / $CHIPAREA" | bc -l 2>/dev/null || echo "0")

  echo "$config_name,$pathway,$pipeline,$speedUpDegree,$globalBufferType,$bufferCoreSize,$CHIPAREA,$ARRAYAREA,$MEMUTIL,$MACRO_DENSITY,$note" >> $RESULTS
  echo "[$pathway $config_name] pipeline=$pipeline speedUp=$speedUpDegree buf=$bufferCoreSize($globalBufferType) Chip=${CHIPAREA}mm² Util=${MEMUTIL}% Density=${MACRO_DENSITY}Mb/mm²"
}

echo "===== Pathway 2.5: Async Pipeline Overlap ====="
run_config "2.5_pipeline" "BM1_baseline_no_pipeline_speedup1"   false 1 false 128 "Baseline: no pipeline, speedUp=1"
run_config "2.5_pipeline" "BM2_speedup_only_no_pipeline"        false 8 false 128 "speedUp=8 only"
run_config "2.5_pipeline" "BM3_pipeline_only_speedup1"          true 1 false 128 "pipeline=true only"
run_config "2.5_pipeline" "BM4_pipeline_speedup8"               true 8 false 128 "BOTH pipeline + speedUp=8"

echo "===== Pathway 2.3: Hierarchical Cache (SRAM Tier 0) ====="
run_config "2.3_sram_cache" "BM5_register_file_buf128"        false 1 false 128  "Register file baseline"
run_config "2.3_sram_cache" "BM6_SRAM_buf128"                 false 1 true  128  "SRAM 128x128 buf"
run_config "2.3_sram_cache" "BM7_SRAM_buf256"                 false 1 true  256  "SRAM 256x256 buf"
run_config "2.3_sram_cache" "BM8_SRAM_buf512"                 false 1 true  512  "SRAM 512x512 buf (Tier 0 cache proxy)"

cp Param.cpp.orig Param.cpp
echo ""
echo "==== Black-magic sweep results ($RESULTS) ===="
cat $RESULTS
