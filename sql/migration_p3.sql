-- P3 迁移：客户运营记录表
-- 用法: mysql -u root -p db_enterprise_ge < sql/migration_p3.sql

USE db_enterprise_ge;

CREATE TABLE IF NOT EXISTS t_customer_record (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL COMMENT '企微员工UserID',
    external_userid VARCHAR(64) NOT NULL COMMENT '外部联系人UserID',
    action_type ENUM('tag','broadcast','follow') NOT NULL COMMENT '操作类型：tag=打标签，broadcast=群发，follow=查跟进',
    detail_json JSON COMMENT '操作详情（JSON格式）',
    api_result JSON COMMENT '企微API返回结果',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_cr_user_id (user_id),
    INDEX idx_cr_external_userid (external_userid),
    INDEX idx_cr_action_type (action_type),
    INDEX idx_cr_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
