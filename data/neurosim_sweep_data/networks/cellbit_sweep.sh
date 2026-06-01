#!/bin/bash
# Phase 47.7.10 W3.5 — cellBit Conservative Sweep (2-bit + 3-bit MLC)
# Tests density-precision tradeoff per Michael's "for conservative testing" ask
# Output: cellbit_sweep_results.csv (20 rows: Mini 4 + Mid 8 + Pro 8)

set -e

BUILD_DIR="/path/to/neurosim"
NEUROSIM_DIR="$BUILD_DIR/Inference_pytorch/NeuroSIM"
NETWORKS_DIR="$BUILD_DIR/networks"

RESULTS="$BUILD_DIR/cellbit_sweep_results.csv"

echo "sku,config,model,d_model_or_resnet,technode,cellBit,subArray,numColMuxed,levelOutput,operationmode,blocks,chipArea_mm2,arrayArea_mm2,adcArea_um2,memUtil_pct,arrayFrac_pct,adcFrac_pct,unit_params_M,macroDensity_Mb_per_mm2" > $RESULTS

cd $NEUROSIM_DIR
[ -f Param.cpp.orig ] || cp Param.cpp Param.cpp.orig

get_params() {
  # Returns params in millions for the given model+unit (block for LLM, full for ResNet18)
  case $1 in
    ResNet18) echo "11.7";;
    Qwen35_9B) echo "177.2";;
    Qwen3VL_30B_A3B) echo "45.1";;
    Qwen35_27B) echo "275.3";;
    Qwen35_35B_A3B) echo "68.8";;
  esac
}

get_blocks() {
  case $1 in
    ResNet18) echo "1";;
    Qwen35_4B) echo "36";;
    Qwen35_9B) echo "32";;
    Qwen3VL_30B_A3B) echo "28";;
    Qwen35_35B_A3B) echo "32";;
    Qwen35_27B) echo "48";;
  esac
}

get_d_model() {
  case $1 in
    ResNet18) echo "0";;
    Qwen35_9B) echo "4096";;
    Qwen3VL_30B_A3B) echo "2048";;
    Qwen35_27B) echo "5120";;
    Qwen35_35B_A3B) echo "2560";;
  esac
}

get_netfile() {
  case $1 in
    ResNet18) echo "NetWork_ResNet18.csv";;
    Qwen35_9B) echo "$NETWORKS_DIR/NetWork_Qwen35_9B_block.csv";;
    Qwen3VL_30B_A3B) echo "$NETWORKS_DIR/NetWork_Qwen3VL_30B_A3B_block.csv";;
    Qwen35_27B) echo "$NETWORKS_DIR/NetWork_Qwen35_27B_block.csv";;
    Qwen35_35B_A3B) echo "$NETWORKS_DIR/NetWork_Qwen35_35B_A3B_block.csv";;
  esac
}

run_config() {
  local sku=$1
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
  make > /tmp/neurosim_v13_cellbit_${config_name}.log 2>&1

  blocks=$(get_blocks $model)
  unit_params_M=$(get_params $model)
  d_model=$(get_d_model $model)
  netfile=$(get_netfile $model)

  OUTPUT=$(./main $netfile 8 8 2>&1)

  CHIPAREA=$(echo "$OUTPUT" | grep "ChipArea : " | tail -1 | awk '{print $3}')
  ARRAYAREA=$(echo "$OUTPUT" | grep "Total Synaptic Array Area on chip:" | tail -1 | awk '{print $7}')
  ADCAREA_UM=$(echo "$OUTPUT" | grep "Total ADC Area on chip:" | awk '{print $6}')
  MEMUTIL=$(echo "$OUTPUT" | grep "Memory Utilization of Whole Chip:" | awk '{print $6}')

  ARRAYFRAC=$(echo "scale=4; $ARRAYAREA / $CHIPAREA * 100" | bc -l 2>/dev/null || echo "0")
  ADCFRAC=$(echo "scale=4; $ADCAREA_UM / ($CHIPAREA * 1000000) * 100" | bc -l 2>/dev/null || echo "0")

  UNIT_MB=$(echo "$unit_params_M * 8" | bc -l 2>/dev/null || echo "0")
  MACRO_DENSITY=$(echo "scale=4; $UNIT_MB / $CHIPAREA" | bc -l 2>/dev/null || echo "0")

  echo "$sku,$config_name,$model,$d_model,$technode,$cellBit,$subArray,$numColMuxed,$levelOutput,$operationmode,$blocks,$CHIPAREA,$ARRAYAREA,$ADCAREA_UM,$MEMUTIL,$ARRAYFRAC,$ADCFRAC,$unit_params_M,$MACRO_DENSITY" >> $RESULTS
  echo "[$sku $config_name $model] cellBit=$cellBit ChipArea=${CHIPAREA}mm² Array%=${ARRAYFRAC}% MemUtil=${MEMUTIL}% MacroDensity=${MACRO_DENSITY}Mb/mm²"
}

echo "===== Mini SKU cellBit conservative (Config E + F × 2-bit + 3-bit on ResNet18) ====="
run_config mini "E_22nm_2bit_256sub_16mux_16lvl_par"  22 2 256 16 16 2 ResNet18
run_config mini "E_22nm_3bit_256sub_16mux_16lvl_par"  22 3 256 16 16 2 ResNet18
run_config mini "F_22nm_2bit_512sub_32mux_16lvl_par"  22 2 512 32 16 2 ResNet18
run_config mini "F_22nm_3bit_512sub_32mux_16lvl_par"  22 3 512 32 16 2 ResNet18

echo "===== Mid SKU cellBit conservative (M1 + M3 × 2-bit + 3-bit × 2 models) ====="
for model in Qwen35_9B Qwen3VL_30B_A3B; do
  echo "--- Model: $model ---"
  run_config mid "M1_22nm_2bit_512sub_32mux_16lvl_seq"  22 2 512 32 16 1 $model
  run_config mid "M1_22nm_3bit_512sub_32mux_16lvl_seq"  22 3 512 32 16 1 $model
  run_config mid "M3_22nm_2bit_512sub_16mux_32lvl_par"  22 2 512 16 32 2 $model
  run_config mid "M3_22nm_3bit_512sub_16mux_32lvl_par"  22 3 512 16 32 2 $model
done

echo "===== Pro SKU cellBit conservative (P1 + P3 × 2-bit + 3-bit × 2 models) ====="
for model in Qwen35_27B Qwen35_35B_A3B; do
  echo "--- Model: $model ---"
  run_config pro "P1_22nm_2bit_256sub_16mux_32lvl_par_x6L"  22 2 256 16 32 2 $model
  run_config pro "P1_22nm_3bit_256sub_16mux_32lvl_par_x6L"  22 3 256 16 32 2 $model
  run_config pro "P3_22nm_2bit_512sub_32mux_16lvl_seq_x6L"  22 2 512 32 16 1 $model
  run_config pro "P3_22nm_3bit_512sub_32mux_16lvl_seq_x6L"  22 3 512 32 16 1 $model
done

cp Param.cpp.orig Param.cpp
echo ""
echo "==== cellBit conservative results ($RESULTS) ===="
cat $RESULTS
