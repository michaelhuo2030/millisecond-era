#!/bin/bash
# Phase 47.7.10 Mid SKU + Pro SKU NeuroSim Sweep
# Sweeps 4 Mid SKU + 5 Pro SKU configs across LLM-class networks
# Output: mid_sku_sweep_results.csv + pro_sku_sweep_results.csv

set -e

BUILD_DIR="/path/to/neurosim"
NEUROSIM_DIR="$BUILD_DIR/Inference_pytorch/NeuroSIM"
NETWORKS_DIR="$BUILD_DIR/networks"

MID_RESULTS="$BUILD_DIR/mid_sku_sweep_results.csv"
PRO_RESULTS="$BUILD_DIR/pro_sku_sweep_results.csv"

echo "config,model,d_model,d_ff,technode,cellBit,subArray,numColMuxed,levelOutput,operationmode,blocks_full,chipArea_mm2_per_block,arrayArea_mm2_per_block,adcArea_um2,memUtil_pct,arrayFrac_pct,adcFrac_pct,block_params_M,macroDensity_Mb_per_mm2" > $MID_RESULTS
cp $MID_RESULTS $PRO_RESULTS

cd $NEUROSIM_DIR
[ -f Param.cpp.orig ] || cp Param.cpp Param.cpp.orig

# Network metadata (avoid bash 3.2 assoc arrays)
get_blocks() {
  case $1 in
    Qwen35_4B) echo 36;;
    Qwen35_9B) echo 32;;
    Qwen3VL_30B_A3B) echo 28;;
    Qwen35_35B_A3B) echo 32;;
    Qwen35_27B) echo 48;;
  esac
}

get_params_M() {
  case $1 in
    Qwen35_4B) echo 48.2;;
    Qwen35_9B) echo 177.2;;
    Qwen3VL_30B_A3B) echo 45.1;;
    Qwen35_35B_A3B) echo 68.8;;
    Qwen35_27B) echo 275.3;;
  esac
}

get_d_model_d_ff() {
  case $1 in
    Qwen35_4B) echo "2048 6144";;
    Qwen35_9B) echo "4096 11008";;
    Qwen3VL_30B_A3B) echo "2048 5632";;
    Qwen35_35B_A3B) echo "2560 6912";;
    Qwen35_27B) echo "5120 13824";;
  esac
}

