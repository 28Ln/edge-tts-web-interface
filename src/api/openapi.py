"""
OpenAPI 文档生成
"""

from flask import Blueprint, jsonify, render_template_string

openapi_bp = Blueprint('openapi', __name__)

# OpenAPI 规范
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Edge TTS Web Interface API",
        "description": "语音识别、AI对话、语音合成服务 API",
        "version": "2.0.0",
        "contact": {
            "name": "API Support",
        },
    },
    "servers": [
        {"url": "/", "description": "当前服务器"},
        {"url": "/v2", "description": "API v2 (带认证)"},
    ],
    "tags": [
        {"name": "health", "description": "健康检查"},
        {"name": "mcu", "description": "MCU 精简接口"},
        {"name": "mcu-v2", "description": "MCU v2 接口 (带认证)"},
    ],
    "paths": {
        "/health": {
            "get": {
                "tags": ["health"],
                "summary": "健康检查",
                "responses": {
                    "200": {"description": "服务正常"},
                },
            },
        },
        "/mcu/ping": {
            "get": {
                "tags": ["mcu"],
                "summary": "连接测试",
                "responses": {
                    "200": {"description": "返回 pong"},
                },
            },
        },
        "/mcu/status": {
            "get": {
                "tags": ["mcu"],
                "summary": "服务状态",
                "responses": {
                    "200": {
                        "description": "服务状态信息",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/StatusResponse"},
                            },
                        },
                    },
                },
            },
        },
        "/mcu/stt": {
            "post": {
                "tags": ["mcu"],
                "summary": "语音转文字",
                "parameters": [
                    {"name": "engine", "in": "query", "schema": {"type": "string", "default": "tencent"}},
                    {"name": "format", "in": "query", "schema": {"type": "string", "default": "wav"}},
                ],
                "requestBody": {
                    "content": {
                        "audio/wav": {"schema": {"type": "string", "format": "binary"}},
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {"audio": {"type": "string", "format": "binary"}},
                            },
                        },
                    },
                },
                "responses": {
                    "200": {"description": "识别结果 (纯文本)"},
                    "400": {"description": "参数错误"},
                },
            },
        },
        "/mcu/ask": {
            "post": {
                "tags": ["mcu"],
                "summary": "AI 问答",
                "parameters": [
                    {"name": "session", "in": "query", "schema": {"type": "string", "default": "default"}},
                ],
                "requestBody": {
                    "content": {
                        "text/plain": {"schema": {"type": "string"}},
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AskRequest"},
                        },
                    },
                },
                "responses": {
                    "200": {"description": "AI 回答 (纯文本)"},
                    "400": {"description": "参数错误"},
                },
            },
        },
        "/mcu/tts": {
            "get": {
                "tags": ["mcu"],
                "summary": "文字转语音",
                "parameters": [
                    {"name": "text", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "voice", "in": "query", "schema": {"type": "string", "default": "xiaoxiao"}},
                    {"name": "format", "in": "query", "schema": {"type": "string", "default": "wav"}},
                ],
                "responses": {
                    "200": {"description": "音频文件", "content": {"audio/wav": {}}},
                    "400": {"description": "参数错误"},
                },
            },
        },
    },
    "components": {
        "schemas": {
            "StatusResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "asr_engines": {"type": "object"},
                    "ai": {"type": "boolean"},
                    "tts": {"type": "boolean"},
                },
            },
            "AskRequest": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "session": {"type": "string"},
                },
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "error_code": {"type": "string"},
                    "message": {"type": "string"},
                },
            },
        },
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
            },
        },
    },
}


@openapi_bp.route('/openapi.json')
def openapi_json():
    """返回 OpenAPI JSON 规范"""
    return jsonify(OPENAPI_SPEC)


SWAGGER_UI_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>API 文档 - Edge TTS</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({
            url: "/openapi.json",
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
            layout: "BaseLayout"
        });
    </script>
</body>
</html>
'''


@openapi_bp.route('/docs')
def swagger_ui():
    """Swagger UI 文档页面"""
    return render_template_string(SWAGGER_UI_HTML)
