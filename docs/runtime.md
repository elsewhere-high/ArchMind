# 运行配置

使用 Conda 中的 Python 3.11。配置模板中的空值必须由运行环境提供；不要把凭据提交到 Git，也不要把带凭据的 URI 放入部署文件。

| 变量 | 用途 |
|---|---|
| CONTAINER_ENGINE | docker 或 podman |
| AGENTTEAMS_ACCESS_MODE | container 或 host |
| AGENTTEAMS_CONTROLLER | container 模式下的 Controller 容器名 |
| AGENTTEAMS_MANAGER_CONTAINER | container 模式下的 Manager 容器名 |
| AGENTTEAMS_API_ENDPOINT | AgentTeams API 地址 |
| MATRIX_ENDPOINT | Matrix 服务地址 |
| MODEL_ENDPOINT | 模型服务地址 |
| AGENTTEAMS_LLM_API_KEY | 本地模型凭据；不得公开 |
| MODEL_CREDENTIAL_CONFIGURED | 已在外部平台配置模型 Secret 时设为 true |
| PACKAGE_URI_BASE | 五个角色 ZIP 文件的统一存储前缀 |
| PACKAGE_URI_REVIEW_COORDINATOR | 单独覆盖协调者包 URI |
| PACKAGE_URI_HARDSCAPE_REVIEWER | 单独覆盖园建包 URI |
| PACKAGE_URI_PLANTING_REVIEWER | 单独覆盖植物包 URI |
| PACKAGE_URI_STORMWATER_SPONGE_REVIEWER | 单独覆盖雨水海绵包 URI |
| PACKAGE_URI_EVIDENCE_VERIFIER | 单独覆盖核验者包 URI |

包 URI 必须使用绝对 URI，不得包含用户名、密码、查询字符串或 fragment。将 `make build` 生成的文件放在 AgentTeams 可访问的受控存储中。

启动顺序：preflight → 构建角色包 → 解析 URI → 渲染 YAML → 应用资源 → 健康检查。生成的 YAML 与本地环境配置不入库。只在独立的干净 Runtime 环境应用资源：平台 Manager 使用 `default`，Team 使用 `archmind-review-team`。

平台通信变量保留 AGENTTEAMS 名称；这是依赖平台的接口。`chief-engineer` 是人工总工角色，只有实际人类消息可以形成有效决策。
