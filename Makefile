SHELL := /bin/sh

.DEFAULT_GOAL := help
.PHONY: help verify demo build runtime-preflight runtime-up runtime-health runtime-down

help:
	@printf 'ArchMind 0.1.0 — 多专业工程预审\n'
	@printf '  make verify             本地测试与安全检查\n'
	@printf '  make demo               合成样例离线评估（不调用模型）\n'
	@printf '  make build              构建五个 AgentTeams 角色包\n'
	@printf '  make runtime-preflight  检查真实运行环境\n'
	@printf '  make runtime-up         配置就绪后准备 AgentTeams 资源\n'
	@printf '  make runtime-health     检查资源与服务健康\n'
	@printf '  make runtime-down       停止本项目 Agent Runtime\n'

demo:
	@test -n "$$CONDA_PREFIX" || { printf 'Activate the ArchMind Conda environment\n'; exit 1; }
	PYTHONDONTWRITEBYTECODE=1 python3 evaluation/score_baseline.py --build-dataset

build:
	sh scripts/build-packages.sh

verify:
	sh scripts/verify-final-package.sh

runtime-preflight:
	sh scripts/runtime-preflight.sh --pre-build

runtime-up:
	sh scripts/bootstrap-runtime.sh

runtime-health:
	sh scripts/runtime-healthcheck.sh

runtime-down:
	sh scripts/runtime-down.sh
