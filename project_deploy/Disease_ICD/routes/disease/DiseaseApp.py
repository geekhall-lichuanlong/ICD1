from flask import Blueprint, Flask, request, jsonify, Response, stream_with_context

from parse import get_url, get_model
from api.CallAPI import mock_llm_stream, mock_llm_stream


disease_app = Blueprint('disease', __name__)


def get_disease_app():
    '''
    获取疾病相关的Flask蓝图
    '''
    return disease_app


# 疾病标准化路由
@disease_app.route('/disease_standardized', methods=['POST'])
def disease_standardized():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]

    # model="checkpoint-2350"
    agent_label = "disease_standardized"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )

# 发现潜在疾病路由
@disease_app.route('/disease_potential_extract', methods=['POST'])
def disease_potential_extract():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]

    # model="checkpoint-2350"
    agent_label = "disease_potential_extract"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )

# 潜在疾病标准化路由
@disease_app.route('/disease_potential_standardized', methods=['POST'])
def disease_potential_standardized():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]

    # model="checkpoint-2350"
    agent_label = "disease_potential_standardized"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )


@disease_app.route('/disease_main_diagnosis', methods=['POST'])
def disease_main_diagnosis():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]

    # model="checkpoint-2350"
    agent_label = "disease_main_diagnosis"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )

@disease_app.route('/disease_screening', methods=['POST'])
def disease_screening():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]
    # print(f" =============================== {content} ===============================")

    # model="checkpoint-2350"
    agent_label = "disease_screening"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )

@disease_app.route('/disease_potential_verify', methods=['POST'])
def disease_potential_verify():
    data = request.json

    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    content = data["messages"][0]["content"]

    # model="checkpoint-2350"
    agent_label = "disease_potential_verify"
    url = get_url(agent_label)
    model = get_model(agent_label)

    print("-----------------------------------")
    print(agent_label)
    # 返回流式响应
    return Response(
        stream_with_context(mock_llm_stream(content, model, url, agent_label=agent_label)),
        content_type='application/json'
    )