<!--
  用户管理页面（管理员视角）
  查看所有用户列表、搜索用户、启用/禁用用户、修改角色、删除用户
-->
<template>
    <div class="user-manage">
        <h3 class="page-title">用户管理</h3>

        <!-- 搜索栏 -->
        <div class="toolbar">
            <el-input
                v-model="keyword"
                placeholder="搜索用户名或邮箱..."
                clearable
                style="width: 280px"
                @keyup.enter="handleSearch"
                @clear="handleSearch"
            >
                <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>

        <!-- 用户表格 -->
        <div class="table-box card-box">
            <el-table :data="users" v-loading="loading" stripe>
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="username" label="用户名" width="120" />
                <el-table-column prop="email" label="邮箱" min-width="180" />
                <el-table-column prop="phone" label="手机号" width="130" />
                <el-table-column label="角色" width="100">
                    <template #default="{ row }">
                        <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                            {{ row.role === "admin" ? "管理员" : "普通用户" }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column label="状态" width="90">
                    <template #default="{ row }">
                        <el-switch
                            :model-value="row.status === 1"
                            :disabled="row.id === currentUserId"
                            @change="(val) => handleStatusChange(row, val)"
                        />
                    </template>
                </el-table-column>
                <el-table-column prop="created_at" label="注册时间" width="170" />
                <el-table-column label="操作" width="180" fixed="right">
                    <template #default="{ row }">
                        <el-button text type="primary" size="small" @click="showRoleDialog(row)">
                            修改角色
                        </el-button>
                        <el-button
                            text
                            type="danger"
                            size="small"
                            :disabled="row.id === currentUserId || row.role === 'admin'"
                            @click="handleDelete(row)"
                        >
                            删除
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
        </div>

        <Pagination
            :total="total"
            :page="page"
            :pageSize="pageSize"
            @update:page="onPageChange"
            @update:pageSize="onSizeChange"
        />

        <!-- 修改角色对话框 -->
        <el-dialog v-model="roleDialogVisible" title="修改用户角色" width="400px">
            <p>用户：<strong>{{ currentUser?.username }}</strong></p>
            <el-radio-group v-model="selectedRole" class="role-group">
                <el-radio value="user">普通用户</el-radio>
                <el-radio value="admin">管理员</el-radio>
            </el-radio-group>
            <template #footer>
                <el-button @click="roleDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmRoleChange">确认</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getUserListApi, updateUserApi, deleteUserApi } from "../../api/admin";
import Pagination from "../../components/Pagination.vue";

const users = ref([]);
const loading = ref(false);
const keyword = ref("");
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const currentUserId = ref(0);

const roleDialogVisible = ref(false);
const currentUser = ref(null);
const selectedRole = ref("user");

/** 加载用户列表 */
async function loadUsers() {
    loading.value = true;
    try {
        const res = await getUserListApi({
            page: page.value,
            page_size: pageSize.value,
            keyword: keyword.value,
        });
        users.value = res.data.items;
        total.value = res.data.total;
    } finally {
        loading.value = false;
    }
}

/** 搜索 */
function handleSearch() {
    page.value = 1;
    loadUsers();
}

/** 启用/禁用用户 */
async function handleStatusChange(row, enabled) {
    try {
        await updateUserApi(row.id, { status: enabled ? 1 : 0 });
        row.status = enabled ? 1 : 0;
        ElMessage.success(enabled ? "用户已启用" : "用户已禁用");
    } catch {
        // 错误已在拦截器处理
    }
}

/** 显示修改角色对话框 */
function showRoleDialog(row) {
    currentUser.value = row;
    selectedRole.value = row.role;
    roleDialogVisible.value = true;
}

/** 确认修改角色 */
async function confirmRoleChange() {
    try {
        await updateUserApi(currentUser.value.id, { role: selectedRole.value });
        currentUser.value.role = selectedRole.value;
        roleDialogVisible.value = false;
        ElMessage.success("角色修改成功");
    } catch {
        // 错误已在拦截器处理
    }
}

/** 删除用户 */
async function handleDelete(row) {
    try {
        await ElMessageBox.confirm(
            `确定要删除用户 "${row.username}" 吗？该操作不可恢复！`,
            "确认删除",
            { type: "warning" }
        );
        await deleteUserApi(row.id);
        ElMessage.success("用户已删除");
        loadUsers();
    } catch {
        // 用户取消
    }
}

function onPageChange(newPage) {
    page.value = newPage;
    loadUsers();
}

function onSizeChange(newSize) {
    pageSize.value = newSize;
    page.value = 1;
    loadUsers();
}

onMounted(() => {
    loadUsers();
});
</script>

<style scoped>
.user-manage {
    max-width: 1200px;
}

.page-title {
    font-size: 18px;
    color: #303133;
    margin-bottom: 20px;
}

.toolbar {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.role-group {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 12px;
}
</style>
