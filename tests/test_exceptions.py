"""
异常处理测试
"""

import pytest
from src.exceptions import (
    AppError,
    ValidationError,
    AudioError,
    ASRError,
    AIError,
    TTSError,
)


def test_app_error():
    """测试基础异常"""
    error = AppError("测试错误")
    assert error.message == "测试错误"
    assert error.code == 500
    assert error.error_code == "INTERNAL_ERROR"
    
    result = error.to_dict()
    assert result['success'] == False
    assert result['error_code'] == "INTERNAL_ERROR"
    assert result['message'] == "测试错误"


def test_validation_error():
    """测试验证错误"""
    error = ValidationError("参数无效")
    assert error.code == 400
    assert error.error_code == "VALIDATION_ERROR"


def test_asr_error():
    """测试 ASR 错误"""
    error = ASRError("识别失败", details="引擎不可用")
    assert error.code == 500
    assert error.error_code == "ASR_ERROR"
    
    result = error.to_dict()
    assert result['details'] == "引擎不可用"


def test_error_inheritance():
    """测试异常继承关系"""
    assert issubclass(ValidationError, AppError)
    assert issubclass(AudioError, AppError)
    assert issubclass(ASRError, AppError)
    assert issubclass(AIError, AppError)
    assert issubclass(TTSError, AppError)
