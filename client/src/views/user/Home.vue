<!--
  普通用户首页
  展示统计卡片：我的文档数、提问数等
-->
<template>
    <div class="user-home">
        <h3 class="page-title">欢迎使用企业知识库问答系统</h3>

        <el-row :gutter="20" class="stats-row">
            <el-col :span="8">
                <div class="stat-card">
                    <div class="stat-icon doc-icon-bg">
                        <el-icon size="28"><Document /></el-icon>
                    </div>
                    <div class="stat-info">
                        <div class="stat-value">{{ stats.docCount }}</div>
                        <div class="stat-label">我的文档</div>
                    </div>
                </div>
            </el-col>
            <el-col :span="8">
                <div class="stat-card">
                    <div class="stat-icon qa-icon-bg">
                        <el-icon size="28"><ChatDotRound /></el-icon>
                    </div>
                    <div class="stat-info">
                        <div class="stat-value">{{ stats.qaCount }}</div>
                        <div class="stat-label">我的提问</div>
                    </div>
                </div>
            </el-col>
            <el-col :span="8">
                <div class="stat-card">
                    <div class="stat-icon total-icon-bg">
                        <el-icon size="28"><Collection /></el-icon>
                    </div>
                    <div class="stat-info">
                        <div class="stat-value">{{ stats.totalDocs }}</div>
                        <div class="stat-label">知识库文档总数</div>
                    </div>
                </div>
            </el-col>
        </el-row>

        <div class="quick-actions">
            <h4>快捷操作</h4>
            <el-row :gutter="16">
                <el-col :span="12">
                    <el-card shadow="hover" class="action-card" @click="$router.push('/user/qa')">
                        <el-icon size="32" color="#409eff"><ChatDotRound /></el-icon>
                        <p>智能问答</p>
                        <span>向知识库助手提问</span>
                    </el-card>
                </el-col>
                <el-col :span="12">
                    <el-card shadow="hover" class="action-card" @click="$router.push('/user/documents')">
                        <el-icon size="32" color="#e6a23c"><Document /></el-icon>
                        <p>文档管理</p>
                        <span>查看和管理知识文档</span>
                    </el-card>
                </el-col>
            </el-row>
        </div>
    </div>
</template>

<script setup>
import { reactive, onMounted } from "vue";
import { getDocumentListApi } from "../../api/document";
import { getQaHistoryApi } from "../../api/qa";

const stats = reactive({
    docCount: 0,
    qaCount: 0,
    totalDocs: 0,
});

/** 加载用户统计数据 */
onMounted(async () => {
    try {
        // 获取文档总数（所有登录用户均可查看全部知识库文档）
        const docRes = await getDocumentListApi({ page: 1, page_size: 1 });
        stats.totalDocs = docRes.data.total || 0;
        stats.docCount = docRes.data.total || 0;
    } catch {
        // 静默处理
    }

    try {
        // 获取提问统计
        const qaRes = await getQaHistoryApi({ page: 1, page_size: 1 });
        stats.qaCount = qaRes.data.total || 0;
    } catch {
        // 静默处理
    }
});
</script>

<style scoped>
.user-home {
    max-width: 1000px;
}

.page-title {
    font-size: 20px;
    color: #303133;
    margin-bottom: 24px;
}

.stats-row {
    margin-bottom: 32px;
}

.stat-card {
    display: flex;
    align-items: center;
    padding: 24px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-icon {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    margin-right: 16px;
    color: #fff;
}

.doc-icon-bg {
    background: linear-gradient(135deg, #667eea, #764ba2);
}

.qa-icon-bg {
    background: linear-gradient(135deg, #f093fb, #f5576c);
}

.total-icon-bg {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
}

.stat-info {
    flex: 1;
}

.stat-value {
    font-size: 28px;
    font-weight: 600;
    color: #303133;
}

.stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 4px;
}

.quick-actions h4 {
    font-size: 16px;
    color: #303133;
    margin-bottom: 16px;
}

.action-card {
    text-align: center;
    cursor: pointer;
    padding: 20px 0;
}

.action-card p {
    font-size: 15px;
    font-weight: 500;
    color: #303133;
    margin: 8px 0 4px;
}

.action-card span {
    font-size: 12px;
    color: #909399;
}
</style>
