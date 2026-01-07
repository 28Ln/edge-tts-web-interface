#!/usr/bin/env python3
"""
环境切换脚本 - 一键切换服务器/本地环境

使用方法:
    python scripts/switch_env.py local    # 切换到本地开发环境
    python scripts/switch_env.py server   # 切换到服务器生产环境
    python scripts/switch_env.py show     # 显示当前配置
"""

import sys
import os
import re

ENV_FILE = '.env'

# 预设环境配置
PRESETS = {
    'local': {
        'APP_ENV': 'development',
        'FLASK_DEBUG': '1',
        'LOG_LEVEL': 'DEBUG',
        'RATE_LIMIT_PER_MINUTE': '10000',
    },
    'server': {
        'APP_ENV': 'production',
        'FLASK_DEBUG': '0',
        'LOG_LEVEL': 'INFO',
        'RATE_LIMIT_PER_MINUTE': '100',
    }
}

def read_env():
    """读取 .env 文件"""
    if not os.path.exists(ENV_FILE):
        print(f"错误: {ENV_FILE} 文件不存在")
        print("请先复制 .env.example 为 .env")
        sys.exit(1)
    
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def write_env(content):
    """写入 .env 文件"""
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

def update_env_value(content, key, value):
    """更新环境变量值"""
    pattern = rf'^{key}=.*$'
    replacement = f'{key}={value}'
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count == 0:
        # 如果没找到，添加到文件末尾
        new_content = content.rstrip() + f'\n{key}={value}\n'
    return new_content

def show_current():
    """显示当前配置"""
    content = read_env()
    print("\n当前 .env 配置:")
    print("-" * 40)
    
    keys_to_show = ['APP_ENV', 'FLASK_DEBUG', 'PORT', 'LOG_LEVEL', 'RATE_LIMIT_PER_MINUTE']
    for key in keys_to_show:
        match = re.search(rf'^{key}=(.*)$', content, re.MULTILINE)
        if match:
            print(f"  {key}={match.group(1)}")
    print("-" * 40)

def switch_env(env_name):
    """切换环境"""
    if env_name not in PRESETS:
        print(f"错误: 未知环境 '{env_name}'")
        print(f"可用环境: {', '.join(PRESETS.keys())}")
        sys.exit(1)
    
    content = read_env()
    preset = PRESETS[env_name]
    
    print(f"\n切换到 {env_name} 环境...")
    for key, value in preset.items():
        content = update_env_value(content, key, value)
        print(f"  {key}={value}")
    
    write_env(content)
    print(f"\n✓ 已切换到 {env_name} 环境")
    print("  重启服务生效: py -m src.main")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n可用环境:")
        for name, config in PRESETS.items():
            print(f"  {name}: {config}")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == 'show':
        show_current()
    elif command in PRESETS:
        switch_env(command)
    else:
        print(f"错误: 未知命令 '{command}'")
        print("使用 'local', 'server' 或 'show'")
        sys.exit(1)

if __name__ == "__main__":
    main()
