# 数据契约与命令行工具

## 数据

- `schemas/drawing-facts-v0.1.schema.json`：结构化工程事实交换契约。
- `docs/issue-schema.json`：专业意见，包含事实引用、专业范围、结论与人工确认标记。
- `schemas/human-decision-v0.1.schema.json`、`v0.2`：人工决定的不同协议版本。
- `schemas/run-state-v0.1.schema.json`：业务审批状态。
- `samples/skill-evidence/00_contracts/`：七次技能使用及其证据链的最小契约。

Schema 和协议版本独立于 ArchMind 的发布版本。现有人工审批协议固定使用 `run-002-human-gate`，部分事项 ID 使用 `HCI-R2-*`；这些是数据格式标识，不代表本项目已经产生运行记录。技能示例同样保留协议要求的固定 run/task ID。

## 工具

以下命令均在激活 `archmind` Conda 环境后执行。参数详见各脚本 `--help`。

```bash
python -B scripts/validate-schemas.py
python -B scripts/validate-run002-gate.py --state <state.json> --human-items <items.json> --decisions <decisions.json>
python -B scripts/normalize-run002-human-items.py --input <raw-items.json> --output <new-items.json> --task-id <task-id>
python -B scripts/record-skill-use-min-001.py --help
python -B scripts/validate-skill-evidence-min-001.py --run-root <actual-run-directory>
```

规范化工具只写新文件，拒绝覆盖；它不批准任何事项。状态校验器检查计数、人工责任和完成状态的一致性，但不会连接 Matrix 验证消息真实性，来源认证由实际 Runtime 的接收流程负责。

七次完整技能记录必须包含真实可核查的输入、输出、定义快照、工具证据及哈希。当前示例只有输入准备，没有实际调用记录，直接做完整证据校验应失败。合成测试的临时记录只用于验证工具行为，不能作为真实审查或技能调用证据。
