from flask import Flask, request, jsonify, Response, stream_with_context
import json
import os


from routes.disease.DiseaseApp import get_disease_app   
from routes.surgery.SurgeryApp import get_surgery_app
from parse import get_flask_url, get_url

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 确保中文字符不被转义

# 注册蓝图
app.register_blueprint(get_disease_app(), url_prefix='/disease') 
app.register_blueprint(get_surgery_app(), url_prefix='/surgery')

# 获取Flask应用的URL
url = get_flask_url()


def _memory_admin_authorized():
    """Optional protection for memory-management endpoints.

    Set MEMORY_ADMIN_TOKEN in production and send the same value through the
    X-Memory-Admin-Token header. Local development remains frictionless when the
    environment variable is not set.
    """
    expected = os.getenv("MEMORY_ADMIN_TOKEN", "").strip()
    return not expected or request.headers.get("X-Memory-Admin-Token", "") == expected

# 初始流程
@app.route('/qwen3/diagnosis_qwen', methods=['POST'])
def disease_diagnosis():
    '''
    处理前端发送的疾病诊断请求
    '''
    try:
        # 读取请求数据
        data = json.loads(request.data)
        # print(f"Received data: {data}")
        if not data or "messages" not in data:
            return jsonify({"error": "Invalid request format"}), 400
       
        from icd.disease.GetICD import get_icd
        response = Response(
            stream_with_context(get_icd(data)),
            content_type='application/json'
        )
        return response

    except Exception as e:
        print(f"疾病诊断处理错误: {e}")
        error_response = {
            "type": "error",
            "status": "error",
            "message": f"处理失败: {str(e)}"
        }
        error_json = json.dumps(error_response, ensure_ascii=False, indent=2)
        return Response(
            error_json,
            content_type='application/json; charset=utf-8',
            status=500
        )


@app.route('/qwen3/memories', methods=['GET', 'POST'])
def disease_long_term_memories():
    """Manage reviewed cross-case ICD coding knowledge."""
    if not _memory_admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    from icd.disease.memory import get_long_term_memory_repository

    repository = get_long_term_memory_repository()
    tenant_id = request.args.get('tenant_id', 'default')
    if request.method == 'GET':
        limit = request.args.get('limit', 100)
        try:
            memories = repository.list(tenant_id=tenant_id, limit=int(limit))
        except ValueError:
            return jsonify({"error": "limit 必须是整数"}), 400
        return jsonify({"tenant_id": tenant_id, "memories": memories})

    body = request.get_json(silent=True) or {}
    tenant_id = str(body.get('tenant_id') or 'default')
    try:
        memory = repository.add(
            tenant_id=tenant_id,
            content=body.get('content', ''),
            keywords=body.get('keywords') or [],
            source=body.get('source') or 'manual_review',
            approved=body.get('approved') is True,
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"message": "长期记忆已保存", "memory": memory}), 201


@app.route('/qwen3/memories/<memory_id>', methods=['DELETE'])
def delete_disease_long_term_memory(memory_id):
    if not _memory_admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    from icd.disease.memory import get_long_term_memory_repository

    tenant_id = request.args.get('tenant_id', 'default')
    deleted = get_long_term_memory_repository().deactivate(
        memory_id, tenant_id=tenant_id
    )
    return jsonify({"deleted": bool(deleted), "memory_id": memory_id})


@app.route('/qwen3/short-term/<thread_id>', methods=['DELETE'])
def delete_disease_short_term_memory(thread_id):
    if not _memory_admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    from icd.disease.langgraph_workflow import delete_short_term_memory

    delete_short_term_memory(thread_id)
    return jsonify({"deleted": True, "thread_id": thread_id})


# @app.route('/surgeries_diagnosis', methods=['POST'])
# def surgery_diagnosis():
#     '''
#     处理前端发送的手术诊断请求（待完成）
#     '''
#     # 读取请求数据
#     data = request.json

#     # 如果数据格式或URL不正确，返回错误信息
#     if not data or "messages" not in data:
#         return jsonify({"error": "Invalid request format"}), 400

#     url = get_url("surgery_standardized")
#     if not url or url == 'none':
#         return jsonify({"error": "Invalid url format"}), 400
    
#     from icd.surgery.GetICD import get_icd
#     get_icd(data)


if __name__ == "__main__":
    # 启动Flask应用
    app.run(host="0.0.0.0", port=5000)