run_config() {
  local sku=$1            # mid or pro
  local config_name=$2
  local technode=$3
  local cellBit=$4
  local subArray=$5
  local numColMuxed=$6
  local levelOutput=$7
  local operationmode=$8
  local model=$9

  case $technode in
    32) wireWidth=56;;
    22) wireWidth=40;;
    14) wireWidth=25;;
    *) echo "Unsupported technode $technode"; return;;
  esac

  cp Param.cpp.orig Param.cpp
  sed -i '' "s|^	technode = .*|	technode = $technode;|" Param.cpp
  sed -i '' "s|^	wireWidth = .*|	wireWidth = $wireWidth;|" Param.cpp
  sed -i '' "s|^	featuresize = .*|	featuresize = ${wireWidth}e-9;|" Param.cpp
  sed -i '' "s|^	cellBit = .*|	cellBit = $cellBit;|" Param.cpp
  sed -i '' "s|^	numRowSubArray = .*|	numRowSubArray = $subArray;|" Param.cpp
  sed -i '' "s|^	numColSubArray = .*|	numColSubArray = $subArray;|" Param.cpp
  sed -i '' "s|^	numColMuxed = .*|	numColMuxed = $numColMuxed;|" Param.cpp
  sed -i '' "s|^	levelOutput = .*|	levelOutput = $levelOutput;|" Param.cpp
  sed -i '' "s|^	operationmode = .*|	operationmode = $operationmode;|" Param.cpp

  rm -f Param.o main
  make > /tmp/neurosim_v13_${config_name}_build.log 2>&1

  blocks=$(get_blocks $model)
  block_params_M=$(get_params_M $model)
  d_info=$(get_d_model_d_ff $model)
  d_model=$(echo $d_info | awk '{print $1}')
  d_ff=$(echo $d_info | awk '{print $2}')

  OUTPUT=$(./main "$NETWORKS_DIR/NetWork_${model}_block.csv" 8 8 2>&1)

  CHIPAREA=$(echo "$OUTPUT" | grep "ChipArea : " | tail -1 | awk '{print $3}')
  ARRAYAREA=$(echo "$OUTPUT" | grep "Total Synaptic Array Area on chip:" | tail -1 | awk '{print $7}')
  ADCAREA_UM=$(echo "$OUTPUT" | grep "Total ADC Area on chip:" | awk '{print $6}')
  MEMUTIL=$(echo "$OUTPUT" | grep "Memory Utilization of Whole Chip:" | awk '{print $6}')

  ARRAYFRAC=$(echo "scale=4; $ARRAYAREA / $CHIPAREA * 100" | bc -l 2>/dev/null || echo "0")
  ADCFRAC=$(echo "scale=4; $ADCAREA_UM / ($CHIPAREA * 1000000) * 100" | bc -l 2>/dev/null || echo "0")

  # Macro density at LLM-class: per-block params in Mb / per-block ChipArea mm²
  BLOCK_MB=$(echo "$block_params_M * 8" | bc -l 2>/dev/null || echo "0")
  MACRO_DENSITY=$(echo "scale=4; $BLOCK_MB / $CHIPAREA" | bc -l 2>/dev/null || echo "0")

  if [ "$sku" = "mid" ]; then
    OUT=$MID_RESULTS
  else
    OUT=$PRO_RESULTS
  fi

  echo "$config_name,$model,$d_model,$d_ff,$technode,$cellBit,$subArray,$numColMuxed,$levelOutput,$operationmode,$blocks,$CHIPAREA,$ARRAYAREA,$ADCAREA_UM,$MEMUTIL,$ARRAYFRAC,$ADCFRAC,$block_params_M,$MACRO_DENSITY" >> $OUT
  echo "[$sku $config_name $model] Chip/Block=${CHIPAREA}mm² Array%=${ARRAYFRAC}% ADC%=${ADCFRAC}% MemUtil=${MEMUTIL}% MacroDensity=${MACRO_DENSITY}Mb/mm²"
}

echo "===== Mid SKU sweep (storage-mode proxy) ====="
# Mid SKU: high cellBit + sequential op + big subArray + low ADC precision
for model in Qwen35_9B Qwen3VL_30B_A3B; do
  echo "--- Model: $model ---"
  run_config mid "M1_22nm_4bit_512sub_32mux_16lvl_seq"   22 4 512 32 16 1 $model
  run_config mid "M2_22nm_4bit_1024sub_64mux_8lvl_seq"   22 4 1024 64 8 1 $model
  run_config mid "M3_22nm_4bit_512sub_16mux_32lvl_par"   22 4 512 16 32 2 $model
  run_config mid "M4_32nm_4bit_512sub_32mux_16lvl_seq"   32 4 512 32 16 1 $model
done

echo "===== Pro SKU sweep (multi-layer post-processed) ====="
# Pro SKU: per-layer NeuroSim sweep + post-processing × N layers + yield^N
for model in Qwen35_27B Qwen35_35B_A3B; do
  echo "--- Model: $model ---"
  run_config pro "P1_22nm_4bit_256sub_16mux_32lvl_par_x6L"   22 4 256 16 32 2 $model
  run_config pro "P2_22nm_4bit_256sub_16mux_16lvl_par_x6L"   22 4 256 16 16 2 $model
  run_config pro "P3_22nm_4bit_512sub_32mux_16lvl_seq_x6L"   22 4 512 32 16 1 $model
  run_config pro "P4_22nm_4bit_256sub_16mux_32lvl_par_x8L"   22 4 256 16 32 2 $model
  run_config pro "P5_14nm_4bit_256sub_16mux_32lvl_par_x6L"   14 4 256 16 32 2 $model
done

cp Param.cpp.orig Param.cpp
echo ""
echo "==== Mid SKU results ($MID_RESULTS) ===="
cat $MID_RESULTS
echo ""
echo "==== Pro SKU results ($PRO_RESULTS) ===="
cat $PRO_RESULTS
