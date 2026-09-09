CONDA_SH_PATH="/home/qluai/miniconda3/etc/profile.d/conda.sh"

tmux kill-session -t icd_start 2>/dev/null || true
# frp
tmux new-session -d -s frp "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && cd /home/qluai/lzy/jointcoder/frp_0.67.0_linux_amd64 && ./frpc -c /home/qluai/lzy/jointcoder/frpc.ini; exec bash'"
# es + ki + agents + run.py
tmux new-session -d -s icd_start "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && bash /home/qluai/lzy/jointcoder/project_deploy/icd_start.sh; exec bash'"

tmux kill-session -t ocr 2>/dev/null || true
    
# ocr
tmux new-session -d -s ocr "bash -c 'source $CONDA_SH_PATH && conda activate Pocr && cd /home/qluai/lzy/jointcoder/project_deploy/PaddleOCR-main/ppstructure && python /home/qluai/lzy/jointcoder/project_deploy/PaddleOCR-main/ppstructure/app_929.py; exec bash'"

tmux kill-session -t qy_w 2>/dev/null || true

# web
tmux new-session -d -s qy_w "bash -c 'cd /home/qluai/lzy/jointcoder/project_deploy/qy_icd/qianyi-web && npm run dev; exec bash'"

tmux kill-session -t qy_b 2>/dev/null || true

# backend
tmux new-session -d -s qy_b "bash -c 'source $CONDA_SH_PATH && conda activate Jcoder && cd /home/qluai/lzy/jointcoder/project_deploy/qy_icd/qy_backend && python manage.py runserver 0.0.0.0:8088; exec bash'"
