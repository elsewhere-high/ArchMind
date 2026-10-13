# 2026 上海开源软件应用创新大赛

参赛作品：ArchMind 多专业工程设计预审工具。赛道：AI+ 工业软件；方向：建筑领域的研发设计与签字前内部预审；采用自主选题。

## 提交入口

- [公开代码仓库](https://github.com/elsewhere-high/ArchMind)
- [参赛 Release](https://github.com/elsewhere-high/ArchMind/releases/tag/v0.1.0-os2026)
- [作品介绍 PDF](https://github.com/elsewhere-high/ArchMind/releases/download/v0.1.0-os2026/ArchMind-OS2026-Introduction.pdf)
- [中文演示视频 MP4](https://github.com/elsewhere-high/ArchMind/releases/download/v0.1.0-os2026/ArchMind-OS2026-Demo.mp4)

## 官方说明核对

核对日期：2026-10-13。来源：[大赛官网](https://www.oschina.net/os2026/)。

官网明确列出建筑领域；工业软件赛道接受用 AI 解决工程、流程或决策问题的开源项目。材料包括完整可运行代码仓库链接、介绍文档和核心功能演示视频。评审权重为技术创新 30%、场景落地 30%、开源治理 20%、长期发展 20%。官网允许真实或仿真环境的验证数据。

官网截止时间为 2026 年 10 月 16 日 24:00（北京时间）；报名确认后的材料提交按确认邮件及官网指引办理。此目录准备材料，不代表已完成报名或向组委会提交。

## 演示范围

视频为真实命令执行结果的可读性回放，配有中文合成语音和字幕。画面不是产品图形界面；显示的专业意见和跨专业关系来自仓库预写的合成回归数据，不是本次新生成的模型输出。演示中的人工确认拦截在临时合成状态文件上运行，不创建真实人工决定，不修改业务状态。

录制内容依次为：输入事实检查、三专业意见与证据引用、跨专业关系和缺失资料、人工确认状态拦截、离线评估、五个角色包构建及复现方式。完整命令、退出码与输出保存在发布附件的验证记录中。

## 本地复现

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

`demo.py` 只使用标准库。它读取现有合成数据并调用现有状态校验器，不依赖模型服务。PDF 与视频的重建使用同一 Conda 环境，额外安装本目录 `requirements-media.txt` 中的依赖。媒体脚本需要中文 TrueType 字体；默认使用 macOS 黑体。其他系统可通过 `--font` 和 `--font-bold` 指定有权使用的简体中文字体。视频语音依赖 macOS `say` 的 Tingting 声音。

```bash
python -m pip install -r submissions/os2026/requirements-media.txt
python -B submissions/os2026/build_materials.py
```

成品写入 `output/pdf/`、`output/video/` 和 `output/submission/`；音频与编码临时文件使用系统临时目录，不进入 Git。

## 当前状态与后续计划

已实现角色和技能定义、结构化数据契约、证据工具、人工确认一致性校验、离线评估、角色包构建和 Runtime 配置脚本。真实模型运行需要另行部署 AgentTeams v1.2.1、容器服务、Matrix、对象存储并配置模型凭据。

后续按证据充分性推进：先完成真实 Runtime 全链路验证与专家标注基准，再扩展授权 CAD/BIM 数据适配和审查界面。尚无生产部署、审查准确率或节时比例的验证数据，不作量化效果承诺。
