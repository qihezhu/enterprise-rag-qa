-- ===================================================
-- 企业知识库问答系统 - 数据库初始化脚本
-- 数据库名: db_enterprise_ge
-- MySQL版本要求: 8.0+
-- ===================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS db_enterprise_ge
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE db_enterprise_ge;

-- ===================================================
-- 用户表
-- ===================================================
CREATE TABLE IF NOT EXISTS t_user (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(32) NOT NULL COMMENT 'MD5加密密码',
    role ENUM('admin', 'user') DEFAULT 'user' COMMENT '角色：admin管理员 user普通用户',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    avatar VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
    status TINYINT DEFAULT 1 COMMENT '状态：1启用 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username),
    INDEX idx_role (role),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ===================================================
-- 知识文档表
-- ===================================================
CREATE TABLE IF NOT EXISTS t_document (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '文档ID',
    title VARCHAR(200) NOT NULL COMMENT '文档标题',
    content LONGTEXT COMMENT '解析后的纯文本内容',
    file_name VARCHAR(200) DEFAULT NULL COMMENT '原始文件名',
    file_type VARCHAR(20) DEFAULT NULL COMMENT '文件类型：pdf/docx/txt/md',
    file_size INT DEFAULT 0 COMMENT '文件大小（字节）',
    chunk_count INT DEFAULT 0 COMMENT '文本分块数量',
    status TINYINT DEFAULT 1 COMMENT '状态：1正常 0已删除',
    uploader_id INT NOT NULL COMMENT '上传者ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (uploader_id) REFERENCES t_user(id) ON DELETE CASCADE,
    INDEX idx_uploader_id (uploader_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    FULLTEXT INDEX idx_title_content (title, content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识文档表';

-- ===================================================
-- 文档分块表（记录文档分块与Chroma向量的映射关系）
-- ===================================================
CREATE TABLE IF NOT EXISTS t_document_chunk (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '分块ID',
    document_id INT NOT NULL COMMENT '所属文档ID',
    chunk_index INT NOT NULL COMMENT '块序号（从0开始）',
    content TEXT NOT NULL COMMENT '块文本内容',
    vector_id VARCHAR(100) DEFAULT NULL COMMENT 'Chroma向量库中的向量唯一ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (document_id) REFERENCES t_document(id) ON DELETE CASCADE,
    INDEX idx_document_id (document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档分块表';

-- ===================================================
-- 对话记录表
-- ===================================================
CREATE TABLE IF NOT EXISTS t_conversation (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '对话ID',
    user_id INT NOT NULL COMMENT '提问用户ID',
    question TEXT NOT NULL COMMENT '用户问题',
    answer LONGTEXT DEFAULT NULL COMMENT '模型回答',
    sources JSON DEFAULT NULL COMMENT '参考来源列表 [{title, file_name, chunk_index, content_preview}]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES t_user(id) ON DELETE CASCADE,
    INDEX idx_user_id_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话记录表';

-- ===================================================
-- 系统日志表
-- ===================================================
CREATE TABLE IF NOT EXISTS t_system_log (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    user_id INT DEFAULT NULL COMMENT '操作人ID（匿名操作可为空）',
    action VARCHAR(50) NOT NULL COMMENT '操作类型：LOGIN/DOC_UPLOAD/QA_ASK/DOC_DELETE/USER_REGISTER等',
    description VARCHAR(500) DEFAULT NULL COMMENT '操作详细描述',
    ip_address VARCHAR(50) DEFAULT NULL COMMENT '客户端IP地址',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES t_user(id) ON DELETE SET NULL,
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';
