# 抓取安全策略说明

## 1. 策略结论（本轮选型）

采用方案 2：
- 保留 SSL 回退能力
- 但必须显式配置开关
- 默认关闭

原因：
- 兼容部分本地环境证书链异常场景
- 同时避免“默认静默降级”带来的安全口径不清

## 2. 配置项

- 环境变量：`TF_V1_ALLOW_INSECURE_SSL_FALLBACK`
- 取值：`1/true/yes/on` 表示开启，其余值关闭
- 默认值：`0`（关闭）

## 3. 行为矩阵

### 3.1 开关关闭（默认）

- `requests.get(..., verify=True)` 失败且为 SSL 错误时：
  - 直接返回错误
  - 不执行 `verify=False` 回退
  - 错误信息包含开启开关指引

### 3.2 开关开启

- 首次仍使用 `verify=True`
- 仅在 SSL 错误时，允许二次 `verify=False` 重试
- 响应中显式返回：
  - `ssl_verified`
  - `ssl_fallback_used`
  - `ssl_fallback_enabled`

## 4. 审计性保证

- 不存在“默默回退”路径
- 回退行为受显式配置控制
- 回退是否发生可通过接口响应字段复核
