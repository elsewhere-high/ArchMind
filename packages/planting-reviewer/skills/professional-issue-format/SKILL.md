---
name: professional-issue-format
description: 将专业发现转换为统一、可验证的结构化 issue；证据不足时强制使用 insufficient_evidence。
---

# professional-issue-format

## Purpose
把专业判断转换为 `docs/issue-schema.json` 定义的结构化问题，保证证据、边界和人工确认门一致。

## Inputs
- 专业事实清单
- 当前专业审查发现
- `docs/issue-schema.json`

## Outputs
符合 Schema 的 JSON 数组。证据不足时 `status="insufficient_evidence"`，`risk_level="undetermined"`，并提供非空 `missing_information`。

## Invocation conditions
专业 Worker 完成事实分析后、向 Team Leader 报告前调用。

## Dependencies
依赖 `extract-review-context` 的事实编号和统一 Issue Schema。

## Failure handling
不能定位图号/位置或没有输入证据时不得写成确定问题；改为证据不足，或明确拒绝输出。

## Validation
字段完整；`confidence` 在 0~1；不伪造规范编号/条款；专业不越界；每条 evidence 可回指输入。

## Security boundary
不执行代码、不访问网络、不读取凭据；不替代法定审查和人类总工签字。

## Reuse value
让多专业输出可聚合、可比较、可审计。

## Version
1.0.0
