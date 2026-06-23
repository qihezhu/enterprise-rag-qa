<template>
  <div class="metrics-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Agent Tool 调用指标</span>
          <el-button @click="refresh" :loading="loading" size="small">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col v-for="metric in metricsList" :key="metric.tool" :span="12">
          <el-card shadow="hover" class="metric-card">
            <template #header>
              <span class="metric-title">Tool: {{ metric.tool }}</span>
            </template>
            <el-row :gutter="12">
              <el-col :span="6">
                <div class="stat">
                  <div class="stat-value">{{ metric.calls }}</div>
                  <div class="stat-label">总调用</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat">
                  <div class="stat-value success">{{ metric.success_rate }}%</div>
                  <div class="stat-label">成功率</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat">
                  <div class="stat-value">{{ metric.p50_ms }}ms</div>
                  <div class="stat-label">P50 延迟</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat">
                  <div class="stat-value">{{ metric.p95_ms }}ms</div>
                  <div class="stat-label">P95 延迟</div>
                </div>
              </el-col>
            </el-row>
            <el-divider style="margin: 12px 0" />
            <el-row :gutter="12">
              <el-col :span="8">
                <span class="detail">成功: {{ metric.success }}</span>
              </el-col>
              <el-col :span="8">
                <span class="detail error-text">失败: {{ metric.errors }}</span>
              </el-col>
              <el-col :span="8">
                <span class="detail">P99: {{ metric.p99_ms }}ms</span>
              </el-col>
            </el-row>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!loading && metricsList.length === 0" description="暂无调用记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";

const loading = ref(false);
const metricsList = ref([]);

async function refresh() {
  loading.value = true;
  try {
    const token = localStorage.getItem("token");
    const res = await axios.get("/api/admin/metrics", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = res.data.data || {};
    const list = [];
    for (const [tool, m] of Object.entries(data)) {
      list.push({ tool, ...m });
    }
    list.sort((a, b) => b.calls - a.calls);
    metricsList.value = list;
  } catch {
    ElMessage.error("获取指标失败");
  } finally {
    loading.value = false;
  }
}

onMounted(refresh);
</script>

<style scoped>
.metrics-page { padding: 20px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.metric-card { margin-bottom: 20px; }
.metric-title { font-weight: 600; }
.stat { text-align: center; }
.stat-value { font-size: 24px; font-weight: 700; color: #303133; }
.stat-value.success { color: #67c23a; }
.stat-label { font-size: 12px; color: #909399; margin-top: 4px; }
.detail { font-size: 13px; color: #606266; }
.error-text { color: #f56c6c; }
</style>
