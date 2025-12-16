# 腾讯云 ASR 配置
# 请在腾讯云控制台获取以下信息：
# https://console.cloud.tencent.com/cam/capi
import os

TENCENT_SECRET_ID = os.environ.get('TENCENT_SECRET_ID', 'your_secret_id')
TENCENT_SECRET_KEY = os.environ.get('TENCENT_SECRET_KEY', 'your_secret_key')
TENCENT_APPID = os.environ.get('TENCENT_APPID', '1258394716')

# AI 对话配置
AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://api-inference.modelscope.cn/v1')
AI_API_KEY = os.environ.get('AI_API_KEY', 'your_api_key')
AI_MODEL = os.environ.get('AI_MODEL', 'Qwen/Qwen3-Coder-480B-A35B-Instruct')
