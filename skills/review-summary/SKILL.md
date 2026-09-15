---
name: review-summary
description: 将已核验证据的专业问题和跨专业关系汇总为提交人类总工确认的综合预审意见。
---

# review-summary

## Purpose
形成清晰、去重、可追溯的综合审核意见，并显式保留未闭合事项与 Human 确认门。

## Inputs
- 三个专业结果
- 跨专业结果
- Evidence Verifier 结果
- 任务状态和参与角色

## Outputs
Markdown：资料摘要、已核验问题、证据不足事项、跨专业协调、未闭合事项、建议处置、Human 确认清单、免责声明。

## Invocation conditions
Evidence Verifier 完成后，由 Team Leader 汇总；Manager 只能检查完整性并提交 Human，不得新增专业结论。

## Dependencies
依赖已保存的结构化结果与证据核验文件。

## Failure handling
核验结果缺失或存在未解释矛盾时不得宣告完成；列为未闭合事项并请求 Human/上游补充。

## Validation
每个纳入摘要的问题可追溯到 issue_id；证据不足项不得包装成确定结论；列出谁审、谁核、谁确认。

## Security boundary
不写入 API Key、密码、隐藏推理或未授权数据；输出不替代法定审查及总工签字。

## Reuse value
可复用于景观多专业预审、复审前汇总和审查档案生成。

## Version
1.0.0
