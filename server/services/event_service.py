"""
事件路由服务
根据企微推送的事件类型分发到对应处理器
"""
from flask import current_app
from .contact_service import contact_service

# 延迟导入避免循环引用
_approval_service = None
_wecom_client = None
_bailian_client = None
_db = None
_ApprovalRecord = None


def _get_approval_service():
    global _approval_service
    if _approval_service is None:
        from .approval_service import approval_service
        _approval_service = approval_service
    return _approval_service


def _get_wecom_client():
    global _wecom_client
    if _wecom_client is None:
        from ..clients.wecom_client import wecom_client
        _wecom_client = wecom_client
    return _wecom_client


def _get_bailian_client():
    global _bailian_client
    if _bailian_client is None:
        from ..clients.bailian_client import bailian_client
        _bailian_client = bailian_client
    return _bailian_client


def _get_db():
    global _db
    if _db is None:
        from ..extensions import db
        _db = db
    return _db


# 待审批缓存: user_id -> {template_name, fields, name, time}
_pending_approval_cache = {}

# 待审批模板跟踪: user_id -> template_name（用于解析字段值响应）
_pending_approval_template = {}

# 模板字段名 → 模板名 反向映射（用于从确认消息推断模板）
_FIELD_TO_TEMPLATE = {
    "请假类型": "请假", "开始日期": "请假", "结束日期": "请假",
    "请假天数": "请假", "请假原因": "请假",
    "加班日期": "加班", "加班时长": "加班", "加班原因": "加班",
    "报销类型": "报销", "报销金额": "报销", "报销说明": "报销",
    "出发日期": "出差", "返回日期": "出差", "目的地": "出差", "出差事由": "出差",
    "采购物品": "采购", "采购金额": "采购", "采购原因": "采购",
    "用章类型": "用章", "用章事由": "用章",
}


def _parse_confirmation_reply(reply_text, user_id):
    """解析百炼返回的确认消息，提取模板和字段，缓存到 _pending_approval_cache"""
    import re
    if "正确吗" not in reply_text and "确认吗" not in reply_text:
        return None
    # 提取 "请确认：" 和 "正确吗？" 之间的内容
    m = re.search(r'请确认[：:]\s*(.+?)[。]?\s*正确吗', reply_text)
    if not m:
        return None
    content = m.group(1)
    # 解析字段: "加班日期2026-06-18，加班时长3小时，加班原因：加急文件"
    # 字段名都在 _FIELD_TO_TEMPLATE 的 key 中
    field_names = list(_FIELD_TO_TEMPLATE.keys())
    # 按长度降序排列，优先匹配长字段名
    field_names.sort(key=lambda x: -len(x))
    fields = {}
    template_name = None
    remaining = content
    for fn in field_names:
        # 匹配: 字段名 + 可选的全角/半角冒号 + 值
        pat = re.escape(fn) + r'[：:]?\s*([^，,]+?)(?=\s*(?:[，,]|$))'
        fm = re.search(pat, remaining)
        if fm:
            val = fm.group(1).strip()
            val = re.sub(r'[。！？!?]+$', '', val)
            fields[fn] = val
            if template_name is None:
                template_name = _FIELD_TO_TEMPLATE.get(fn)
            # 从 remaining 中移除已匹配的部分，避免重复匹配
            remaining = remaining.replace(fm.group(0), '', 1)
    if not fields or not template_name:
        return None
    ctx = {"template_name": template_name, "fields": fields, "name": user_id}
    _pending_approval_cache[user_id] = ctx
    try:
        current_app.logger.info(f"[审批缓存] user={user_id} template={template_name} fields={fields}")
    except RuntimeError:
        pass
    return ctx


CONFIRM_KEYWORDS = {"正确", "确认", "好的", "可以", "行", "对", "是", "嗯",
                    "对的", "是的", "行的", "可以的", "好", "没错", "没问题"}


def _is_confirmation(msg):
    """检测是否为审批确认消息"""
    clean = msg.strip().rstrip("。，,!.！?？ ")
    return clean in CONFIRM_KEYWORDS


