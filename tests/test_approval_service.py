"""审批服务单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from server.services.approval_service import ApprovalService, APPROVAL_TYPE_KEYWORDS


class TestApprovalIntentParsing:
    """意图解析测试"""

    def test_parse_leave_intent(self):
        """识别请假意图并提取天数和日期"""
        svc = ApprovalService()
        result = svc.parse_intent("我要请假3天从下周一开始")
        assert result["approval_type"] == "请假"
        assert result["fields"].get("天数") == 3
        assert "下周一" in str(result["fields"].get("开始日期", ""))

    def test_parse_overtime_intent(self):
        svc = ApprovalService()
        result = svc.parse_intent("申请加班，明天晚上")
        assert result["approval_type"] == "加班"

    def test_parse_expense_intent(self):
        svc = ApprovalService()
        result = svc.parse_intent("报销差旅费500元")
        assert result["approval_type"] == "报销"

    def test_parse_unknown_intent(self):
        svc = ApprovalService()
        result = svc.parse_intent("帮我看看今天的天气")
        assert result["approval_type"] == "通用申请"
        assert result["confidence"] < 0.6


@pytest.fixture
def svc():
    return ApprovalService()


class TestSchemaMock:
    """Mock Schema 测试"""

    def test_leave_schema(self, svc, app):
        with app.app_context():
            schema = svc.get_schema("请假")
        assert schema["template_name"] == "请假"
        assert len(schema["controls"]) >= 4
        required_fields = [c["name"] for c in schema["controls"] if c["required"]]
        assert "请假类型" in required_fields
        assert "开始日期" in required_fields

    def test_unknown_template(self, svc, app):
        with app.app_context():
            schema = svc.get_schema("未知模板")
        assert len(schema["controls"]) == 0


class TestCardBuilding:
    """卡片构建测试"""

    def test_build_confirmation_card(self, svc):
        card = svc.build_confirmation_card("请假", {
            "请假类型": "年假", "开始日期": "6月17日", "天数": 3
        })
        assert card["card_type"] == "text_notice"
        assert "确认" in card["main_title"]["title"]
        assert len(card["button_selection"]["buttons"]) == 2


class TestSubmitValidation:
    """提交校验测试"""

    @patch.object(ApprovalService, "get_schema")
    def test_missing_required_field(self, mock_schema, svc, app):
        mock_schema.return_value = {
            "template_name": "请假",
            "controls": [
                {"id": "leave_type", "name": "请假类型", "type": "selector", "required": True},
                {"id": "start_date", "name": "开始日期", "type": "date", "required": True},
            ],
        }
        with app.app_context():
            result = svc.submit("user1", "请假", {"请假类型": "年假"})
        assert result["errcode"] == -1
        assert "开始日期" in result["errmsg"]
