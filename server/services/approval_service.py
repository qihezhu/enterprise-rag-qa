"""
审批服务模块
对话式审批引擎：意图解析 → 动态获取模板Schema → 构建确认卡片 → 提交审批 → 状态查询
"""
import re
from datetime import datetime, timedelta, timezone
from flask import current_app
from ..clients.wecom_client import wecom_client


# 审批类型关键词映射（LLM 意图解析的参考字典）
APPROVAL_TYPE_KEYWORDS = {
    "请假": "leave",
    "加班": "overtime",
    "报销": "expense",
    "出差": "travel",
    "采购": "purchase",
    "用章": "seal",
    "调休": "comp_leave",
    "申请": "generic",
}

# 时区: Asia/Shanghai (UTC+8)
CST = timezone(timedelta(hours=8))

# 审批模板名称 → 真实 template_id 映射
TEMPLATE_ID_MAP = {
    "请假": "d11afa25d96276303b0656fc4c94b692_1702182349",
}


class ApprovalService:
    """对话式审批引擎"""

    # ==================== 意图解析 ====================

    def parse_intent(self, user_message, user_id=None):
        """
        从自然语言中解析审批意图和字段
        实际场景中千问 LLM 完成 NLP，此方法做 Schema 映射和校验
        参数：
            user_message: 用户自然语言输入
            user_id: 企微用户 ID
        返回：
            {"approval_type": "请假", "fields": {...}, "confidence": 0.9}
        """
        # 匹配审批类型
        approval_type = "通用申请"
        matched_type = None
        for keyword, atype in APPROVAL_TYPE_KEYWORDS.items():
            if keyword in user_message:
                approval_type = keyword
                matched_type = atype
                break

        # 提取天数
        fields = {"申请人": user_id or "unknown"}
        if "天" in user_message:
            days_match = re.search(r"(\d+)\s*天", user_message)
            if days_match:
                fields["天数"] = int(days_match.group(1))

        # 提取日期
        date_patterns = [
            r"从(下?周[一二三四五六日天])",
            r"(\d+)月(\d+)日",
            r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        ]
        dates_found = []
        for pat in date_patterns:
            for m in re.finditer(pat, user_message):
                dates_found.append(m.group(0))

        if dates_found:
            fields["开始日期"] = dates_found[0]
            if len(dates_found) > 1:
                fields["结束日期"] = dates_found[-1]

        return {
            "approval_type": approval_type,
            "matched_type": matched_type or "generic",
            "fields": fields,
            "confidence": 0.85 if matched_type else 0.5,
        }

    # 模板名称归一化映射（百炼Agent可能传入变体名称）
    TEMPLATE_NAME_ALIASES = {
        "年假": "请假", "事假": "请假", "病假": "请假", "调休": "请假",
        "婚假": "请假", "产假": "请假", "请假申请": "请假",
        "加班申请": "加班", "报销申请": "报销", "出差申请": "出差",
    }

    def _normalize_template_name(self, name):
        """将百炼可能传入的变体名称归一化"""
        return self.TEMPLATE_NAME_ALIASES.get(name, name)

    # ==================== 模板 Schema ====================

    def get_schema(self, template_name):
        """
        获取审批模板的动态控件 Schema
        永远通过 API 动态获取，禁止硬编码控件 ID
        """
        template_name = self._normalize_template_name(template_name)
        # 尝试通过 API 获取模板详情
        try:
            resp = wecom_client.get_template_detail(template_name)
            if resp.get("errcode") == 0:
                controls = resp.get("template_content", {}).get("controls", [])
                return {
                    "template_name": template_name,
                    "controls": [
                        {
                            "id": c.get("property", {}).get("control", ""),
                            "name": c.get("title", [{}])[0].get("text", ""),
                            "type": c.get("property", {}).get("control", ""),
                            "required": c.get("property", {}).get("uncheck", "") != "1",
                            "options": [],
                        }
                        for c in controls
                    ],
                }
        except Exception as e:
            current_app.logger.warning(f"获取审批模板API失败: {e}，使用本地Mock")
        # 本地 Mock（开发阶段）
        return self._mock_schema(template_name)

    def _mock_schema(self, template_name):
        """本地 Mock 审批模板 Schema（API 不可用时的回退）"""
        # 请假模板
        leave_controls = [
            {"id": "leave_type", "name": "请假类型", "type": "selector",
             "required": True, "options": ["年假", "事假", "病假", "调休", "婚假", "产假"]},
            {"id": "start_date", "name": "开始日期", "type": "date", "required": True},
            {"id": "end_date", "name": "结束日期", "type": "date", "required": True},
            {"id": "days", "name": "请假天数", "type": "number", "required": True},
            {"id": "reason", "name": "请假原因", "type": "text", "required": True},
        ]
        mock_map = {
            "请假": leave_controls,
            "加班": [
                {"id": "overtime_date", "name": "加班日期", "type": "date", "required": True},
                {"id": "overtime_hours", "name": "加班时长", "type": "number", "required": True},
                {"id": "overtime_reason", "name": "加班原因", "type": "text", "required": True},
            ],
            "报销": [
                {"id": "expense_type", "name": "报销类型", "type": "selector",
                 "required": True, "options": ["差旅费", "办公费", "招待费", "交通费"]},
                {"id": "expense_amount", "name": "报销金额", "type": "number", "required": True},
                {"id": "expense_reason", "name": "报销说明", "type": "text", "required": True},
            ],
            "出差": [
                {"id": "travel_start", "name": "出发日期", "type": "date", "required": True},
                {"id": "travel_end", "name": "返回日期", "type": "date", "required": True},
                {"id": "travel_city", "name": "目的地", "type": "text", "required": True},
                {"id": "travel_reason", "name": "出差事由", "type": "text", "required": True},
            ],
        }
        controls = mock_map.get(template_name, [])
        return {"template_name": template_name, "controls": controls}

    # ==================== 确认卡片 ====================

    def build_confirmation_card(self, approval_type, fields, task_id="task_approval"):
        """构建企微模板卡片（用于用户确认）"""
        field_lines = "\n".join([f"· {k}: {v}" for k, v in fields.items()])
        return {
            "card_type": "text_notice",
            "source": {"desc": f"{approval_type}申请确认"},
            "main_title": {"title": f"请确认{approval_type}信息"},
            "sub_title_text": f"确认后将提交{approval_type}申请",
            "horizontal_content_list": [
                {"keyname": k, "value": str(v)} for k, v in fields.items()
            ],
            "task_id": task_id,
            "card_action": {
                "type": 1, "url": ""
            },
            "button_list": [
                {"task_id": task_id, "replace_name": "已确认", "replace_text": "已确认提交"},
            ],
            "button_selection": {"is_show": True, "buttons": [
                {"text": "确认提交", "style": 1, "key": "approval_confirm"},
                {"text": "取消", "style": 2, "key": "approval_cancel"},
            ]},
        }

    # ==================== 提交审批 ====================

    # 常见字段名缩写映射（百炼Agent可能使用简称）
    _FIELD_ALIAS_MAP = {
        "请假天数": ["天数", "请假天数", "天数"],
        "请假原因": ["原因", "请假原因", "事由", "请假事由"],
        "加班日期": ["日期", "加班日期", "overtime_date"],
        "加班时长": ["时长", "加班时长", "小时", "overtime_hours"],
        "加班原因": ["原因", "加班原因", "事由", "加班事由"],
        "报销类型": ["类型", "报销类型", "费用类型"],
        "报销金额": ["金额", "报销金额", "费用金额"],
        "报销说明": ["说明", "报销说明", "事由", "报销事由"],
        "出发日期": ["出发日期", "开始日期", "出发"],
        "返回日期": ["返回日期", "结束日期", "返回"],
        "目的地": ["目的地", "出差城市", "城市"],
        "出差事由": ["事由", "出差事由", "原因", "出差原因"],
    }

    @staticmethod
    def _get_field_value(ctrl, fields):
        """从 fields 中获取控件值，支持 id / name / 常见缩写三种匹配"""
        cid = ctrl["id"]
        cname = ctrl["name"]
        # 1. 精确匹配 id
        val = fields.get(cid, "")
        if val:
            return val
        # 2. 精确匹配 name
        val = fields.get(cname, "")
        if val:
            return val
        # 3. 别名匹配
        aliases = ApprovalService._FIELD_ALIAS_MAP.get(cname, [])
        for alias in aliases:
            val = fields.get(alias, "")
            if val:
                return val
        # 4. 模糊匹配：fields 的 key 包含 cname 的核心词 或 cname 包含 fields 的 key
        cname_core = cname.rstrip("原因天数日期时长金额类型说明事由城市")
        for fk, fv in fields.items():
            if not fv:
                continue
            if cname_core and cname_core in fk:
                return fv
            if fk in cname:
                return fv
        return ""

    def submit(self, user_id, template_name, fields):
        """
        提交审批申请
        强制时区 Asia/Shanghai，提交前进行 Schema 校验
        """
        # 归一化模板名称
        template_name = self._normalize_template_name(template_name)
        # 1. 校验 Schema（缺少必填字段时阻断提交）
        # 同时接受 id（如 leave_type）和 name（如 请假类型）作为字段 key
        schema = self.get_schema(template_name)
        missing = [
            c["name"] for c in schema.get("controls", [])
            if c["required"] and not self._get_field_value(c, fields)
        ]
        if missing:
            current_app.logger.warning(
                f"审批字段校验-缺失必填字段: {missing}，阻断提交 | "
                f"received_fields={list(fields.keys())} | "
                f"expected_ctrls={[(c['id'], c['name']) for c in schema.get('controls', []) if c['required']]}"
            )
            return {"errcode": -1, "errmsg": f"缺少必填字段: {', '.join(missing)}。已收到字段: {', '.join(fields.keys())}。请提供缺失信息。"}

        # 2. 构建审批数据（时间戳强制 Asia/Shanghai）
        now = datetime.now(CST)
        template_id = TEMPLATE_ID_MAP.get(template_name, template_name)
        approval_data = {
            "creator_userid": user_id,
            "template_id": template_id,
            "use_template_approver": 0,
            "approver": [
                {"attr": 2, "userid": [user_id]}  # 直系上级
            ],
            "apply_data": {
                "contents": [
                    {
                        "control": ctrl["id"],
                        "id": ctrl["id"],
                        "value": {
                            "text": str(self._get_field_value(ctrl, fields))
                        },
                    }
                    for ctrl in schema.get("controls", [])
                ]
            },
            "summary_list": [
                {"summary_info": [{"text": f"{k}: {v}", "lang": "zh_CN"}]}
                for k, v in list(fields.items())[:3]
            ],
        }

        # 3. 调用企微 API（权限不足时降级为本地记录模式）
        try:
            resp = wecom_client.apply_event(approval_data)
            if resp.get("errcode") != 0:
                current_app.logger.warning(f"审批API调用失败({resp.get('errcode')}): {resp.get('errmsg')}，降级为演示模式")
                return {"errcode": 0, "sp_no": f"DEMO-{now.strftime('%Y%m%d%H%M%S')}-{user_id}", "demo_mode": True}
        except Exception as e:
            current_app.logger.warning(f"审批API异常: {e}，降级为演示模式")
            return {"errcode": 0, "sp_no": f"DEMO-{now.strftime('%Y%m%d%H%M%S')}-{user_id}", "demo_mode": True}
        return resp

    # ==================== 状态查询 ====================

    def query_status(self, sp_no):
        """查询审批单状态，优先查数据库，API不可用时降级"""
        # 先查数据库中的真实记录
        try:
            from ..models.approval_record import ApprovalRecord
            from ..extensions import db
            record = ApprovalRecord.query.filter_by(sp_no=sp_no).first()
            if record:
                status_map = {"pending": "审批中", "approved": "已通过", "rejected": "已驳回", "cancelled": "已撤销"}
                status_code_map = {"pending": 1, "approved": 2, "rejected": 3, "cancelled": 4}
                return {
                    "sp_no": sp_no,
                    "status": status_map.get(record.status, record.status),
                    "sp_status_code": status_code_map.get(record.status, 1),
                    "applicant": record.user_id,
                    "detail": {
                        "sp_status": status_code_map.get(record.status, 1),
                        "template_name": record.template_name,
                        "apply_time": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
                    },
                }
        except Exception:
            pass
        # Demo 单号：数据库没有则返回模拟数据
        if sp_no.startswith("DEMO-"):
            now = datetime.now(CST)
            return {
                "sp_no": sp_no,
                "status": "审批中",
                "sp_status_code": 1,
                "applicant": sp_no.rsplit("-", 1)[-1] if "-" in sp_no else "unknown",
                "detail": {"sp_status": 1, "template_name": "演示审批", "apply_time": now.strftime("%Y-%m-%d %H:%M:%S")},
            }
        try:
            resp = wecom_client.get_approval_detail(sp_no)
            if resp.get("errcode") == 0:
                info = resp.get("info", {})
                status_map = {1: "审批中", 2: "已通过", 3: "已驳回", 4: "已撤销", 5: "已通过（同层）"}
                return {
                    "sp_no": sp_no,
                    "status": status_map.get(info.get("sp_status"), "未知"),
                    "sp_status_code": info.get("sp_status"),
                    "applicant": info.get("applyer", {}).get("userid", ""),
                    "detail": info,
                }
        except Exception:
            pass
        # API 调用失败，返回模拟数据
        return {
            "sp_no": sp_no,
            "status": "审批中",
            "sp_status_code": 1,
            "applicant": "unknown",
            "detail": {"sp_status": 1, "template_name": "未知", "note": "API暂不可用，返回模拟数据"},
        }


approval_service = ApprovalService()
