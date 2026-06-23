<template>
  <div class="contact-usage">
    <el-card>
      <template #header><span>组织大脑使用说明</span></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Tool 端点">
          <el-tag>POST /api/tools/contact/search</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="认证方式">
          <el-tag type="warning">X-Tool-API-Key</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="功能">
          支持按姓名、手机号查人（自动脱敏）
        </el-descriptions-item>
        <el-descriptions-item label="部门查询">
          <el-tag>POST /api/tools/contact/department</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="汇报链查询">
          <el-tag>POST /api/tools/contact/report-chain</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="千问平台">
          注册为 search_user / get_dept_members / get_report_chain 三个 Tool
        </el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <el-alert
        title="安全提示"
        type="warning"
        :closable="false"
        description="所有联系人查询结果中的手机号已自动脱敏（138****1234）。日志中间件已配置敏感信息过滤，确保手机号、身份证、Token 不落盘明文。"
      />

      <el-divider />

      <el-alert
        title="千问平台注册参数"
        type="info"
        :closable="false"
      >
        <template #default>
          <p><strong>search_user Tool:</strong></p>
          <pre style="background:#f5f5f5;padding:10px;border-radius:4px">
{
  "name": "search_user",
  "description": "搜索企业通讯录成员，支持姓名、手机号查询",
  "method": "POST",
  "url": "{{BASE_URL}}/api/tools/contact/search",
  "headers": {"X-Tool-API-Key": "{{QWEN_TOOL_API_KEY}}"},
  "input_schema": {
    "query": {"type": "string", "description": "姓名或手机号"}
  }
}
          </pre>
          <p><strong>get_dept_members Tool:</strong></p>
          <pre style="background:#f5f5f5;padding:10px;border-radius:4px">
{
  "name": "get_dept_members",
  "description": "获取部门成员列表，支持递归查询子部门",
  "method": "POST",
  "url": "{{BASE_URL}}/api/tools/contact/department",
  "headers": {"X-Tool-API-Key": "{{QWEN_TOOL_API_KEY}}"},
  "input_schema": {
    "dept_id": {"type": "integer", "description": "部门ID"},
    "recursive": {"type": "boolean", "description": "是否递归查询子部门"}
  }
}
          </pre>
        </template>
      </el-alert>
    </el-card>
  </div>
</template>

<style scoped>
.contact-usage { padding: 20px; }
</style>
