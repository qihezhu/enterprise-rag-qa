<template>
  <div class="customer-ops">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>客户运营记录</span>
          <el-select
            v-model="actionFilter"
            placeholder="操作类型"
            clearable
            style="width: 140px"
            @change="fetchData"
          >
            <el-option label="全部" value="" />
            <el-option label="打标签" value="tag" />
            <el-option label="群发" value="broadcast" />
            <el-option label="查跟进" value="follow" />
          </el-select>
        </div>
      </template>

      <el-table :data="records" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="user_id" label="员工" width="120" />
        <el-table-column prop="external_userid" label="客户ID" min-width="160" />
        <el-table-column prop="action_type" label="操作" width="90">
          <template #default="{ row }">
            <el-tag :type="actionType(row.action_type)" size="small">
              {{ actionLabel(row.action_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="200">
          <template #default="{ row }">
            <template v-if="row.detail_json">
              <div v-if="row.action_type === 'tag'">
                <el-tag
                  v-for="(tag, i) in row.detail_json.tag_names"
                  :key="i"
                  size="small"
                  class="detail-tag"
                >
                  {{ tag }}
                </el-tag>
              </div>
              <div v-else-if="row.action_type === 'broadcast'">
                {{ row.detail_json.text?.substring(0, 60) }}{{ (row.detail_json.text?.length || 0) > 60 ? '...' : '' }}
              </div>
              <span v-else>-</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
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
const actionFilter = ref("");

function actionType(v) {
  return { tag: "success", broadcast: "warning", follow: "info" }[v] || "info";
}
function actionLabel(v) {
  return { tag: "打标签", broadcast: "群发", follow: "查跟进" }[v] || v;
}
function formatTime(ts) {
  if (!ts) return "-";
  return new Date(ts).toLocaleString("zh-CN");
}

async function fetchData() {
  loading.value = true;
  try {
    const token = localStorage.getItem("token");
    const res = await axios.get("/api/wecom/customer-records", {
      params: { page: page.value, page_size: pageSize.value, action_type: actionFilter.value },
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = res.data.data || res.data;
    records.value = data.items || [];
    total.value = data.total || 0;
  } catch {
    ElMessage.error("获取客户运营记录失败");
  } finally {
    loading.value = false;
  }
}

onMounted(fetchData);
</script>

<style scoped>
.customer-ops { padding: 20px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.detail-tag { margin: 2px; }
</style>
