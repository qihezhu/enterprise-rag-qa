<!--
  管理员仪表盘页面
  展示系统核心统计数据、近7天提问趋势（折线图）、文档类型分布（饼图）、最近活动动态
  使用 ECharts 实现图表可视化
-->
<template>
    <div class="dashboard">
        <h3 class="page-title">系统仪表盘</h3>

        <!-- 统计卡片 -->
        <el-row :gutter="20" class="stats-row">
            <el-col :span="6">
                <div class="stat-card card-blue">
                    <div class="stat-value">{{ stats.user_count }}</div>
                    <div class="stat-label">用户总数</div>
                </div>
            </el-col>
            <el-col :span="6">
                <div class="stat-card card-green">
                    <div class="stat-value">{{ stats.document_count }}</div>
                    <div class="stat-label">文档总数</div>
                </div>
            </el-col>
            <el-col :span="6">
                <div class="stat-card card-orange">
                    <div class="stat-value">{{ stats.qa_count_today }}</div>
                    <div class="stat-label">今日提问</div>
                </div>
            </el-col>
            <el-col :span="6">
                <div class="stat-card card-purple">
                    <div class="stat-value">{{ stats.qa_count_total }}</div>
                    <div class="stat-label">累计问答</div>
                </div>
            </el-col>
        </el-row>

        <!-- ECharts图表 -->
        <el-row :gutter="20" class="charts-row">
            <el-col :span="14">
                <div class="chart-box">
                    <h4>近7天提问趋势</h4>
                    <div ref="lineChartRef" class="chart-container"></div>
                </div>
            </el-col>
            <el-col :span="10">
                <div class="chart-box">
                    <h4>文档类型分布</h4>
                    <div ref="pieChartRef" class="chart-container"></div>
                </div>
            </el-col>
        </el-row>

        <!-- 最近活动 -->
        <div class="activity-box">
            <h4>最近活动动态</h4>
            <el-timeline>
                <el-timeline-item
                    v-for="(activity, idx) in stats.recent_activities"
                    :key="idx"
                    :timestamp="activity.time"
                    placement="top"
                >
                    <span class="activity-user">{{ activity.user }}</span>
                    {{ getActionLabel(activity.action) }}
                    <span class="activity-detail">{{ activity.detail }}</span>
                </el-timeline-item>
            </el-timeline>
            <el-empty v-if="stats.recent_activities.length === 0" description="暂无活动记录" />
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from "vue";
import * as echarts from "echarts";
import { getStatisticsApi } from "../../api/admin";

/** 统计数据 */
const stats = reactive({
    user_count: 0,
    document_count: 0,
    total_chunks: 0,
    qa_count_today: 0,
    qa_count_total: 0,
    daily_qa_trend: [],
    doc_type_distribution: [],
    recent_activities: [],
});

const lineChartRef = ref(null);
const pieChartRef = ref(null);

/** 加载统计数据并渲染图表 */
onMounted(async () => {
    try {
        const res = await getStatisticsApi();
        Object.assign(stats, res.data);

        // 等待DOM更新后渲染图表
        await nextTick();
        renderLineChart();
        renderPieChart();
    } catch {
        // 错误已在拦截器处理
    }
});

/** 渲染近7天提问趋势折线图 */
function renderLineChart() {
    if (!lineChartRef.value || !stats.daily_qa_trend.length) return;

    const chart = echarts.init(lineChartRef.value);
    chart.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
        xAxis: {
            type: "category",
            data: stats.daily_qa_trend.map((item) => item.date),
            axisLine: { lineStyle: { color: "#dcdfe6" } },
        },
        yAxis: {
            type: "value",
            minInterval: 1,
            axisLine: { lineStyle: { color: "#dcdfe6" } },
        },
        series: [
            {
                data: stats.daily_qa_trend.map((item) => item.count),
                type: "line",
                smooth: true,
                symbol: "circle",
                symbolSize: 8,
                lineStyle: { color: "#409eff", width: 3 },
                itemStyle: { color: "#409eff" },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: "rgba(64,158,255,0.3)" },
                        { offset: 1, color: "rgba(64,158,255,0.05)" },
                    ]),
                },
            },
        ],
    });

    // 响应窗口大小变化
    window.addEventListener("resize", () => chart.resize());
}

/** 渲染文档类型分布饼图 */
function renderPieChart() {
    if (!pieChartRef.value || !stats.doc_type_distribution.length) return;

    const chart = echarts.init(pieChartRef.value);
    chart.setOption({
        tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
        legend: { bottom: "0%", textStyle: { fontSize: 12 } },
        series: [
            {
                type: "pie",
                radius: ["55%", "80%"],
                center: ["50%", "45%"],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
                label: { show: false },
                emphasis: {
                    label: { show: true, fontSize: 16, fontWeight: "bold" },
                },
                data: stats.doc_type_distribution.map((item) => ({
                    name: item.type.toUpperCase(),
                    value: item.count,
                })),
            },
        ],
    });

    window.addEventListener("resize", () => chart.resize());
}

/** 获取操作类型的友好显示文本 */
function getActionLabel(action) {
    const labels = {
        LOGIN: "登录了系统",
        USER_REGISTER: "注册了新账号",
        DOC_UPLOAD: "上传了文档",
        DOC_DELETE: "删除了文档",
        QA_ASK: "提问",
        USER_UPDATE: "修改了用户信息",
        USER_DELETE: "删除了用户",
    };
    return labels[action] || action;
}
</script>

<style scoped>
.dashboard {
    max-width: 1200px;
}

.page-title {
    font-size: 20px;
    color: #303133;
    margin-bottom: 24px;
}

/* ==================== 统计卡片 ==================== */
.stats-row {
    margin-bottom: 24px;
}

.stat-card {
    padding: 20px;
    border-radius: 8px;
    color: #fff;
}

.card-blue {
    background: linear-gradient(135deg, #667eea, #764ba2);
}

.card-green {
    background: linear-gradient(135deg, #43e97b, #38f9d7);
    color: #303133;
}

.card-orange {
    background: linear-gradient(135deg, #f093fb, #f5576c);
}

.card-purple {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
    color: #303133;
}

.stat-card .stat-value {
    font-size: 32px;
    font-weight: 700;
}

.stat-card .stat-label {
    font-size: 13px;
    margin-top: 4px;
    opacity: 0.9;
}

/* ==================== 图表区域 ==================== */
.charts-row {
    margin-bottom: 24px;
}

.chart-box {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.chart-box h4 {
    font-size: 15px;
    color: #303133;
    margin-bottom: 12px;
}

.chart-container {
    width: 100%;
    height: 300px;
}

/* ==================== 活动动态 ==================== */
.activity-box {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.activity-box h4 {
    font-size: 15px;
    color: #303133;
    margin-bottom: 16px;
}

.activity-user {
    font-weight: 600;
    color: #409eff;
}

.activity-detail {
    color: #909399;
    margin-left: 4px;
}
</style>
