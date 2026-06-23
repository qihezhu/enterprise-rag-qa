<template>
  <div class="approval-monitor">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审批记录监控</span>
          <div class="header-actions">
            <el-select
              v-model="statusFilter"
              placeholder="按状态筛选"
              clearable
              style="width: 140px; margin-right: 12px"
              @change="fetchData"
            >
              <el-option label="全部" value="" />
              <el-option label="待审批" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="已取消" value="cancelled" />
            </el-select>
            <el-button type="primary" @click="openCreateDialog">新建审批</el-button>
          </div>
        </div>
      </template>

      <el-table :data="records" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="user_id" label="申请人" width="140" />
        <el-table-column prop="sp_no" label="审批单号" min-width="180" />
        <el-table-column prop="template_name" label="模板" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="申请内容" min-width="200">
          <template #default="{ row }">
            <template v-if="row.fields_json">
              <el-tag
                v-for="(val, key) in row.fields_json"
                :key="key"
                size="small"
                class="field-tag"
              >
                {{ key }}: {{ val }}
              </el-tag>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" size="small" @click="approve(row)">通过</el-button>
              <el-button type="danger" size="small" @click="reject(row)">驳回</el-button>
            </template>
            <span v-else style="color: #909399">-</span>
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

    <!-- 新建审批对话框 -->
    <el-dialog v-model="dialogVisible" title="新建审批" width="560px" @close="resetForm">
      <el-form :model="form" label-width="80px">
        <el-form-item label="审批模板">
          <el-select v-model="form.template_name" @change="onTemplateChange" style="width: 100%">
            <el-option v-for="t in templates" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="申请人">
          <el-input v-model="form.user_id" placeholder="请输入申请人姓名或userid" />
        </el-form-item>
        <el-form-item
          v-for="ctrl in currentControls"
          :key="ctrl.id"
          :label="ctrl.name"
          :required="ctrl.required"
        >
          <el-select
            v-if="ctrl.type === 'selector'"
            v-model="form.fields[ctrl.name]"
            style="width: 100%"
          >
            <el-option v-for="o in ctrl.options" :key="o" :label="o" :value="o" />
          </el-select>
          <el-input
            v-else-if="ctrl.type === 'number'"
            v-model.number="form.fields[ctrl.name]"
            type="number"
          />
          <el-date-picker
            v-else-if="ctrl.type === 'date'"
            v-model="form.fields[ctrl.name]"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
          <el-input v-else v-model="form.fields[ctrl.name]" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitApproval">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { getApprovalRecordsApi, updateApprovalStatusApi, adminSubmitApprovalApi } from "../../api/approval";
import { ElMessage, ElMessageBox } from "element-plus";
import Pagination from "../../components/Pagination.vue";

const records = ref([]);
const loading = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const statusFilter = ref("");

// ==================== 新建审批 ====================
const dialogVisible = ref(false);
const submitting = ref(false);
const templates = ["请假", "加班", "报销", "出差", "采购", "用章"];
const form = ref({
  template_name: "请假",
  user_id: "",
  fields: {},
});

