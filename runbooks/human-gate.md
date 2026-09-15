# 人工确认协议

实际人工决策必须来自指定 chief-engineer 身份在指定 Matrix 房间中的消息，并保存可核查的来源。

## Ordered states

`CREATED → RUNNING → PROFESSIONAL_REVIEW → CROSS_DISCIPLINE_REVIEW → EVIDENCE_VERIFYING → WAITING_HUMAN`

After a real HumanDecision, processing may enter `RESUMED`, `REVIEW_REJECTED`, `BLOCKED_FOR_EVIDENCE`, or `RERUN_REQUIRED`. `COMPLETED` is legal only when every Human-required item has a terminally processed outcome, `unprocessed_human_required_items = 0`, and `human_gate_closed = true`.

`REQUEST_MORE_EVIDENCE` with missing material keeps the total task incomplete in `BLOCKED_FOR_EVIDENCE`. `RERUN` is PARTIAL/BLOCKED unless the original result, Human reason, redispatch, new result, and renewed evidence verification are all preserved.

## Human stop rule

When Evidence Verifier output and Human Items exist, Manager must:

1. write `run-state.json` with `status = WAITING_HUMAN`;
2. write the Human Items and a waiting-state snapshot;
3. send the Human action request to the Matrix room;
4. not generate the final review summary;
5. not set the task to completed; and
6. perform no further automatic state transition until a real `chief-engineer` message is received.

No timer, default, keyword shortcut, script, Admin proxy, or agent may manufacture a HumanDecision.

## HumanDecision wire format

For `run-002-human-gate`, the Human posts one fenced JSON object per decision, conforming to `schemas/human-decision-v0.2.schema.json`. Version v0.2 retains the v0.1 decision semantics, authorization boundary, required fields, and state-transition constraints while accepting both historical `HCI-001` identifiers and the canonical Run-002 identifiers `HCI-R2-001` through `HCI-R2-012`. The receiving Manager preserves the original Matrix event, saves the normalized decision separately, and never records passwords, access tokens, API keys, or hidden reasoning.

## Skill-call evidence

Each actual call record must contain: `run_id`, `task_id`, `agent_id`, `skill_name`, `skill_version`, `started_at`, `completed_at`, `input_reference`, `output_reference`, `status`, `error`, and reliable `latency_ms` when available. A Skill file merely being installed is not invocation evidence.

Required actual calls:

- each professional reviewer: `extract-review-context` and `professional-issue-format`;
- Team Leader: `cross-discipline-conflict-check` and, after verification, `review-summary` for the Human-facing pre-summary only;
- Evidence Verifier: `evidence-verification`.

## Context-transfer evidence

Preserve real Matrix event references and/or shared-file hashes for Manager → Team Leader, Team Leader → Reviewer, Reviewer → Team Leader, Team Leader → Evidence Verifier, Manager → Human, and Human → Manager/task. Never create a context-transfer record for an exchange that did not occur.
