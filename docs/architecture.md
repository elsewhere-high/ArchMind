# 系统结构

Manager 负责分派与完整性检查；review-coordinator 组织园建、植物和雨水海绵三个独立 Reviewer，再把结果交给 evidence-verifier 核验，最后交由人类总工处置。

输入是明确授权的结构化 Drawing Facts。事实、专业意见、跨专业关系、核验结果和人工决策分别保存。当前源码没有 CAD/BIM/OCR 解析器，也没有图形界面。

AgentTeams 是外部运行平台；角色包由 packages 中的清单与声明式技能组成。模型、容器、Matrix、对象存储需由运行环境提供。心跳默认关闭。