const templateSchemas = {
  请假: [
    { id: "leave_type", name: "请假类型", type: "selector", required: true, options: ["年假", "事假", "病假", "调休", "婚假", "产假"] },
    { id: "start_date", name: "开始日期", type: "date", required: true },
    { id: "end_date", name: "结束日期", type: "date", required: true },
    { id: "days", name: "请假天数", type: "number", required: true },
    { id: "reason", name: "请假原因", type: "text", required: true },
  ],
  加班: [
    { id: "overtime_date", name: "加班日期", type: "date", required: true },
    { id: "overtime_hours", name: "加班时长", type: "number", required: true },
    { id: "overtime_reason", name: "加班原因", type: "text", required: true },
  ],
  报销: [
    { id: "expense_type", name: "报销类型", type: "selector", required: true, options: ["差旅费", "办公费", "招待费", "交通费"] },
    { id: "expense_amount", name: "报销金额", type: "number", required: true },
    { id: "expense_reason", name: "报销说明", type: "text", required: true },
  ],
  出差: [
    { id: "travel_start", name: "出发日期", type: "date", required: true },
    { id: "travel_end", name: "返回日期", type: "date", required: true },
    { id: "travel_city", name: "目的地", type: "text", required: true },
    { id: "travel_reason", name: "出差事由", type: "text", required: true },
  ],
  采购: [
    { id: "purchase_item", name: "采购物品", type: "text", required: true },
    { id: "purchase_amount", name: "采购金额", type: "number", required: true },
    { id: "purchase_reason", name: "采购原因", type: "text", required: true },
  ],
  用章: [
    { id: "seal_type", name: "用章类型", type: "selector", required: true, options: ["公章", "合同章", "财务章", "法人章"] },
    { id: "seal_reason", name: "用章事由", type: "text", required: true },
  ],
};

const currentControls = computed(() => templateSchemas[form.value.template_name] || []);

function onTemplateChange() {
  form.value.fields = {};
}

function openCreateDialog() {
  form.value = { template_name: "请假", user_id: "", fields: {} };
  dialogVisible.value = true;
}

function resetForm() {
  form.value = { template_name: "请假", user_id: "", fields: {} };
}

async function submitApproval() {
  const ctrls = currentControls.value;
  const missing = ctrls.filter(c => c.required && !form.value.fields[c.name]);
  if (missing.length) {
    ElMessage.warning(`请填写必填字段: ${missing.map(c => c.name).join("、")}`);
    return;
  }
  if (!form.value.user_id.trim()) {
    ElMessage.warning("请填写申请人");
    return;
  }
  submitting.value = true;
  try {
    await adminSubmitApprovalApi({
      user_id: form.value.user_id.trim(),
      template_name: form.value.template_name,
      fields: form.value.fields,
    });
    ElMessage.success("审批提交成功");
    dialogVisible.value = false;
    fetchData();
  } catch {
    ElMessage.error("提交失败");
  } finally {
    submitting.value = false;
  }
}

// ==================== 审批操作 ====================

async function approve(row) {
  try {
    await ElMessageBox.confirm(`确认通过 ${row.user_id} 的${row.template_name}申请？`, "审批通过", { type: "warning" });
  } catch { return; }
  try {
    await updateApprovalStatusApi(row.id, "approved");
    ElMessage.success("已通过");
    fetchData();
  } catch {
    ElMessage.error("操作失败");
  }
}

async function reject(row) {
  try {
    await ElMessageBox.confirm(`确认驳回 ${row.user_id} 的${row.template_name}申请？`, "审批驳回", { type: "warning" });
  } catch { return; }
  try {
    await updateApprovalStatusApi(row.id, "rejected");
    ElMessage.success("已驳回");
    fetchData();
  } catch {
    ElMessage.error("操作失败");
  }
}

// ==================== 工具函数 ====================

function statusType(status) {
  const map = { pending: "warning", approved: "success", rejected: "danger", cancelled: "info" };
  return map[status] || "info";
}

function statusLabel(status) {
  const map = { pending: "待审批", approved: "已通过", rejected: "已驳回", cancelled: "已取消" };
  return map[status] || status;
}

function formatTime(ts) {
  if (!ts) return "-";
  return new Date(ts).toLocaleString("zh-CN");
}

async function fetchData() {
  loading.value = true;
  try {
    const res = await getApprovalRecordsApi({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value,
    });
    records.value = res.data.items || [];
    total.value = res.data.total || 0;
  } catch {
    ElMessage.error("获取审批记录失败");
  } finally {
    loading.value = false;
  }
}

onMounted(fetchData);
</script>

<style scoped>
.approval-monitor {
  padding: 20px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-actions {
  display: flex;
  align-items: center;
}
.field-tag {
  margin: 2px;
}
</style>
