#!/bin/bash
###################################################################################
# Poseidon Batch Simulation Script
#
# This script is used to run Poseidon simulations in batch mode.
# It builds the project, prepares the environment, and executes multiple experiments
# with different configurations in parallel.
# Usage: ./batch.sh
###################################################################################

# 默认参数
conda activate py27
MAX_JOBS=36
ccname="poseidon"

# Gear experiment setting:
# label="" 
# exp_list=("trace_twoflow" "trace_convergence_dc" "trace_start_exit")
# topo_list=("topo_cross_dc_100G")
# md_strategy_list=("rtt")
# poseidon_m_list=("0.01" "0.025" "0.05" "0.1" "0.25")
# has_win_list=("0" "1")

label="" 
exp_list=("trace_twoflow" "trace_convergence_dc" "trace_start_exit")
topo_list=("topo_cross_dc_25G")
md_strategy_list=("rtt")
poseidon_m_list=("0.01" "0.025" "0.05" "0.1" "0.25" "0.5")
has_win_list=("0" "1")


# brownfield setting:  need modift third.cc and rdma-hw.cc for brownfield switch and brownfield algorithm
# label="brownfield"
# exp_list=("trace_twoflow")
# topo_list=("topo_cross_dc_100G")
# md_strategy_list=("rtt")
# poseidon_m_list=("0.01" "0.025" "0.05" "0.1" "0.25")
# has_win_list=("0" "1")

declare -A bw_map=(
    ["topo_cross_dc_10G"]=10
    ["topo_cross_dc_25G"]=25
    ["topo_cross_dc_100G"]=100
    ["topo_muti_hop"]=10
)
declare -A simulation_time_map=(
    ["trace_twoflow_inner"]=4
    ["trace_twoflow"]=4
    ["trace_start_exit"]=7
    ["trace_convergence_dc"]=9
    ["trace_muti_hop"]=3
)
declare -A exp_code_map=(
    ["trace_twoflow_inner"]=1
    ["trace_twoflow"]=1
    ["trace_start_exit"]=2
    ["trace_convergence_dc"]=3
    ["trace_muti_hop"]=4
)

mkdir -p ./results/data
declare -A pid_to_name
declare -A pid_to_idx
declare -A pid_to_start_time
declare -a all_pids

log() {
    local message="$2"
    local level="${1:-info}"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    # 根据日志级别设置颜色
    case "$level" in
        info) color="\033[0;32m" ;;  # 绿色
        WARNING) color="\033[0;33m" ;;  # 黄色
        INFO) color="\033[0;31m" ;;  # 红色
        *) color="\033[0m" ;;  # 默认颜色
    esac
    echo -e "${color}[$timestamp] [$level] $message\033[0m"
}

print_progress() {
    local current=$1
    local total=$2
    local bar_length=40

    local percent=$(( 100 * current / total ))
    local filled=$(( bar_length * current / total ))
    local empty=$(( bar_length - filled ))

    local bar
    local spaces
    bar=$(printf "%0.s#" $(seq 1 $filled))
    spaces=$(printf "%0.s-" $(seq 1 $empty))
    echo -ne "[${bar}${spaces}] ${percent}%% ($current/$total)\r"
}

calc_total_tasks() {
    local total=0
    for exp in "${exp_list[@]}"; do
        for topo in "${topo_list[@]}"; do
            for md_strategy in "${md_strategy_list[@]}"; do
                for poseidon_m in "${poseidon_m_list[@]}"; do
                    for has_win in "${has_win_list[@]}"; do
                        local bw=${bw_map[$topo]}
                        local out_name="{$exp}_{$topo}_{${bw}G}_{$ccname}_{$md_strategy}_{m=$poseidon_m}_{win=$has_win}"
                        local out_path="./results/data/${out_name}.txt"
                        if [ ! -f "$out_path" ]; then
                            ((total++))
                        fi
                    done
                done
            done
        done
    done
    echo "$total"
}

