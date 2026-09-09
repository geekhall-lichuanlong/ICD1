from flask import Blueprint, Flask, request, jsonify, Response, stream_with_context


from parse import get_url,get_model
from api.CallAPI import mock_llm_stream, call_api_stream
surgery_app = Blueprint('surgery', __name__)    




def get_surgery_app():
    '''
    获取手术相关的Flask蓝图
    '''
    return surgery_app

#  手术标准化路由
@surgery_app.route('/surgery_standardized', methods=['POST'])
def surgery_standardized():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]


    agent_label = "surgery_standardized"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )
    
#  提取额外手术路由
@surgery_app.route('/surgery_additional', methods=['POST'])
def surgery_additional():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]

    agent_label = "surgery_additional"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )
    
# 另编码路由
@surgery_app.route('/surgery_another_coding', methods=['POST'])
def surgery_another_coding():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]


    agent_label = "surgery_another_coding"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )

# 排序路由
@surgery_app.route('/surgery_sorting', methods=['POST'])
def surgery_sorting():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]


    agent_label = "surgery_sorting"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )
# 筛查路由
@surgery_app.route('/surgery_screening', methods=['POST'])
def surgery_screening():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]


    agent_label = "surgery_screening"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )
