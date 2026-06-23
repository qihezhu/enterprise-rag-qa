<template>
  <div class="wecom-config">
    <el-card>
      <template #header>
        <span>企业微信配置状态</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="CorpID">
          {{ config.corp_id || '未配置' }}
          <el-tag v-if="config.corp_id" type="success" size="small">已配置</el-tag>
          <el-tag v-else type="danger" size="small">未配置</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="AgentID">
          {{ config.agent_id || '未配置' }}
        </el-descriptions-item>
        <el-descriptions-item label="Secret">
          {{ config.secret_configured ? '*** 已配置 ***' : '未配置' }}
          <el-tag v-if="config.secret_configured" type="success" size="small">已配置</el-tag>
          <el-tag v-else type="danger" size="small">未配置</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="回调 URL">
          {{ config.callback_url || '未配置' }}
        </el-descriptions-item>
        <el-descriptions-item label="Token 状态">
          <el-tag :type="config.token_valid ? 'success' : 'warning'">
            {{ config.token_valid ? '有效' : '待验证' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Redis 状态">
          <el-tag :type="config.redis_ok ? 'success' : 'danger'">
            {{ config.redis_ok ? '连接正常' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <div class="actions">
        <el-button type="primary" @click="testToken" :loading="testing">
          <el-icon><Connection /></el-icon> 测试 Token 获取
        </el-button>
      </div>

      <el-divider />

      <el-alert
        title="配置说明"
        type="info"
        :closable="false"
        description="请确保已在企微管理后台创建自建应用，并在千问Agent平台完成机器人绑定。环境变量需设置 WECOM_CORP_ID、WECOM_SECRET、WECOM_TOKEN、WECOM_ENCODING_AES_KEY。"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { getWeComStatusApi, testTokenApi } from "../../api/wecom";
import { ElMessage } from "element-plus";

const config = ref({
  corp_id: "",
  agent_id: "",
  secret_configured: false,
  callback_url: "",
  token_valid: false,
  redis_ok: false,
});

const testing = ref(false);

onMounted(async () => {
  try {
    const res = await getWeComStatusApi();
    config.value = res.data || res;
  } catch {
    // 使用默认值
  }
});

async function testToken() {
  testing.value = true;
  try {
    const res = await testTokenApi();
    if (res.code === 0 || res.ok) {
      ElMessage.success("Token 获取成功");
      config.value.token_valid = true;
    } else {
      ElMessage.error(res.message || "Token 获取失败");
    }
  } catch (e) {
    ElMessage.error("连接失败: " + (e.message || "未知错误"));
  } finally {
    testing.value = false;
  }
}
</script>

<style scoped>
.wecom-config {
  padding: 20px;
}
.actions {
  margin-top: 20px;
}
</style>
