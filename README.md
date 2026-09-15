# ArchMind

多专业工程设计预审工具。ArchMind 将园建、植物、雨水海绵审查、跨专业协调、证据核验和人工确认组织成有明确责任边界的 AgentTeams 工作流。

输入是授权的结构化工程事实；输出是可追溯的专业意见、跨专业关系和待人工确认事项。当前没有 CAD/BIM/OCR 解析器，也没有图形界面。

## 本地运行

```bash
conda env create -f environment.yml
conda activate archmind
make verify
make demo
make build
```

已有 `archmind` 环境时，直接激活即可。`make demo` 对合成测试数据执行离线评估，不启动服务、不调用模型；结果在 `evaluation/baseline/`。五个角色包位于 `packages/dist/`。

## 工作流

```text
人工提交任务
  → Manager：任务分派、完整性检查
  → review-coordinator
      → 园建 Reviewer
      → 植物 Reviewer
      → 雨水海绵 Reviewer
      → 跨专业协调
      → evidence-verifier：证据核验
  → 人类总工确认
```

五类技能分别负责上下文提取、专业意见格式化、跨专业关系检查、证据核验和汇总。技能是声明式指令文档；文件存在或角色包安装完成不表示模型实际使用过技能。

## 真实 AgentTeams 运行

需要独立的 AgentTeams v1.2.1 环境、Docker/Podman 服务、Matrix、对象存储以及自己的模型服务凭据。

```bash
conda activate archmind
cp .env.example .env
# 在本地填写 .env 中的服务地址、角色包 URI 和凭据配置
make runtime-preflight
make runtime-up
make runtime-health
```

`runtime-up` 准备声明式资源，不发送审查任务。通过 Matrix 分派真实业务任务时，遵守 [任务分派](runbooks/dispatch.md) 与 [人工确认协议](runbooks/human-gate.md)。`make runtime-down` 停止 Agent Runtime，不删除业务资源。所有角色默认关闭心跳。

## 文档

- [系统结构](docs/architecture.md)
- [运行配置](docs/runtime.md)
- [开发与验证](docs/development.md)
- [数据契约与工具](docs/contracts.md)
- [数据与责任边界](docs/security.md)
- [第三方依赖](THIRD_PARTY_NOTICES.md)

AI 预审不替代法定审查或专业工程师签字。证据不足必须明确标注；未处理的人工确认事项不能由脚本、计时器或 Agent 自动批准。

## 许可

Copyright (C) 2026 Ustinian5。ArchMind 采用 [GNU AGPL v3.0](LICENSE)，许可标识为 `AGPL-3.0-only`。第三方平台和服务遵守各自条款。
