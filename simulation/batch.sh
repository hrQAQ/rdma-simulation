#!/bin/bash

./waf build

# exp_list=("trace_twoflow" "trace_convergence_dc" "trace_start_exit" "trace_twoflow_inner" "trace_muti_hop")
exp_list=("trace_muti_hop")
ccname="poseidon"
# topo_list=("topo_cross_dc_10G" "topo_cross_dc_100G" "topo_muti_hop")
topo_list=("topo_muti_hop")
md_strategy_list=("rtt" "ack")
poseidon_m_list=("0.01" "0.05" "0.1" "0.25" "0.5" "1")
has_win_list=("0" "1")
label="brownfield"

declare -A bw_map
declare -A simulation_time_map
declare -A exp_code_map
bw_map=(["topo_cross_dc_10G"]=10 ["topo_cross_dc_100G"]=100 ["topo_muti_hop"]=100)
simulation_time_map=(["trace_twoflow_inner"]=4 ["trace_twoflow"]=4 ["trace_start_exit"]=7 ["trace_convergence_dc"]=9 ["trace_muti_hop"]=3)
exp_code_map=(["trace_twoflow_inner"]=1 ["trace_twoflow"]=1 ["trace_start_exit"]=2 ["trace_convergence_dc"]=3 ["trace_muti_hop"]=4)

mkdir -p ./results/data
declare -A pid_to_name
declare -a all_pids

# 计算总任务数
total_tasks=0

for exp in "${exp_list[@]}"; do
  for topo in "${topo_list[@]}"; do 
    for md_strategy in "${md_strategy_list[@]}"; do
      for poseidon_m in "${poseidon_m_list[@]}"; do
        for has_win in "${has_win_list[@]}"; do 
          out_name="{$exp}_{$topo}_{${bw}G}_{$ccname}_{$md_strategy}_{m=$poseidon_m}_{win=$has_win}"
          out_path="./results/data/${out_name}.txt"
          if [ ! -f "$out_path" ]; then
            ((total_tasks++))
          fi
        done
      done
    done
  done
done

# 当前已完成任务数
completed_tasks=0

# 启动任务

MAX_JOBS=48
CPU_BASE=0
cpu_index=0

for exp in "${exp_list[@]}"; do
  for topo in "${topo_list[@]}"; do 
    for md_strategy in "${md_strategy_list[@]}"; do
      for poseidon_m in "${poseidon_m_list[@]}"; do
        for has_win in "${has_win_list[@]}"; do
          bw=${bw_map[$topo]}
          simulation_time=${simulation_time_map[$exp]}
          exp_code=${exp_code_map[$exp]}

          out_name="{$exp}_{$topo}_{${bw}G}_{$ccname}_{$md_strategy}_{m=$poseidon_m}_{win=$has_win}"
          if [ "$label" != "" ]; then
            out_name="${out_name}_{$label}"
          fi
          out_path="./results/data/${out_name}.txt"

          if [ -f "$out_path" ]; then
            echo "[Skip] $out_name already exists."
            continue
          fi

          echo "[Run] $out_name"
          echo "Running: Experiment:($exp $exp_code $simulation_time) Topo:($topo $bw) CC:($ccname $poseidon_m $md_strategy) Config:(has_win:$has_win)"
          echo "Logging to $out_path"
          echo ""

          # # 控制最大并发数
          # while (( $(jobs -r | wc -l) >= MAX_JOBS )); do
          #   sleep 1
          # done

          # 计算要绑定的 CPU core
          # cpu_core=$(( CPU_BASE + cpu_index % MAX_JOBS ))
          # ((cpu_index++))

          # taskset -c "$cpu_core" \
          python run.py \
            --cc "$ccname" \
            --trace "$exp" \
            --exp_code "$exp_code" \
            --bw "$bw" \
            --topo "$topo" \
            --simulation_time "$simulation_time" \
            --poseidon_m "$poseidon_m" \
            --poseidon_min_rate 1.0 \
            --poseidon_md_strategy "$md_strategy" \
            --has_win "$has_win" \
            --out_name "$out_name" &
        
          pid=$!
          pid_to_name[$pid]="$out_name"
          all_pids+=($pid)

          sleep 1
        done
      done
    done
  done
done


# 实时进度条函数
print_progress() {
  local current=$1
  local total=$2
  local bar_length=40

  local percent=$(( 100 * current / total ))
  local filled=$(( bar_length * current / total ))
  local empty=$(( bar_length - filled ))

  bar=$(printf "%0.s#" $(seq 1 $filled))
  spaces=$(printf "%0.s-" $(seq 1 $empty))
  echo -ne "[${bar}${spaces}] ${percent}%% ($current/$total)\r"
}

# 等待所有任务并显示进度条
for pid in "${all_pids[@]}"; do
  wait "$pid"
  status=$?
  ((completed_tasks++))
  name=${pid_to_name[$pid]}
  if [ $status -eq 0 ]; then
    echo -e "\n[Done] $name (PID $pid)"
  else
    echo -e "\n[Fail] $name (PID $pid, Exit Code $status)"
  fi
  print_progress $completed_tasks $total_tasks
done

echo -e "\nAll tasks completed."