# 启动任务
run_tasks() {
    local completed_tasks=0
    local cpu_index=0
    local total_tasks
    total_tasks=$(calc_total_tasks)
    log "INFO" "Total tasks to run: $total_tasks with max concurrency of $MAX_JOBS"

    idx=0
    for exp in "${exp_list[@]}"; do
        for topo in "${topo_list[@]}"; do
            for md_strategy in "${md_strategy_list[@]}"; do
                for poseidon_m in "${poseidon_m_list[@]}"; do
                    for has_win in "${has_win_list[@]}"; do
                        local bw=${bw_map[$topo]}
                        local simulation_time=${simulation_time_map[$exp]}
                        local exp_code=${exp_code_map[$exp]}
                        local out_name="{$exp}_{$topo}_{${bw}G}_{$ccname}_{$md_strategy}_{m=$poseidon_m}_{win=$has_win}"
                        if [ "$label" != "" ]; then
                            out_name="${out_name}_{$label}"
                        fi
                        local out_path="./results/data/${out_name}.txt"

                        if [ -f "$out_path" ]; then
                            log "WARNING" "[Skip] $out_name already exists."
                            continue
                        fi

                        log "info" "[Experiment $idx]   ($exp $exp_code $simulation_time) Topo:($topo $bw) CC:($ccname $poseidon_m $md_strategy) Config:(has_win:$has_win)"
                        log "info" "   -> [DATA PATH] $out_path"

                        # 控制并发数目，当前运行的任务数达到最大限制时，等待，等待结束后，对Completed任务数进行更新
                        local flag=0 # 设置flag 变量，表示是否需要等待，如果当前运行的任务数达到最大限制，则设置flag为1
                        while [ $(jobs -r | wc -l) -ge $MAX_JOBS ]; do
                            flag=1
                            sleep 1
                            print_progress $completed_tasks $total_tasks
                        done
                        # 如果flag=1的任务结束等待，说明有任务完成了，现在设计一个函数查询该任务的pid和name，然后再设计一个函数根据查询结果更新pid_to_name和all_pids数组，并打印进度条
                        if [ $flag -eq 1 ]; then
                            removed_pids=()
                            for pid in "${all_pids[@]}"; do
                                if ! kill -0 "$pid" 2>/dev/null; then
                                    removed_pids+=("$pid")
                                    name=${pid_to_name[$pid]}
                                    fin_idx=${pid_to_idx[$pid]}
                                    log "INFO" "[Task $fin_idx done] $name completed in $(( $(date +%s) - ${pid_to_start_time[$pid]} )) seconds"
                                fi
                            done
                            for pid in "${removed_pids[@]}"; do
                                # 从 all_pids 中移除 $pid
                                new_all_pids=()
                                for p in "${all_pids[@]}"; do
                                    [[ "$p" != "$pid" ]] && new_all_pids+=("$p")
                                done
                                all_pids=("${new_all_pids[@]}")
                            done
                            completed_tasks=$((completed_tasks + ${#removed_pids[@]}))
                            print_progress $completed_tasks $total_tasks
                        fi

                        # sleep_time=$(( RANDOM % 2 + 5 ))
                        # sleep $sleep_time &

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
                        sleep 1

                        pid=$!
                        pid_to_name[$pid]="$out_name"
                        pid_to_idx[$pid]=$idx
                        pid_to_start_time[$pid]=$(date +%s)
                        all_pids+=($pid)
                        idx=$((idx + 1))
                    done
                done
            done
        done
    done

    # 等待所有任务并显示进度条
    for pid in "${all_pids[@]}"; do
        wait "$pid"
        status=$?
        ((completed_tasks++))
        name=${pid_to_name[$pid]}
        idx=${pid_to_idx[$pid]}
        if [ $status -eq 0 ]; then
            log "INFO" "[Task $idx done] $name (PID $pid) completed successfully in $(( $(date +%s) - ${pid_to_start_time[$pid]} )) seconds"
        else
            log "INFO" "[Task $idx failed] $name (PID $pid) with exit status $status after $(( $(date +%s) - ${pid_to_start_time[$pid]} )) seconds"
        fi
        print_progress $completed_tasks $total_tasks
    done

    log "" "All tasks completed. Total: $completed_tasks/$total_tasks"
}

main() {
    ./waf build
    run_tasks
}

main "$@"