# Provider Config Notes

`providers.toml` 建议放在 `private/` 下，不进入版本控制。

示例：

```toml
[serpapi]
api_key = "your-key"

[static_json]
data_path = "private/provider-data/example-results.json"
```

如果只做离线验证，可以只保留 `[static_json]`。
