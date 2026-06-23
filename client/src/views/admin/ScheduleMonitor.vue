<template>
  <div class="schedule-monitor">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>日程监控</span>
          <el-select
            v-model="statusFilter"
            placeholder="状态筛选"
            clearable
            style="width: 140px"
            @change="fetchData"
          >
            <el-option label="全部" value="" />
            <el-option label="已创建" value="created" />
            <el-option label="已更新" value="updated" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </div>
      </template>

      <el-table :data="records" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="organizer_user_id" label="组织者" width="120" />
        <el-table-column prop="schedule_id" label="日程ID" min-width="160" />
        <el-table-column prop="subject" label="会议主题" min-width="150" />
        <el-table-column prop="location" label="地点" width="120" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="170">
          <template #default="{ row }">{{ formatTime(row.end_time) }}</template>
        </el-table-column>
        <el-table-column label="参会人员" min-width="150">
          <template #default="{ row }">
            <el-tag
              v-for="(user, i) in (row.attendees_json || [])"
              :key="i"
              size="small"
              class="user-tag"
            >
              {{ user.userid || user }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <Pagination
        :total="total"
        :page="page"
        :pageSize="pageSize"
        @update:page="page = $event; fetchData()"
        @update:pageSize="pageSize = $event; fetchData()"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import Pagination from "../../components/Pagination.vue";
import axios from "axios";

const records = ref([]);
const loading = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const statusFilter = ref("");

function statusType(s) {
  return { created: "success", updated: "warning", cancelled: "info" }[s] || "info";
}
function statusLabel(s) {
  return { created: "已创建", updated: "已更新", cancelled: "已取消" }[s] || s;
}
function formatTime(ts) {
  if (!ts) return "-";
  return new Date(ts).toLocaleString("zh-CN");
}

async function fetchData() {
  loading.value = true;
  try {
    const token = localStorage.getItem("token");
    const res = await axios.get("/api/wecom/schedule-records", {
      params: { page: page.value, page_size: pageSize.value, status: statusFilter.value },
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = res.data.data || res.data;
    records.value = data.items || [];
    total.value = data.total || 0;
  } catch {
    ElMessage.error("获取日程记录失败");
  } finally {
    loading.value = false;
  }
}

onMounted(fetchData);
</script>

<style scoped>
.schedule-monitor { padding: 20px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.user-tag { margin: 2px; }
</style>
