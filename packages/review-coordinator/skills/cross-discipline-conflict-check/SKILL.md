---
name: cross-discipline-conflict-check
description: 对多个专业的独立输出做关联检查，识别共享位置、共享构件和相互矛盾的控制条件。
---

# cross-discipline-conflict-check

## Purpose
识别专业输出之间的真实关联或冲突，不把多条意见简单拼接成“跨专业问题”。

## Inputs
- 至少两个专业 Worker 的结构化结果
- 原始事实编号索引
- Team 任务目标

## Outputs
JSON：`cross_issue_id`、`location`、`involved_issue_ids`、`involved_disciplines`、`shared_evidence`、`relationship`、`coordination_action`、`requires_human_review`、`confidence`。

## Invocation conditions
Team Leader 收齐至少两个专业结果后调用；缺少第三专业结果时需显式说明范围。

## Dependencies
依赖各专业符合统一 Schema 的输出；不依赖外部 MCP。

## Failure handling
只有位置相同但没有因果/空间/控制关系时，不判为冲突；标记 `no_verified_relationship`。证据不足则列缺失资料。

## Validation
每个跨专业关系至少引用两个不同专业的 issue_id 和对应事实；协调行动不能替代任一专业最终判断。

## Security boundary
只处理本任务内的结构化结果；不扩展到真实项目、外部知识库或凭据。

## Reuse value
可复用于多专业会签、碰撞总审和证据去重。

## Version
1.0.0
