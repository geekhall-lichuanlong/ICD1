#!/bin/bashpwd

CONDA_SH_PATH="/home/qluai/miniconda3/etc/profile.d/conda.sh"

# # Step 1: Start Elasticsearch
# tmux has-session -t es_el 2>/dev/null || tmux new-session -d -s es_el "bash -c 'source $CONDA_SH_PATH /home/es/elasticsearch-8.17.2/bin/elasticsearch; exec bash'"

# # Step 2: Start Kibana
# tmux has-session -t kb 2>/dev/null || tmux new-session -d -s kb "bash -c 'source $CONDA_SH_PATH /home/qluai/lzy/jointcoder/es/kibana-8.17.2/bin/kibana; exec bash'"

# Step 3: Start Disease Agent
if tmux has-session -t Alldisease_agent 2>/dev/null; then
    tmux kill-session -t Alldisease_agent
fi

tmux new-session -d -s Alldisease_agent "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && bash /home/qluai/lzy/jointcoder/project_deploy/disease.sh; exec bash'"

# Step 4: Start Surgery Agent
if tmux has-session -t Allsurgery_agent 2>/dev/null; then
    tmux kill-session -t Allsurgery_agent
fi

tmux new-session -d -s Allsurgery_agent "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && bash /home/qluai/lzy/jointcoder/project_deploy/surgery.sh; exec bash'"

# Step 5: Start ICD System
if tmux has-session -t dicd 2>/dev/null; then
    tmux kill-session -t dicd
fi

tmux new-session -d -s dicd "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && cd /home/qluai/lzy/jointcoder/project_deploy/Disease_ICD && bash /home/qluai/lzy/jointcoder/project_deploy/Disease_ICD/run.sh; exec bash'"

# Step 6: Start Surgery ICD
if tmux has-session -t sicd 2>/dev/null; then
    tmux kill-session -t sicd
fi

tmux new-session -d -s sicd "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && cd /home/qluai/lzy/jointcoder/project_deploy/Surgeries_ICD/ && bash /home/qluai/lzy/jointcoder/project_deploy/Surgeries_ICD/run.sh; exec bash'"

# Quit function: Kill all tmux sessions (main six + agent1-5 + sagent1-5)
while true; do
    read -p "请输入命令（输入 quit 关闭并删除所有会话）： " CMD
    if [[ "$CMD" == "quit" ]]; then
        # Kill main six sessions
        for sess in es_el kb disease_agent surgery_agent dicd sicd; do
            tmux kill-session -t $sess 2>/dev/null
        done

        # Kill agent1-5 and sagent1-5 sessions
        for i in {1..5}; do
            tmux kill-session -t agent$i 2>/dev/null
            tmux kill-session -t sagent$i 2>/dev/null
        done

        echo "All tmux sessions killed."
        break
    else
        echo "无效命令，请重新输入。"
    fi
done