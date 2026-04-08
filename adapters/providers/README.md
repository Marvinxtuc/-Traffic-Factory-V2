# Providers Boundary

本目录只提供一期最小 provider 占位，不接入真实第三方平台。

已落地占位：

- `content_provider.py`：内容生成能力占位
- `image_provider.py`：图片生成能力占位
- `publish_check_provider.py`：发布检查增强能力占位

统一协议：

- `base.py` 提供 `CapabilityProvider` 协议和 `CapabilityCallResult` 返回结构。

边界约束：

1. 不接入外部 API Key。
2. 不引入复杂网络依赖。
3. 仅用于统一能力接入结构验证。
