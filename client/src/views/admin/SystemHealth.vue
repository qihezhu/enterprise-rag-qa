<template>
  <div class="system-health">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统健康状态</span>
          <el-button @click="refresh" :loading="loading" size="small">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col v-for="item in services" :key="item.name" :span="8">
          <el-card shadow="hover" class="health-card">
            <div class="health-item">
              <div class="health-icon">
                <el-tag
                  :type="item.status === 'ok' ? 'success' : item.status === 'warning' ? 'warning' : 'danger'"
                  effect="dark"
                  size="large"
                >
                  {{ item.icon }}
                </el-tag>
              </div>
              <div class="health-info">
                <div class="health-name">{{ item.label }}</div>
                <div class="health-message">{{ item.message }}</div>
                <el-tag :type="statusTagType(item.status)" size="small">
                  {{ statusLabel(item.status) }}
                </el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-divider />

      <el-descriptions title="服务详情" :column="2" border>
        <el-descriptions-item v-for="item in services" :key="item.name" :label="item.label">
          {{ item.message }}
          <el-tag :type="statusTagType(item.status)" size="small">
            {{ statusLabel(item.status) }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";

const loading = ref(false);
const services = ref([
  { name: "mysql", label: "MySQL", icon: "DB", status: "unknown", message: "检测中..." },
  { name: "redis", label: "Redis", icon: "RD", status: "unknown", message: "检测中..." },
  { name: "chroma", label: "Chroma", icon: "CV", status: "unknown", message: "检测中..." },
  { name: "wecom_token", label: "企微Token", icon: "WC", status: "unknown", message: "检测中..." },
  { name: "ollama", label: "Ollama", icon: "OL", status: "unknown", message: "检测中..." },
]);

function statusTagType(s) {
  return s === "ok" ? "success" : s === "warning" ? "warning" : "danger";
}
function statusLabel(s) {
  return s === "ok" ? "正常" : s === "warning" ? "警告" : s === "error" ? "异常" : "未知";
}

async function refresh() {
  loading.value = true;
  try {
    const res = await axios.get("/api/health/");
    const checks = res.data.data?.checks || res.data.checks || {};
    for (const svc of services.value) {
      const check = checks[svc.name];
      if (check) {
        svc.status = check.status;
        svc.message = check.message || "";
      }
    }
  } catch {
    ElMessage.error("健康检查失败");
  } finally {
    loading.value = false;
  }
}

onMounted(refresh);
</script>

<style scoped>
.system-health { padding: 20px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.health-card { margin-bottom: 20px; }
.health-item { display: flex; align-items: center; gap: 16px; }
.health-icon { flex-shrink: 0; }
.health-name { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.health-message { font-size: 13px; color: #909399; margin-bottom: 6px; }
</style>
