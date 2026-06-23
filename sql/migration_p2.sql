-- P2 迁移：日程记录表
-- 用法: mysql -u root -p db_enterprise_ge < sql/migration_p2.sql

USE db_enterprise_ge;

CREATE TABLE IF NOT EXISTS t_schedule_record (
    id INT PRIMARY KEY AUTO_INCREMENT,
    organizer_user_id VARCHAR(64) NOT NULL COMMENT '组织者企微UserID',
    schedule_id VARCHAR(64) COMMENT '企微日程ID',
    subject VARCHAR(200) NOT NULL COMMENT '会议主题',
    start_time DATETIME COMMENT '开始时间（UTC）',
    end_time DATETIME COMMENT '结束时间（UTC）',
    attendees_json JSON COMMENT '参会人员列表（JSON）',
    location VARCHAR(200) COMMENT '会议室/地点',
    status ENUM('created','updated','cancelled') DEFAULT 'created' COMMENT '日程状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_sr_organizer (organizer_user_id),
    INDEX idx_sr_schedule_id (schedule_id),
    INDEX idx_sr_start_time (start_time),
    INDEX idx_sr_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
