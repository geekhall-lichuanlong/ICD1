#!/bin/bash

CONDA_SH_PATH="/home/qluai/miniconda3/etc/profile.d/conda.sh"

tmux new-session -d -s sagent1 "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && RAY_memory_monitor_refresh_ms=100 CUDA_VISIBLE_DEVICES=2 swift deploy --model_type qwen3  --model /home/qluai/lzy/jointcoder/sft_agent/surgery_agent1/v0-20251223-144333/checkpoint-450-best --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=1.05 --port 8000; exec bash'"

tmux new-session -d -s sagent2 "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && RAY_memory_monitor_refresh_ms=100 CUDA_VISIBLE_DEVICES=2 swift deploy --model_type qwen3  --model /home/qluai/lzy/jointcoder/sft_agent/surgery_agent2/v0-20251223-155105/checkpoint-250-best --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=1.05 --port 8001; exec bash'"

# tmux new-session -d -s sagent3 "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && RAY_memory_monitor_refresh_ms=1 CUDA_VISIBLE_DEVICES=0 swift deploy --model_type qwen3 --tensor_parallel_size 1 --model /mnt/bigdisk/icdproject/ICD_code_of_Jcoder_Hospital_surgeries/SFT_model/surgeryAgent/agent3_anotherCoding/v0-20250916-123600/checkpoint-300 --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=1 --port 8002; exec bash'"

tmux new-session -d -s sagent4 "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && RAY_memory_monitor_refresh_ms=100 CUDA_VISIBLE_DEVICES=2 swift deploy --model_type qwen3  --model /home/qluai/lzy/jointcoder/sft_agent/surgery_agent3/v0-20251223-161745/checkpoint-600-best --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=1 --port 8003; exec bash'"

tmux new-session -d -s sagent5 "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && RAY_memory_monitor_refresh_ms=100 CUDA_VISIBLE_DEVICES=2 swift deploy --model_type qwen3  --model /home/qluai/lzy/jointcoder/sft_agent/surgery_agent5/v0-20251223-173252/checkpoint-650-best --response_prefix \"<think>\n\n</think>\n\n\" --repetition_penalty=1 --port 8009; exec bash'"

echo "Created tmux sessions: sagent1 to sagent5, all activating conda environment 'Jcoder' and starting corresponding swift deploy commands."

# 进入命令监听循环
while true; do
    read -p "请输入命令（输入 quit 关闭并删除 sagent1-sagent5）： " CMD
    if [[ "$CMD" == "quit" ]]; then
        echo "Closing and killing tmux sessions: sagent1 to sagent5..."
        for i in {1..5}
        do
            tmux kill-session -t sagent$i 2>/dev/null
        done
        echo "Selected tmux sessions closed and deleted."
        break
    else
        echo "无效命令，请重新输入。"
    fi
done