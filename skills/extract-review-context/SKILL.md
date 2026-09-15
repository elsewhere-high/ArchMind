---
name: extract-review-context
description: 从指定项目资料中提取与当前专业直接相关、可追溯的事实，不补写缺失信息。
---

# extract-review-context

## Purpose
将项目资料压缩为当前专业可使用的事实清单，并保留来源、事实编号、图号和位置。

## Inputs
- 明确列出的项目资料路径
- 当前专业名称与审查范围
- 可选任务 ID

## Outputs
JSON 事实数组；每项含 `fact_id`、`source`、`drawing_reference`、`location`、`quoted_fact`、`relevance`。另列 `missing_inputs`。

## Invocation conditions
任何专业审查开始前调用；只读取任务明确授权的输入，不读取验收答案或其他项目资料。

## Dependencies
无外部服务；仅依赖任务目录内的 Markdown/JSON 文本。

## Failure handling
文件缺失、JSON 无效或专业范围不明时停止提取，报告具体路径和缺失项，不猜测。

## Validation
每个事实必须能逐字或等义回指输入；随机抽查 `fact_id` 必须唯一且真实存在。

## Security boundary
不得读取凭据、环境变量、其他项目目录、真实生产图纸或未授权文件；不得输出敏感信息。

## Reuse value
可复用于园建、植物、雨水海绵及后续其他专业的文本资料接入。

## Version
1.0.0
