#!/bin/bash
CONDA_SH_PATH="/home/qluai/miniconda3/etc/profile.d/conda.sh"

# 创建 5 个 tmux 会话（agent1-agent5），每个激活 conda 环境
#!/bin/bash

# 创建 5 个 tmux 会话（agent1-agent5），每个激活 conda 环境后执行指定命令
tmux new-session -d -s agent1 "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && RAY_memory_monitor_refresh_ms=200 CUDA_VISIBLE_DEVICES=3 swift deploy --model_type qwen3  --model /home/qluai/lzy/jointcoder/sft_agent/disease_agent1/v1-20251219-153002/checkpoint-1719-best --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=1.0 --port 8004; exec bash'"

tmux new-session -d -s agent5 "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && RAY_memory_monitor_refresh_ms=100 CUDA_VISIBLE_DEVICES=3 swift deploy --model_type qwen3  --model /home/qluai/lzy/jointcoder/sft_agent/disease_agent5/v2-20251223-105056/checkpoint-1550-best --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=1 --port 8008; exec bash'"

tmux new-session -d -s agent6 "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && RAY_memory_monitor_refresh_ms=100 CUDA_VISIBLE_DEVICES=3 swift deploy --model_type qwen3  --model /home/qluai/lzy/jointcoder/sft_agent/disease_agent_sc/v0-20260202-222219/checkpoint-2775-best --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=1.0 --port 8007; exec bash'"
echo "Created tmux sessions: agent1 to agent5, all activating conda environment 'JcoderICD' and starting corresponding swift deploy commands."

# 进入命令监听循环
while true; do
    read -p "请输入命令（输入 quit 删除并关闭 agent1-agent6）： " CMD
    if [[ "$CMD" == "quit" ]]; then
        echo "Closing and killing tmux sessions: agent1 to agent6..."
        for i in {1..6}
        do
            tmux kill-session -t agent$i 2>/dev/null
        done
        echo "Selected tmux sessions closed and deleted."
        break
    else
        echo "无效命令，请重新输入。"
    fi
done


# #!/bin/bash
# set -euo pipefail

# CONDA_SH_PATH="/home/ubuntu/miniconda3/etc/profile.d/conda.sh"
# CONDA_ENV="Jcoder"

# require_cmd() {
#   command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' not found in PATH"; exit 1; }
# }

# require_file() {
#   [[ -f "$1" ]] || { echo "ERROR: file not found: $1"; exit 1; }
# }

# start_tmux_session() {
#   local session="$1"
#   local ray_refresh="$2"
#   local cuda="$3"
#   local tp="$4"
#   local model="$5"
#   local rep_penalty="$6"
#   local port="$7"

#   tmux has-session -t "$session" 2>/dev/null && tmux kill-session -t "$session" || true

#   tmux new-session -d -s "$session" \
#     "bash -c 'source \"$CONDA_SH_PATH\" && conda activate \"$CONDA_ENV\" && \
#       RAY_memory_monitor_refresh_ms=$ray_refresh CUDA_VISIBLE_DEVICES=$cuda \
#       swift deploy --model_type qwen3 --tensor_parallel_size $tp --model \"$model\" \
#       --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=$rep_penalty --port $port; \
#       exec bash'"
# }

# main() {
#   require_cmd tmux
#   require_file "$CONDA_SH_PATH"

#   # session|RAY_refresh|CUDA|TP|model_path|repetition_penalty|port
#   SESSIONS=(
#     "agent1|100|0|1|/mnt/bigdisk/all_disease/model/agent1/v0-20251211-103553/checkpoint-25776|1.1|8004"
#     "agent5|100|0|1|/mnt/bigdisk/all_disease/model/agent5/v1-20251207-184113/checkpoint-26379|1|8008"
#     "agent6|100|0|1|/mnt/bigdisk/all_disease/model/agent6/v0-20260104-110513/checkpoint-25608|1.1|8007"
#   )

#   CREATED=()
#   for row in "${SESSIONS[@]}"; do
#     IFS='|' read -r session ray cuda tp model rep port <<<"$row"
#     start_tmux_session "$session" "$ray" "$cuda" "$tp" "$model" "$rep" "$port"
#     CREATED+=("$session")
#   done

#   echo "Created tmux sessions: ${CREATED[*]} (conda env: $CONDA_ENV)"

#   while true; do
#     read -r -p "请输入命令（输入 quit 删除并关闭 ${CREATED[*]}）： " CMD
#     if [[ "$CMD" == "quit" ]]; then
#       echo "Closing and killing tmux sessions: ${CREATED[*]}..."
#       for s in "${CREATED[@]}"; do
#         tmux kill-session -t "$s" 2>/dev/null || true
#       done
#       echo "Selected tmux sessions closed and deleted."
#       break
#     else
#       echo "无效命令，请重新输入。"
#     fi
#   done
# }

# main "$@"