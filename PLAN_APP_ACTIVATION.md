# App 联网激活改进方案

> 本文档为 AI 实施指引（非用户文档），描述蚁仓系统 App 端联网激活机制的技术改造设计。落地时按"实施步骤"顺序执行，并参照现有 `backend/` 代码风格（FastAPI + SQLAlchemy + Pydantic）。

---

## 背景与问题

当前 `device_token` 机制存在的问题：

1. **只绑设备不绑账号** → 无法区分"谁"在用，无法做账号维度的设备归属管理。
2. **无状态 JWT 无法主动吊销** → 借给别人后，只要 token 未过期就无法使其失效，存在账号借用风险。
3. **`activation_proof` 非空就接受** → 没有真正的身份校验，激活逻辑形同虚设。

---

## 目标

1. App 没登录不能和服务器对接。
2. App 账号没激活不能对接。
3. 换账号不能正常使用（防止账号借用）。
4. 管理员可在 Web 端吊销设备。

---

## 技术方案

### 数据模型

新建 `app_device` 表（对应 `backend/models/app_device.py`）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | Integer, PK | 主键 |
| `user_id` | Integer, FK → `user.id` | 绑定管理员账号 |
| `device_id` | String | App 生成的设备唯一标识 |
| `device_name` | String | 设备名称 |
| `activated_at` | DateTime | 激活时间 |
| `expires_at` | DateTime | 过期时间 |
| `is_active` | Boolean | 是否激活中，默认 `True` |
| `last_heartbeat_at` | DateTime | 最后心跳时间 |

- 约束：`UNIQUE(user_id, device_id)`
- 对应 schema 文件：`backend/schemas/app_device.py`
- 表初始化：在 `backend/init_db.py` 中加入 `app_device` 表创建逻辑。

### 接口设计

#### 1. POST `/api/app/activate`（需要管理员 JWT 鉴权）

- **入参**：`{ device_id, device_name }`
- **逻辑**：
  1. 从管理员 JWT 取 `user_id`。
  2. 查 `app_device` 表，同一 `user_id` 限制绑定 1 台设备（上限可由 `config.py` 配置）。
  3. 如已有旧设备 → 旧设备 `is_active = false`。
  4. 新建记录 → 签发 `device_token`（payload 含 `user_id` + `device_id`）。
- **返回**：`{ device_token, expires_at }`

#### 2. POST `/api/app/heartbeat`（需要 `device_token`）

- **逻辑**：
  1. 解析 `device_token` 得 `user_id` + `device_id`。
  2. 查 `app_device` 表确认 `is_active = true` 且未过期。
  3. 刷新 `last_heartbeat_at`。
- **返回**：`{ valid, expires_at, remaining_days }`
- **失败**：token 过期 / `is_active = false` → `401`

#### 3. GET `/api/app/devices`（需要管理员 JWT）

- **返回**：当前账号绑定的设备列表。

#### 4. DELETE `/api/app/devices/{id}`（需要管理员 JWT）

- **逻辑**：吊销设备 → `is_active = false`。

### 鉴权改造

- `get_current_user`（`backend/dependencies.py`）保持双通道（user token / device token）。
- `device_token` payload 增加 `user_id` 字段。
- 心跳时查 `app_device` 表校验 `is_active`，不再纯靠 JWT 过期判断。

### 安全闭环

| 场景 | 结果 |
| --- | --- |
| App 没登录 | 拿不到管理员 JWT → 无法调 `activate` → `401` |
| App 登录但没激活 | `app_device` 表无记录 → 心跳失败 → `401` |
| 账号 A 借给 B | B 是另一 `user_id` → 无法用 A 的 token → `401` |
| 管理员吊销设备 | `is_active = false` → 心跳失败 → `401` |
| 同一账号换设备 | 旧设备自动失效 |

### Web 端新增

- 系统设置页（`frontend/src/views/Settings.vue`）新增"设备管理" Tab。
- 显示已激活设备列表：设备名、激活时间、最后心跳、状态。
- 支持吊销操作（调用 `DELETE /api/app/devices/{id}`）。
- 前端 API 封装加入 `frontend/src/api/index.js`。

### 实施步骤

1. 新建 `app_device` 表 + model + schema。
2. 改 `activate` 接口（加管理员鉴权 + 查表 + 写记录）。
3. 改 `heartbeat` 接口（加查表校验）。
4. 新增 `devices` 管理接口（`GET` / `DELETE`）。
5. Web 端 `Settings.vue` 加设备管理 Tab。
6. `init_db.py` 加 `app_device` 表初始化。
7. 测试：激活 → 心跳 → 吊销 → 换账号 全流程。

### 注意事项

- `device_token` 有效期改为 **7 天**（缩短，配合心跳续期）。
- 心跳建议 App 每 **24 小时**调一次。
- 绑定设备数限制可通过 `config.py` 配置。
- 旧 `verify-license` 接口保留不动（向后兼容）。
