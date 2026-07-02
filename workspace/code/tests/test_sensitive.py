"""
敏感字段脱敏工具单元测试
"""

import pytest
from utils.sensitive import mask_id_card, mask_phone, mask_email, mask_name, auto_mask


class TestMaskIdCard:
    """身份证号脱敏测试"""

    def test_normal_id_card(self):
        assert mask_id_card("110101199001011234") == "110101********1234"

    def test_short_id_card(self):
        assert mask_id_card("123456") == "123456"

    def test_empty_id_card(self):
        assert mask_id_card("") == ""

    def test_none_id_card(self):
        assert mask_id_card(None) is None

    def test_15_digit_id(self):
        result = mask_id_card("110101900101123")
        assert len(result) == 15
        assert result[:6] == "110101"


class TestMaskPhone:
    """手机号脱敏测试"""

    def test_normal_phone(self):
        assert mask_phone("13800138000") == "138****8000"

    def test_short_phone(self):
        assert mask_phone("123456") == "123456"

    def test_empty_phone(self):
        assert mask_phone("") == ""

    def test_none_phone(self):
        assert mask_phone(None) is None


class TestMaskEmail:
    """邮箱脱敏测试"""

    def test_normal_email(self):
        assert mask_email("zhangsan@company.com") == "z****@company.com"

    def test_short_local_email(self):
        assert mask_email("z@company.com") == "z****@company.com"

    def test_email_without_at(self):
        assert mask_email("notanemail") == "notanemail"

    def test_empty_email(self):
        assert mask_email("") == ""

    def test_none_email(self):
        assert mask_email(None) is None


class TestMaskName:
    """姓名脱敏测试"""

    def test_two_char_name(self):
        assert mask_name("张三") == "张*"

    def test_three_char_name(self):
        assert mask_name("李小明") == "李*明"

    def test_four_char_name(self):
        assert mask_name("欧阳小明") == "欧**明"

    def test_empty_name(self):
        assert mask_name("") == ""

    def test_none_name(self):
        assert mask_name(None) is None


class TestAutoMask:
    """自动脱敏测试"""

    def test_auto_mask_normal(self):
        data = {
            "id_card": "110101199001011234",
            "phone": "13800138000",
            "email": "zhangsan@company.com",
            "name": "张三",
            "position": "工程师",  # 非敏感字段
        }
        result = auto_mask(data)
        assert "********" in result["id_card"]
        assert "****" in result["phone"]
        assert "z****@" in result["email"]
        assert result["position"] == "工程师"

    def test_auto_mask_empty_fields(self):
        data = {"id_card": "", "phone": "", "email": ""}
        result = auto_mask(data)
        assert result["id_card"] == ""
        assert result["phone"] == ""
        assert result["email"] == ""

    def test_auto_mask_partial_fields(self):
        data = {"id_card": "110101199001011234"}
        result = auto_mask(data)
        assert "********" in result["id_card"]
        assert "phone" not in result  # 原字典没有这个字段

    def test_auto_mask_custom_fields(self):
        """自定义脱敏字段"""
        data = {"name": "张三", "position": "工程师"}
        custom = [("name", mask_name)]
        result = auto_mask(data, custom)
        assert result["name"] == "张*"
        assert result["position"] == "工程师"

    def test_auto_mask_original_not_modified(self):
        """确保不修改原始数据"""
        original = {"id_card": "110101199001011234"}
        result = auto_mask(original)
        assert original["id_card"] == "110101199001011234"
        assert result["id_card"] != original["id_card"]