class EventService:
    """事件路由器 —— 分发企微回调事件到对应处理器"""

    def __init__(self):
        pass

    def route_event(self, event_type, parsed_data):
        handler_map = {
            "approval_status_change": self.handle_approval_change,
            "external_contact_add": self.handle_external_contact_add,
            "schedule_change": self.handle_schedule_change,
            "task_card_click": self.handle_task_card_click,
            "enter_agent": self.handle_enter_agent,
        }
        # 普通文本消息（MsgType=text，无Event字段）
        msg_type = parsed_data.get("msgtype", "")
        if msg_type == "text" and not event_type:
            return self.handle_text_message(parsed_data)
        handler = handler_map.get(event_type)
        if handler:
            return handler(parsed_data)
        current_app.logger.info(f"[事件路由] 未识别的事件类型: {event_type} msgtype={msg_type}")

    # ==================== P1: 审批状态变更 ====================

    def handle_approval_change(self, data):
        """
        处理审批状态变更回调
        XML 包含 <ApprovalInfo> 节点，status: 1=审批中, 2=已通过, 3=已驳回, 4=已撤销
        """
        sp_no = data.get("sp_no", data.get("approvalinfo", {}).get("sp_no", ""))
        status_code = int(data.get("sp_status", data.get("approvalinfo", {}).get("sp_status", 1)))

        status_map = {1: "pending", 2: "approved", 3: "rejected", 4: "cancelled"}
        new_status = status_map.get(status_code, "pending")

        current_app.logger.info(f"[审批回调] sp_no={sp_no} status={new_status}")

        if not sp_no:
            return

        # 更新数据库记录
        db = _get_db()
        global _ApprovalRecord
        if _ApprovalRecord is None:
            from ..models.approval_record import ApprovalRecord
            _ApprovalRecord = ApprovalRecord

        record = _ApprovalRecord.query.filter_by(sp_no=sp_no).first()
        if record:
            record.status = new_status
            db.session.commit()

            # 审批通过后主动通知申请人
            if new_status == "approved":
                fields = record.fields_json or {}
                detail = " / ".join([f"{k}:{v}" for k, v in fields.items()])
                msg = f"你的{record.template_name}申请已通过审批\n{detail}"
                _get_wecom_client().send_message(record.user_id, "text", msg)

            # 审批被驳回通知
            if new_status == "rejected":
                msg = f"你的{record.template_name}申请已被驳回"
                _get_wecom_client().send_message(record.user_id, "text", msg)
        else:
            current_app.logger.warning(f"[审批回调] 未找到审批记录: sp_no={sp_no}")

    # ==================== P1: 卡片按钮点击 ====================

    def handle_task_card_click(self, data):
        """
        处理模板卡片按钮点击回调
        企微要求 5 秒内调 update_button 防止重复点击
        此方法在异步线程中执行（回调入口已 200 响应）
        """
        user_id = data.get("from_user", "")
        response_code = data.get("response_code", "")
        button_key = data.get("event_key", "")
        task_id = data.get("task_id", "")

        current_app.logger.info(
            f"[卡片回调] user={user_id} button={button_key} response_code={response_code}"
        )

        if not user_id or not response_code:
            return

        client = _get_wecom_client()

        if button_key == "approval_cancel":
            # 取消：更新按钮状态为"已取消"
            client.update_button(user_id, response_code, button_key, "已取消")
            current_app.logger.info(f"[卡片回调] 用户取消审批: {user_id}")
            return

        if button_key == "approval_confirm":
            # 确认提交：更新按钮为"已确认"，异步提交审批
            client.update_button(user_id, response_code, button_key, "已确认提交")
            current_app.logger.info(f"[卡片回调] 用户确认审批，等待提交: {user_id}")

    # ==================== P2: 日程变更 ====================

    def handle_schedule_change(self, data):
        """
        处理日程变更回调
        企微 <ChangeSchedule> 事件: schedule_id, change_type (create/update/cancel)
        """
        schedule_id = data.get("schedule_id", "")
        change_type = data.get("change_type", "update")

        current_app.logger.info(
            f"[日程回调] schedule_id={schedule_id} change_type={change_type}"
        )

        if not schedule_id:
            return

        # 更新本地数据库
        db = _get_db()
        global _ScheduleRecord
        if _ScheduleRecord is None:
            from ..models.schedule_record import ScheduleRecord
            _ScheduleRecord = ScheduleRecord

        record = _ScheduleRecord.query.filter_by(schedule_id=schedule_id).first()
        if record:
            status_map = {"create": "created", "update": "updated", "cancel": "cancelled"}
            record.status = status_map.get(change_type, "updated")
            db.session.commit()
            current_app.logger.info(f"[日程回调] 已更新日程状态: {schedule_id} -> {record.status}")

    # ==================== P3: 客户事件 ====================

    def handle_external_contact_add(self, data):
        """
        处理外部联系人添加回调
        自动打标签 + 发送欢迎语
        """
        user_id = data.get("from_user", "")
        external_userid = data.get("external_userid", "")

        current_app.logger.info(
            f"[客户回调] 新增客户: user={user_id} external={external_userid}"
        )

        if not external_userid:
            return

        client = _get_wecom_client()

        # 自动打标签：新客户
        try:
            from .customer_service import customer_service
            customer_service.mark_tag(user_id, external_userid, ["新客户"])
            current_app.logger.info(f"[客户回调] 已自动打标签: {external_userid}")
        except Exception as e:
            current_app.logger.warning(f"[客户回调] 自动打标签失败: {e}")

        # 发送欢迎语
        welcome_msg = (
            "您好！感谢添加我为好友。\n"
            "我是AI智能助手，可以帮您:\n"
            "· 查询公司政策和知识\n"
            "· 提交审批申请\n"
            "· 查询通讯录\n"
            "· 预约会议\n"
            "如有任何问题，随时问我！"
        )
        try:
            client.send_message(user_id, "text", welcome_msg)
            current_app.logger.info(f"[客户回调] 已发送欢迎语: {external_userid}")
        except Exception as e:
            current_app.logger.warning(f"[客户回调] 发送欢迎语失败: {e}")

    def handle_enter_agent(self, data):
        """
        处理用户进入机器人会话
        发送欢迎卡片
        """
        user_id = data.get("from_user", "")
        current_app.logger.info(f"[会话回调] 用户进入Agent: {user_id}")

        if not user_id:
            return

        client = _get_wecom_client()
        greeting = (
            "你好！我是AI智能助手，我能帮你:\n"
            "· 📝 对话式审批（请假、报销、加班等）\n"
            "· 📚 知识库问答（公司制度、流程规范）\n"
            "· 👤 查组织通讯录\n"
            "· 📅 预约会议和查忙闲\n"
            "· 🏷️ 客户管理和跟进\n\n"
            "直接打字告诉我你需要什么吧！"
        )
        try:
            client.send_message(user_id, "text", greeting)
        except Exception as e:
            current_app.logger.warning(f"[会话回调] 发送问候失败: {e}")

    def _debug_log(self, entry):
        import os, json
        from datetime import datetime as dt
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "dispatch_log.json")
        try:
            entry["time"] = str(dt.now())
            existing = []
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = [existing]
            existing.append(entry)
            if len(existing) > 50:
                existing = existing[-50:]
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def handle_text_message(self, data):
        """处理用户文本消息，百炼Agent优先，Ollama兜底"""
        user_id = data.get("from_user", "")
        content = data.get("content", "")

        current_app.logger.info(f"[文本消息] user={user_id} content={content[:100]}")

        if not user_id or not content:
            self._debug_log({"stage": "text_msg_skip", "reason": "no user_id or content"})
            return

        self._debug_log({"stage": "text_msg_start", "user_id": user_id, "content": content[:100]})

        # 注册用户到通讯录缓存（构建 name→userid 映射）
        try:
            contact_service.register_user(user_id)
        except Exception:
            pass

        # 本地拦截：客户打标签请求（百炼 Tool Calling 不可靠时的兜底）
        tag_reply = self._handle_tag_locally(user_id, content)
        if tag_reply:
            reply = tag_reply
            self._debug_log({"stage": "local_tag_handler", "reply": reply[:200]})
        # 本地拦截：通讯录查询（绕过百炼Agent，避免Agent编造人员信息）
        elif self._is_contact_query(content):
            reply = self._handle_contact_locally(content)
            self._debug_log({"stage": "local_contact_handler", "reply_len": len(reply), "reply": reply[:200]})
        # 本地拦截：知识库问答请求（绕过百炼Agent，直接走RAG，避免Agent编造来源名和答案）
        elif self._is_knowledge_query(content):
            reply = self._handle_knowledge_locally(content)
            self._debug_log({"stage": "local_knowledge_handler", "reply_len": len(reply), "reply": reply[:200]})
        # 本地拦截：审批确认（用户说"正确"等，从缓存获取上下文直接提交，避免百炼编造单号）
        elif _is_confirmation(content) and user_id in _pending_approval_cache:
            reply = self._handle_confirmation_locally(user_id)
            self._debug_log({"stage": "local_confirmation_handler", "reply_len": len(reply), "reply": reply[:200]})
        # 本地拦截：审批单号查询（绕过百炼Agent，直接查DB，避免Agent编造状态）
        elif self._is_approval_sp_query(content):
            reply = self._handle_approval_query_locally(content)
            self._debug_log({"stage": "local_approval_query_handler", "reply_len": len(reply), "reply": reply[:200]})
        # 本地拦截：空审批请求（没有字段值的请假/加班等，强制走信息收集流程，避免百炼跳过确认直接提交）
        elif self._is_empty_approval_request(content):
            reply = self._handle_approval_init_locally(user_id, content)
            self._debug_log({"stage": "local_approval_init_handler", "reply_len": len(reply), "reply": reply[:200]})
        # 本地拦截：审批字段值响应（用户回复了审批信息，本地解析并确认，避免百炼跳过确认直接提交）
        elif self._is_approval_field_response(user_id, content):
            reply = self._handle_approval_field_values(user_id, content)
            self._debug_log({"stage": "local_approval_field_handler", "reply_len": len(reply), "reply": reply[:200]})
        else:
            # 所有消息统一走百炼 Agent（百炼负责 Tool Calling）
            reply = self._chat_with_bailian(user_id, content)
            if reply is None:
                current_app.logger.info("[文本消息] 百炼不可用，降级到 Ollama")
                reply = self._chat_with_ollama(content)
                self._debug_log({"stage": "ollama_fallback", "reply_len": len(reply), "reply": reply[:200]})
            else:
                self._debug_log({"stage": "bailian_done", "reply_len": len(reply), "reply": reply[:200]})

        reply = self._sanitize_reply(reply)

        client = _get_wecom_client()
        try:
            result = client.send_message(user_id, "text", reply)
            self._debug_log({"stage": "send_ok", "result": str(result)[:200]})
            current_app.logger.info(f"[文本消息] 已回复 user={user_id}")
        except Exception as e:
            self._debug_log({"stage": "send_fail", "error": str(e)})

    def _sanitize_reply(self, text):
        """清理回复中的 Markdown 语法、LLM幻觉和无用追问"""
        import re
        # 移除 ![alt](url) 图片语法
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # 移除 http://image_url_placeholder 等占位链接
        text = re.sub(r'http://image_url_placeholder\S*', '', text)
        # 移除 Markdown 标题标记（### ## #），保留文字
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # 移除 **加粗** 标记（支持跨多行），保留文字
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        # 移除无序列表标记
        text = re.sub(r'^[\-\*]\s+', '  ', text, flags=re.MULTILINE)
        # 保留有序列表标记（知识库回答和汇报链需要 "1. 2. 3." 格式）
        # 移除行内代码标记
        text = re.sub(r'`(.+?)`', r'\1', text)
        # 移除斜体标记
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
        # 截掉"请提供user_id"相关的追问段落
        text = re.sub(r'\n*请提供您的企业微信用户ID.*?(?=\n|$)', '', text)
        text = re.sub(r'\n*如果您不确定如何查找用户ID.*?(?=\n|$)', '', text)
        text = re.sub(r'\n*我可以帮助您找到对应的用户ID.*?(?=\n|$)', '', text)
        # 移除 LLM 幻觉生成的"引用图片"道歉及其变体
        text = re.sub(r'\n*\s*看起来我错误地尝试引用了一张图片[，,。.]?\s*.*?(?=\n|$)', '', text)
        text = re.sub(r'\n*\s*实际上这里并没有相关的图片信息[，,。.]?\s*.*?(?=\n|$)', '', text)
        text = re.sub(r'\n*\s*请直接参考上述内容[，,。.]?\s*.*?(?=\n|$)', '', text)
        text = re.sub(r'\n*\s*我错误地引用了.*?(?=\n|$)', '', text)
        text = re.sub(r'\n*\s*引用.*?图片.*?(?=\n|$)', '', text)
        # 移除 LLM 幻觉生成的无用结尾语
        text = re.sub(r'\n*\s*如果有(?:更多|其他|任何)问题[，,]?(?:请|可以|随时).*?(?=\n|$)', '', text)
        text = re.sub(r'\n*\s*需要.{0,10}(?:帮助|协助|支持).*?(?=\n|$)', '', text)
        # 清理残留的"另外，"等截断碎片
        text = re.sub(r'\n*另外，\s*', '', text)
        text = re.sub(r'\n*\s*此外[，,]\s*.*?(?=\n|$)', '', text)
        # 清理末尾空白行和多余的连续换行
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.rstrip()
        return text.strip()

    def _handle_tag_locally(self, user_id, content):
        """本地拦截打标签请求，直接调用 customer_service，绕过百炼"""
        import re
        # 匹配: 给/为XX打标签YY 或 给/为XX打上标签YY
        m = re.search(r'[给为]([^\s打]+)\s*打\s*(?:上\s*)?标签\s*["\']?(.+?)["\']?\s*$', content)
        if not m:
            return None
        customer_name = m.group(1).strip()
        tag_name = m.group(2).strip().rstrip("。.!！")
        if not customer_name or not tag_name:
            return None

        current_app.logger.info(f"[本地打标签] customer={customer_name} tag={tag_name} user_id={user_id}")
        from .customer_service import customer_service

        # Step 1: 搜索客户
        results = customer_service.search_external_contact(user_id, customer_name)
        current_app.logger.info(f"[本地打标签] search results: {results}")
        if not results:
            # fallback: 尝试用英文名搜索
            if user_id:
                from ..clients.wecom_client import wecom_client
                raw = wecom_client.list_external_contacts(user_id)
                current_app.logger.info(f"[本地打标签] raw list_external_contacts: errcode={raw.get('errcode')} count={len(raw.get('external_userid',[]))}")
                # 尝试模糊匹配
                for eid in raw.get("external_userid", []):
                    detail = wecom_client.get_external_contact(eid)
                    if detail.get("errcode") == 0:
                        n = detail.get("external_contact", {}).get("name", "")
                        if customer_name in n or n in customer_name:
                            results = [{"external_userid": eid, "name": n}]
                            break
            if not results:
                return f"没有找到名为{customer_name}的客户信息。请确认名字是否正确，或通过企业微信客户端手动操作。"
        # 取第一个结果

        # Step 2: 打标签
        external_userid = results[0]["external_userid"]
        resp = customer_service.mark_tag(user_id, external_userid, [tag_name])
        if resp.get("errcode") == 0:
            demo = "（演示模式）" if resp.get("demo_mode") else ""
            return f"已成功为客户{customer_name}添加\"{tag_name}\"标签。{demo}"
        return f"打标签失败：{resp.get('errmsg', '未知错误')}，请通过企业微信客户端手动操作。"

    def _is_knowledge_query(self, content):
        """检测是否为知识库问答请求（应绕过百炼直接走RAG）"""
        import re
        # 排除审批/操作请求（包含数量、具体动作）
        exclude_patterns = [
            r'我要(?:请假|申请|报销|加班|出差)',
            r'帮我(?:请假|申请|提交|预约|安排|查|搜索|找)',
            r'\d+[天元个次小时]',
            r'(?:提交|查询).*审批',
            r'^查(?:一下|询)?\s*(?:单号|审批)',
            r'^给\s*\S+\s*打',
        ]
        for pat in exclude_patterns:
            if re.search(pat, content):
                return False
        # 知识库关键词
        kw_patterns = [
            r'(?:公司|企业|我们|员工).*(?:政策|制度|规定|流程|规范|标准|手册|指南|策略|办法)',
            r'(?:政策|制度|规定|流程|规范|标准|手册|指南|策略|办法).*(?:是什么|怎么|如何|怎样)',
            r'(?:年假|事假|病假|婚假|产假|调休|考勤|考核|绩效|入职|离职|转正|晋升|差旅|报销|加班|采购|备份|安全|培训|薪酬|福利|合同|组织架构|部门职责|信息安全).*(?:政策|制度|规定|流程|标准|办法|规范|策略|管理|手册)',
            r'(?:怎么|如何|怎样).*(?:请假|报销|加班|出差|申请|操作|办理|处理|进行|备份)',
            r'.*(?:政策|制度|规定|流程|手册|规范|策略).*(?:查询|查看|了解|介绍|说明)',
            r'什么是.*',
            r'.*是什么',
            r'.*与什么有关', r'.*和什么相关', r'.*跟什么有关',
            r'.*包括什么', r'.*包含什么', r'.*包括哪些',
            r'.*怎么(?:走|办|做|操作|处理|申请)',
            r'.*如何(?:申请|操作|处理|办理|进行|备份)',
            r'.*规定$', r'.*制度$', r'.*政策$', r'.*流程$', r'.*规范$',
            r'.*策略$', r'.*办法$', r'.*手册$', r'.*指南$',
            r'(?:员工|公司).*手册',
            r'关于.*(?:规定|制度|政策|流程|规范|策略|办法|手册)',
        ]
        for pat in kw_patterns:
            if re.search(pat, content):
                return True
        return False

    def _handle_knowledge_locally(self, content):
        """本地处理知识库问答，直接走RAG+Ollama，绕过百炼Agent"""
        import re
        from ..services.rag_service import RAGService
        try:
            rag = RAGService(current_app.config)
            result = rag.ask(content)
            answer = result.get("answer", "")
            sources = result.get("sources", [])
            # 清理：去除LLM可能输出的方括号包裹的来源名
            answer = re.sub(r'来源[：:]\s*\[(.+?)\]', r'来源：\1', answer)
            answer = re.sub(r'\[来源[：:]\s*(.+?)\]', r'来源：\1', answer)
            # 清理"以下是XXX"占位符残留
            answer = re.sub(r'以下是\s*XXX\s*[：:]', '以下是相关要点：', answer)
            # 判断是否为"未找到内容"的回复
            no_content_markers = ['暂时无法回答', '没有找到与您问题相关的信息', '没有找到相关']
            is_no_content = any(m in answer for m in no_content_markers)
            if sources and not is_no_content:
                real_names = list(dict.fromkeys(s["file_name"] for s in sources if s.get("file_name")))
                if real_names:
                    has_real_source = any(name in answer for name in real_names)
                    if not has_real_source:
                        # 去除LLM可能编造的来源行，追加真实来源
                        answer = re.sub(r'\n*引用来源[：:].*$', '', answer)
                        answer = re.sub(r'\n*来源[：:].*$', '', answer)
                        answer = answer.rstrip() + "\n来源：" + "、".join(real_names)
            return answer
        except Exception as e:
            current_app.logger.error(f"[本地知识库] 查询异常: {e}", exc_info=True)
            return "抱歉，知识库查询失败，请稍后再试。"

    def _is_contact_query(self, content):
        """检测是否为通讯录查询请求（应绕过百炼直接走本地）"""
        import re
        patterns = [
            r'查.{0,5}(?:汇报|上级|领导)',
            r'(?:帮我|帮我|请|麻烦)?查一?下.{0,10}(?:汇报线|汇报链|上级)',
            r'搜索手机号\d+',
            r'手机号\d+',
            r'查.{0,5}(?:人力|后勤|技术|财务|行政|市场|销售|研发|运营|产品|设计|测试)',
            r'(?:人力|后勤|技术|财务|行政|市场|销售|研发|运营|产品|设计|测试)部',
            r'查一?下.+(?:部门|人员|成员|同事)',
            r'帮我查一?下\s*\S+\s*$',
            r'查一?下\s*\S+\s*$',
            r'.{0,5}(?:人员|成员|同事|部门).{0,5}(?:有谁|有哪些|多少人|谁在)',
        ]
        # 排除审批/日程/客户/会议相关（含时间/客户关键词应走百炼Agent解析）
        exclude = [
            r'(?:请假|加班|报销|出差|采购|用章|调休).*申请',
            r'(?:审批|单号|SP\d|DEMO-)',
            r'\d+[天元个次小时]',
            r'(?:今天|明天|后天|上午|下午|中午|晚上|凌晨)',
            r'(?:忙不忙|有空|空闲|是否有空|是否空闲|忙闲|日程|会议|预约)',
            r'\d+[点:：]\d*',
            r'(?:跟进|标签|群发|客户|打标签|跟进记录)',
        ]
        for pat in exclude:
            if re.search(pat, content):
                return False
        for pat in patterns:
            if re.search(pat, content):
                return True
        return False

    def _handle_contact_locally(self, content):
        """本地处理通讯录查询，直接调用contact_service + Ollama格式化，绕过百炼Agent"""
        import re
        from ..services.contact_service import contact_service

        try:
            result_data = None
            query_type = "search"
            dept_keywords = ["人力", "后勤", "技术", "财务", "行政", "市场", "销售", "研发", "运营", "产品", "设计", "测试"]

            # 1. 检测手机号搜索
            phone_match = re.search(r'1[3-9]\d{9}', content)
            if phone_match:
                phone = phone_match.group(0)
                result_data = contact_service.search_user(phone)
                query_type = "phone_search"
            # 2. 检测汇报链查询
            elif re.search(r'(?:汇报线|汇报链|上级|领导)', content):
                name_match = re.search(r'(?:查一?下|帮我查一?下)?\s*(\S+?)(?:的汇报|汇报|上级|领导)', content)
                name = name_match.group(1) if name_match else content.strip()
                name = re.sub(r'^(?:查一?下|帮我查一?下|请|麻烦)\s*', '', name)
                result_data = contact_service.get_report_chain(name)
                query_type = "report_chain"
            # 3. 检测部门查询
            elif any(kw in content for kw in dept_keywords):
                # 找出所有提到的部门
                from ..clients.wecom_client import wecom_client
                all_depts = wecom_client.list_department(0)
                dept_list = all_depts.get("department", [])
                # 只查询用户消息中实际提到的部门，而非全部存在关键词的部门
                mentioned_depts = [d for d in dept_list if any(kw in d.get("name", "") and kw in content for kw in dept_keywords)]
                if mentioned_depts:
                    parts = []
                    for dept in mentioned_depts:
                        members = contact_service.get_department_members(dept["id"])
                        parts.append({"dept_name": dept["name"], "members": members.get("members", [])})
                    result_data = {"departments": parts}
                    query_type = "department"
            # 4. 默认为成员搜索
            if result_data is None:
                search_name = content.strip()
                search_name = re.sub(r'^(?:帮我|请|麻烦)?查一?下\s*', '', search_name)
                search_name = re.sub(r'^(?:搜索|查找|寻找)\s*', '', search_name)
                search_name = re.sub(r'\s*(?:的信息|是谁|是哪个?|在哪).*$', '', search_name)
                if search_name:
                    result_data = contact_service.search_user(search_name)
                    query_type = "search"

            if result_data is None:
                return "抱歉，未找到相关信息。"

            # 用 Ollama 格式化为符合规范的回复
            reply = self._format_contact_result(query_type, result_data, content)
            return reply
        except Exception as e:
            current_app.logger.error(f"[本地通讯录] 查询异常: {e}", exc_info=True)
            return "抱歉，通讯录查询失败，请稍后再试。"

    def _format_contact_result(self, query_type, result_data, original_query):
        """格式化通讯录查询结果为规范文本"""
        import re
        # 构建 Ollama prompt
        if query_type == "phone_search":
            results = result_data.get("results", [])
            if not results:
                return "未找到该手机号对应的成员。"
            user = results[0]
            phone = ""
            m = re.search(r'1[3-9]\d{9}', original_query)
            if m:
                phone = m.group(0)
            return f"""手机号{phone}对应的是{user['department']}的{user['name']}同事。以下是TA的详细信息：
姓名：{user['name']}
部门：{user['department']}
状态：{user['status']}
用户ID：{user['userid']}"""

        elif query_type == "report_chain":
            chain = result_data.get("chain", [])
            if not chain:
                name = result_data.get("user_id", "该成员")
                return f"未找到{name}的汇报链信息。"
            lines = [f"{chain[0]['name']}的汇报链如下："]
            for i, user in enumerate(chain):
                suffix = ""
                if i == 1 and len(chain) >= 2:
                    suffix = f"（{chain[0]['name']}的直接上级）"
                lines.append(f"{i+1}. {user['name']}{suffix}")
                lines.append(f"   部门：{user['department']}")
                lines.append(f"   状态：{user['status']}")
                lines.append(f"   用户ID：{user['userid']}")
            return "\n".join(lines)

        elif query_type == "department":
            depts = result_data.get("departments", [])
            if not depts:
                return "未找到相关部门信息。"
            parts = []
            for dept in depts:
                if not dept["members"]:
                    parts.append(f"{dept['dept_name']}部门：无成员。")
                else:
                    parts.append(f"{dept['dept_name']}部门")
                    for m in dept["members"]:
                        parts.append(f"- {m['name']}")
                        parts.append(f"  部门：{m['department']}")
                        parts.append(f"  状态：{m['status']}")
                        parts.append(f"  用户ID：{m['userid']}")
            return "\n".join(parts)

        else:  # search
            results = result_data.get("results", [])
            if not results:
                return f"未找到与{original_query.strip()}相关的成员信息。"
            user = results[0]
            return f"""姓名：{user['name']}
部门：{user['department']}
状态：{user['status']}
用户ID：{user['userid']}"""

    def _chat_with_bailian(self, user_id, user_message):
        """调用百炼 Agent 进行智能对话，失败返回 None"""
        app_id = current_app.config.get("BAILIAN_APP_ID", "")
        api_key = current_app.config.get("DASHSCOPE_API_KEY", "")
        if not app_id or not api_key:
            return None
        try:
            # 在消息前附加当前用户身份，让 Agent 知道 user_id
            clean_msg = user_message.strip().rstrip("。，,!.！?？ ")
            if clean_msg in CONFIRM_KEYWORDS:
                # 用户确认审批信息，强制注入最高优先级指令
                prompt = (
                    f"[最高优先级系统指令] 用户刚刚确认了审批信息（回复\"{user_message}\"），"
                    f"你必须立即调用 /approval/submit 工具提交审批。"
                    f"禁止编造审批单号，禁止生成回复文字。如果你不调用工具，审批数据将丢失。"
                    f"[当前用户 user_id=\"{user_id}\"] {user_message}"
                )
            else:
                prompt = f"[当前用户 user_id=\"{user_id}\"] {user_message}"
            client = _get_bailian_client()
            result = client.chat(user_id, prompt)
            if result.get("success"):
                reply_text = result["text"]
                # 解析百炼返回的确认消息，缓存审批上下文供本地提交使用
                _parse_confirmation_reply(reply_text, user_id)
                return reply_text
            current_app.logger.error(f"[Bailian] 调用失败: {result.get('error')}")
            return None
        except Exception as e:
            current_app.logger.error(f"[Bailian] 调用异常: {e}", exc_info=True)
            return None

    def _handle_confirmation_locally(self, user_id):
        """本地处理审批确认，从缓存获取上下文并直接调用提交，避免百炼编造单号"""
        ctx = _pending_approval_cache.pop(user_id, None)
        if not ctx:
            return "审批上下文已过期，请重新提交申请。"

        template_name = ctx["template_name"]
        fields = ctx["fields"]
        name = ctx.get("name", user_id)

        try:
            # 解析用户名为 userid
            from ..routes.tools.approval_tool import _resolve_user_id
            resolved_user_id = _resolve_user_id(name)
            if not resolved_user_id:
                return f"未找到成员 {name}，请确认姓名后重试。"
        except Exception:
            resolved_user_id = name

        # 直接调用审批提交逻辑
        from datetime import datetime as dt
        import json
        from ..extensions import db
        from ..models.approval_record import ApprovalRecord
        approval_service = _get_approval_service()

        now_str = dt.now().strftime("%Y%m%d%H%M%S")
        fallback_sp_no = f"DEMO-{now_str}-{resolved_user_id}"

        try:
            resp = approval_service.submit(resolved_user_id, template_name, fields)
        except Exception as e:
            current_app.logger.error(f"[本地提交] submit异常: {e}", exc_info=True)
            resp = {"errcode": 0, "sp_no": fallback_sp_no, "demo_mode": True, "fallback_reason": str(e)}

        if resp.get("errcode", -1) != 0:
            sp_no = fallback_sp_no
        else:
            sp_no = resp.get("sp_no", fallback_sp_no)

        # 写入数据库
        try:
            record = ApprovalRecord(
                user_id=resolved_user_id,
                sp_no=sp_no,
                template_name=template_name,
                status="pending",
                fields_json=fields,
            )
            db.session.add(record)
            db.session.commit()
            current_app.logger.info(f"[本地提交] 记录已写入 id={record.id} sp_no={sp_no}")
        except Exception as e:
            current_app.logger.error(f"[本地提交] 数据库写入失败: {e}", exc_info=True)

        return f"审批已提交，单号：{sp_no}，状态：待审批。"

    def _is_approval_sp_query(self, content):
        """检测是否为审批单号查询请求（应绕过百炼直接查DB）"""
        import re
        patterns = [
            r'(?:查|查询|查看).{0,5}(?:单号|审批).{0,10}(?:审批|进程|状态|进度)',
            r'(?:单号|审批).{0,5}(?:进程|状态|进度|查询)',
        ]
        for pat in patterns:
            if re.search(pat, content):
                return True
        return False

    def _handle_approval_query_locally(self, content):
        """本地处理审批单号查询，直接查DB，绕过百炼Agent"""
        import re
        from ..models.approval_record import ApprovalRecord

        sp_match = re.search(r'(?:DEMO-|SP)[a-zA-Z0-9_\-]+', content)
        if not sp_match:
            return "未识别审批单号，请提供完整的单号（如 DEMO-20260622092831-XuQi）。"

        sp_no = sp_match.group(0)
        try:
            record = ApprovalRecord.query.filter_by(sp_no=sp_no).first()
            if record:
                status_map = {"pending": "审批中", "approved": "已通过", "rejected": "已驳回", "cancelled": "已撤销"}
                status_text = status_map.get(record.status, record.status)
                return f"审批单号：{sp_no}\n状态：{status_text}"
            return f"未找到单号 {sp_no} 的审批记录，请确认单号是否正确。"
        except Exception as e:
            current_app.logger.error(f"[本地审批查询] 查询异常: {e}", exc_info=True)
            return "抱歉，审批查询失败，请稍后再试。"

    def _is_empty_approval_request(self, content):
        """检测是否为无字段值的审批请求（如 帮我提交一个加班申请），应拦截避免百炼跳过信息收集直接提交"""
        import re
        # 必须包含审批关键词
        approval_kw = ["请假", "加班", "报销", "出差", "采购", "用章"]
        if not any(kw in content for kw in approval_kw):
            return False
        # 排除审批单号查询
        if self._is_approval_sp_query(content):
            return False
        # 排除确认消息
        if content.strip().rstrip("。，,!.！?？ ") in CONFIRM_KEYWORDS:
            return False
        # 排除已有日期值的消息 (2026-6-22, 6月22日, 6.22 等)
        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', content):
            return False
        if re.search(r'\d+月\d+日', content):
            return False
        # 排除已有数量+单位的消息 (3天, 5小时, 5000元 等)
        if re.search(r'\d+\s*[天元个次小时日周月]', content):
            return False
        # 排除已有具体审批类型值的消息 (年假, 事假, 病假 等)
        type_values = ["年假", "事假", "病假", "婚假", "产假", "调休", "差旅费", "办公费", "招待费", "交通费", "公章", "合同章", "财务章", "法人章"]
        if any(tv in content for tv in type_values):
            return False
        return True

    def _handle_approval_init_locally(self, user_id, content):
        """本地处理空审批请求，提示用户提供必填字段，避免百炼跳过信息收集直接提交"""
        import re
        # 识别模板类型
        template_fields = {
            "请假": "请假类型（年假/事假/病假/调休/婚假/产假）、开始日期、结束日期、请假天数、请假原因",
            "加班": "加班日期、加班时长（小时）、加班原因",
            "报销": "报销类型（差旅费/办公费/招待费/交通费）、报销金额、报销说明",
            "出差": "出发日期、返回日期、目的地、出差事由",
            "采购": "采购物品、采购金额、采购原因",
            "用章": "用章类型（公章/合同章/财务章/法人章）、用章事由",
        }
        detected = None
        for kw in ["请假", "加班", "报销", "出差", "采购", "用章"]:
            if kw in content:
                detected = kw
                break
        if not detected:
            return "请说明你需要办理的审批类型（请假/加班/报销/出差/采购/用章），并提供相关信息。"
        # 记录待处理的模板，用于后续字段解析
        _pending_approval_template[user_id] = detected
        fields_prompt = template_fields.get(detected, "")
        return f"请提供以下{detected}信息：{fields_prompt}。请直接回复，例如：{self._example_for_template(detected)}"

    def _example_for_template(self, template_name):
        """返回模板的示例输入"""
        examples = {
            "请假": "年假 2026-6-22 2026-6-24 3天 回家",
            "加班": "2026-6-22 3 加急文件",
            "报销": "差旅费 5000 出差交通住宿",
            "出差": "2026-6-22 2026-6-25 北京 客户拜访",
            "采购": "办公用品 2000 打印纸墨盒",
            "用章": "公章 合同签署",
        }
        return examples.get(template_name, "")

    def _is_approval_field_response(self, user_id, content):
        """检测用户是否在回复审批字段值（之前被问了审批信息，现在提供了具体值）"""
        import re
        # 必须有待处理的审批模板
        if user_id not in _pending_approval_template:
            return False
        # 排除确认消息和空审批请求
        clean = content.strip().rstrip("。，,!.！?？ ")
        if clean in CONFIRM_KEYWORDS:
            return False
        if self._is_empty_approval_request(content):
            return False
        if self._is_approval_sp_query(content):
            return False
        # 必须包含日期或具体值（不是闲聊）
        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', content):
            return True
        if re.search(r'\d+\s*[天元个次小时日周月]', content):
            return True
        # 包含审批类型具体值
        type_values = ["年假", "事假", "病假", "婚假", "产假", "调休", "差旅费", "办公费", "招待费", "交通费", "公章", "合同章", "财务章", "法人章"]
        if any(tv in content for tv in type_values):
            return True
        return False

    def _handle_approval_field_values(self, user_id, content):
        """本地解析审批字段值，缓存并确认，避免百炼跳过确认直接提交"""
        import re
        template_name = _pending_approval_template.pop(user_id, None)
        if not template_name:
            return "请先说明你需要办理的审批类型。"

        # 模板字段定义（name, type）
        template_field_defs = {
            "请假": [("请假类型", "select"), ("开始日期", "date"), ("结束日期", "date"), ("请假天数", "number"), ("请假原因", "text")],
            "加班": [("加班日期", "date"), ("加班时长", "number"), ("加班原因", "text")],
            "报销": [("报销类型", "select"), ("报销金额", "number"), ("报销说明", "text")],
            "出差": [("出发日期", "date"), ("返回日期", "date"), ("目的地", "text"), ("出差事由", "text")],
            "采购": [("采购物品", "text"), ("采购金额", "number"), ("采购原因", "text")],
            "用章": [("用章类型", "select"), ("用章事由", "text")],
        }
        field_defs = template_field_defs.get(template_name, [])

        # 从内容中提取值
        dates = re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', content)
        # 先移除日期再提取数字，避免年份被当数字
        cleaned_for_num = re.sub(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', '', content)
        numbers = re.findall(r'(\d+)\s*(?:天|元|个|次|小时|日|周|月)?', cleaned_for_num)
        numbers = [int(n) for n in numbers if n.isdigit() and int(n) > 0]
        # 审批类型选择值
        select_options = {
            "请假类型": ["年假", "事假", "病假", "婚假", "产假", "调休"],
            "报销类型": ["差旅费", "办公费", "招待费", "交通费"],
            "用章类型": ["公章", "合同章", "财务章", "法人章"],
        }

        fields = {}
        date_idx = 0
        num_idx = 0

        for fname, ftype in field_defs:
            if ftype == "select":
                options = select_options.get(fname, [])
                for opt in options:
                    if opt in content:
                        fields[fname] = opt
                        content = content.replace(opt, "", 1)
                        break
            elif ftype == "date":
                if date_idx < len(dates):
                    fields[fname] = dates[date_idx]
                    date_idx += 1
            elif ftype == "number":
                if num_idx < len(numbers):
                    fields[fname] = numbers[num_idx]
                    num_idx += 1

        # 处理剩余文本 → text 类型字段
        remaining = re.sub(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', '', content)
        remaining = re.sub(r'\d+\s*(?:天|元|个|次|小时|日|周|月)?', '', remaining)
        remaining = remaining.strip().strip("，,。.!！?？ ")
        text_fields = [f[0] for f in field_defs if f[1] == "text"]
        if remaining and text_fields:
            # 最后一个 text 字段获取剩余内容
            for tf in text_fields:
                if tf not in fields:
                    fields[tf] = remaining
                    break

        if not fields:
            return f"未能从您的输入解析出{template_name}信息，请按格式重新输入。例如：{self._example_for_template(template_name)}"

        # 缓存审批上下文 + 确认
        ctx = {"template_name": template_name, "fields": fields, "name": user_id}
        _pending_approval_cache[user_id] = ctx
        field_summary = "，".join([f"{k}：{v}" for k, v in fields.items()])
        return f"请确认：{field_summary}。正确吗？"

    def _chat_with_ollama(self, user_message):
        """调用本地 Ollama qwen3:8b 进行对话"""
        import requests

        ollama_url = current_app.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = current_app.config.get("LLM_MODEL_NAME", "qwen3:8b")

        system_prompt = """你是企业AI助手，可以帮用户完成以下任务：
1. 审批：请假、加班、报销、出差、采购、用章
2. 通讯录：搜索成员、查部门、查汇报关系
3. 日程：查忙闲、预约会议
4. 客户：打标签、群发消息、查跟进记录
5. 知识库：企业制度、流程规范问答

回复要求：纯文本，禁止使用任何Markdown格式符号（如**加粗**、#标题、-列表、*斜体*、`代码块`等）。用换行和空格排版。简洁直接。"""

        try:
            resp = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 1024},
                },
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()["message"]["content"]
            return f"AI服务暂时不可用（{resp.status_code}），请稍后再试。"
        except Exception as e:
            current_app.logger.error(f"[Ollama] 调用失败: {e}")
            return "抱歉，AI服务当前不可用，请稍后再试。"


event_service = EventService()
