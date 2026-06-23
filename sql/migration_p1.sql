-- P1 迁移：审批记录表
-- 用法: mysql -u root -p db_enterprise_ge < sql/migration_p1.sql

USE db_enterprise_ge;

CREATE TABLE IF NOT EXISTS t_approval_record (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL COMMENT '企微UserID（申请人）',
    sp_no VARCHAR(64) COMMENT '企微审批单号',
    template_name VARCHAR(100) NOT NULL COMMENT '审批模板名称',
    status ENUM('pending','approved','rejected','cancelled') DEFAULT 'pending' COMMENT '审批状态',
    fields_json JSON COMMENT '审批字段快照（JSON格式）',
    card_msg_id VARCHAR(64) COMMENT '卡片消息ID（用于update_button）',
    response_code VARCHAR(64) COMMENT '卡片响应码',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_ar_user_id (user_id),
    INDEX idx_ar_sp_no (sp_no),
    INDEX idx_ar_status (status),
    INDEX idx_ar_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
