---
name: evidence-verification
description: 核验专业问题是否由输入事实支持、是否越界、是否矛盾，并识别必须交给 Human 的事项。
---

# evidence-verification

## Purpose
对已有专业问题和跨专业结果做证据审计；不重新做专业审查。

## Inputs
- 原始授权输入
- 三个专业结果
- 跨专业结果
- Issue Schema

## Outputs
JSON：`verified_issues`、`insufficient_evidence_issues`、`rejected_issues`、`boundary_findings`、`conflicts`、`human_confirmation_items`。每项给出理由与引用。

## Invocation conditions
专业输出与跨专业检查完成后，由 `evidence-verifier` 独立调用。

## Dependencies
依赖原始事实和上游结构化输出；不得依赖 Worker 的隐藏推理或未保存消息。

## Failure handling
无法回指事实、图号/位置不明、引用依据不在输入中时，降为 `insufficient_evidence`；明确列出 `missing_information`，不得补写。

## Validation
至少抽查一条证据充分问题和一条证据不足问题；检查专业越界、矛盾、重复与 Human 门。

## Security boundary
不访问凭据或网络；不修改专业原始结果；不代替人类总工确认和签字。

## Reuse value
为任何高责任多 Agent 工作流提供独立证据门。

## Version
1.0.0
