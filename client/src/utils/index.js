/**
 * 前端工具函数模块
 */

/**
 * 格式化日期时间字符串
 * @param {string} dateStr - ISO日期字符串
 * @returns {string} 格式化后的日期时间
 */
export function formatDateTime(dateStr) {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    const h = String(date.getHours()).padStart(2, "0");
    const min = String(date.getMinutes()).padStart(2, "0");
    return `${y}-${m}-${d} ${h}:${min}`;
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 可读的文件大小
 */
export function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
    }
    return `${size.toFixed(1)} ${units[i]}`;
}

/**
 * 获取文件类型对应的图标颜色
 * @param {string} fileType - 文件扩展名
 * @returns {string} 颜色值
 */
export function getFileTypeColor(fileType) {
    const colors = {
        pdf: "#f56c6c",
        docx: "#409eff",
        txt: "#67c23a",
        md: "#e6a23c",
    };
    return colors[fileType] || "#909399";
}

/**
 * 获取主题分类对应的标签颜色
 * @param {string} topic - 主题名称
 * @returns {string} 颜色值
 */
export function getTopicColor(topic) {
    const colors = {
        "财务管理": "#e6a23c",
        "行政管理": "#409eff",
        "技术管理": "#67c23a",
        "IT运维": "#f56c6c",
        "数据管理": "#00bcd4",
        "开发规范": "#9c27b0",
        "组织管理": "#ff9800",
        "人力资源": "#e91e63",
        "安全管理": "#607d8b",
    };
    return colors[topic] || "#909399";
}
