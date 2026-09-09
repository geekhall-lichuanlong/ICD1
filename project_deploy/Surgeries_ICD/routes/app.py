from flask import Flask, request, jsonify, Response, stream_with_context
import json
from datetime import datetime
from routes.surgery.SurgeryApp import get_surgery_app
from parse import get_flask_url, get_url

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 确保中文字符不被转义

# 注册蓝图
app.register_blueprint(get_surgery_app(), url_prefix='/surgery')

# 获取Flask应用的URL
url = get_flask_url()

# 初始流程
@app.route('/qwen3/surgeries_diagnosis', methods=['POST'])
def surgery_diagnosis():
    '''
    处理前端发送的诊断请求
    '''
    try:
        
        # 读取请求数据
        data = json.loads(request.data)
        # print("请求数据:", data)  # 调试信息
        
        
        messages = data.get("messages")
        content = messages[0]["content"]
        
        print(content)

        content = json.loads(content)

        print('loads 成功')
        # print("收到诊断请求，内容如下：")
        # print(content["手术名称"])  # 调试信息
        
        kong=0
        if  content["手术名称"] == "" or content["手术经过"] == "":
            kong=1
            print("手术名称为空")
            error_content = "手术名称或手术经过为空，请检查输入病例！"
            table_response = {
                "agent_name": "错误提示",
                        "message": {
                        "content": error_content,
                        "reasoning_content": ""
                    },
                    "next_agent": 0,
                    "next_agent_url": "",
                    "usage": 0
            }
            return jsonify({
                "type": "agent_response",
                "agent_name": "错误信息",
                "raw_response": json.dumps(table_response, ensure_ascii=False),
                "message": table_response["message"],
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }), 200
        
        if kong==1:
            return jsonify({"error": "Invalid request format"}), 400
        
        if not data or "messages" not in data:
            return jsonify({"error": "Invalid request format"}), 400
        
       
        from icd.GetICD import get_icd
        response = Response(
            stream_with_context(get_icd(data)),
            content_type='application/json'
        )
        return response
        
    except Exception as e:
        print(f"诊断处理错误: {e}")
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




if __name__ == "__main__":
    # 启动Flask应用
    app.run(host="0.0.0.0", port=6000)