# ArchMind · 2026 上海开源软件应用创新大赛

**参赛赛道：AI+ 工业软件。** ArchMind 面向建筑工程设计中的多专业内部预审，将园建、植物、雨水海绵、跨专业协调、证据核验与人工确认组织为有明确责任边界的工作流。

本次发布提供 7 页中文作品介绍、3 分 41 秒演示视频、完整离线验证记录和五个 AgentTeams 角色包。

## 评审材料

- [作品介绍 PDF](https://github.com/elsewhere-high/ArchMind/releases/download/v0.1.0-os2026/ArchMind-OS2026-Introduction.pdf)：项目背景、技术架构、应用场景、创新点、验证结果与开源规划。
- [作品演示视频 MP4](https://github.com/elsewhere-high/ArchMind/releases/download/v0.1.0-os2026/ArchMind-OS2026-Demo.mp4)：1920×1080，H.264/AAC，中文合成配音与画内字幕。
- [完整提交材料 ZIP](https://github.com/elsewhere-high/ArchMind/releases/download/v0.1.0-os2026/ArchMind-OS2026-Submission.zip)：介绍文档、视频、UTF-8 字幕、验证记录、角色包和提交链接。
- [源码与复现说明](https://github.com/elsewhere-high/ArchMind)：完整代码同时可从本 Release 的 Source code 附件下载。

## 视频章节

| 时间 | 内容 |
|---|---|
| 00:00 | 项目介绍 |
| 00:19 | 角色、证据与责任架构 |
| 00:41 | 读取工程事实 |
| 01:01 | 查看三专业意见与事实引用 |
| 01:24 | 跨专业关系、缺失资料和人工事项 |
| 01:50 | 拒绝带待确认事项提前完成 |
| 02:12 | 项目验证 |
| 02:31 | 离线评估 |
| 02:57 | 五个角色包构建 |
| 03:18 | 开源交付与后续计划 |

## 验证与范围

在 Conda `archmind` 环境执行 `make verify`、`make demo`、`make build` 均通过。18 条合成记录的必填字段完整性为 171/171，证据引用完整性为 18/18，证据不足的可解释性为 6/6，人工确认准备度为 7/7，已有 Schema 覆盖记录的有效性为 11/11。

视频回放真实命令输出；专业意见与跨专业关系是仓库预写合成回归数据，不是本次新生成的模型审查结果。人工确认拦截只操作临时测试文件。上述比例衡量数据结构和约束，不代表 AI 准确率、工程合规率或生产效率。

当前交付为命令行工具、声明式技能与角色包，无 CAD/BIM/OCR 解析器或产品图形界面。真实模型运行需独立部署 AgentTeams v1.2.1、容器服务、Matrix、对象存储并配置模型服务。AI 预审不替代法定审查和专业人员签字。

## 复现

```bash
conda env create -f environment.yml
conda activate archmind
make verify
python -B submissions/os2026/demo.py input
python -B submissions/os2026/demo.py review
python -B submissions/os2026/demo.py evidence
python -B submissions/os2026/demo.py gate
make demo
make build
```

源码采用 `AGPL-3.0-only`；第三方依赖见仓库 `THIRD_PARTY_NOTICES.md`。贡献方式见 `CONTRIBUTING.md`。Release 附件提供 SHA-256 校验清单。

官方规则来源：[2026 上海开源软件应用创新大赛](https://www.oschina.net/os2026/)，核对日期 2026-10-13。此发布提供参赛材料，不代表已向组委会完成提交。
