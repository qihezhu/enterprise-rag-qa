# API接口设计规范

## 一、URL设计

### 1.1 基本原则
- 使用RESTful风格，资源名使用复数名词
- URL全部小写，单词间使用连字符 `-` 分隔
- 版本号放在URL中：`/api/v1/users`
- 避免层级过深，最多三级：`/api/v1/users/{id}/orders`

### 1.2 示例

```
GET    /api/v1/users           # 用户列表
GET    /api/v1/users/{id}      # 用户详情
POST   /api/v1/users           # 创建用户
PUT    /api/v1/users/{id}      # 更新用户
DELETE /api/v1/users/{id}      # 删除用户
GET    /api/v1/users/{id}/orders  # 用户的订单列表
```

## 二、请求规范

### 2.1 请求头

```
Content-Type: application/json
Authorization: Bearer <jwt_token>
Accept: application/json
```

### 2.2 分页参数

```
GET /api/v1/users?page=1&page_size=20&sort=-created_at&keyword=张三
```

## 三、响应规范

### 3.1 统一响应格式

所有接口返回统一的JSON格式：

```json
{
    "code": 200,
    "message": "操作成功",
    "data": { ... }
}
```

### 3.2 HTTP状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 | 成功 | GET、PUT请求成功 |
| 201 | 已创建 | POST创建资源成功 |
| 204 | 无内容 | DELETE成功 |
| 400 | 请求错误 | 参数校验失败 |
| 401 | 未认证 | Token过期或无效 |
| 403 | 无权限 | 权限不足 |
| 404 | 未找到 | 资源不存在 |
| 409 | 冲突 | 资源已存在（如用户名重复）|
| 500 | 服务器错误 | 服务端异常 |

## 四、鉴权规范

1. 使用JWT Token鉴权，Token放在请求头Authorization中
2. Token有效期24小时，过期后返回401
3. 敏感操作（删除、修改权限等）需要二次验证

## 五、错误响应

```json
{
    "code": 400,
    "message": "参数校验失败",
    "data": {
        "errors": [
            {"field": "username", "message": "用户名不能为空"},
            {"field": "email", "message": "邮箱格式不正确"}
        ]
    }
}
```

## 六、接口文档

1. 使用Swagger/OpenAPI规范编写接口文档
2. 接口文档地址：`/api/docs`
3. 每个接口须包含：请求方法、路径、参数说明、请求示例、响应示例、错误码说明
4. 接口变更时必须同步更新文档
