# 开发与验证

在项目目录中运行：

```bash
conda activate archmind
make verify
make demo
make build
```

`make verify` 检查源码凭据、公共数据边界、Markdown 链接、技能与部署结构、资源渲染、七次技能记录的合成流程、人工确认约束及 Schema。源码检查只跳过根 Git 元数据，嵌套 Git 和环境文件仍禁止进入交付包。

对导出的发布目录执行严格检查：

```bash
python -B tests/validate-final-secret-scan.py --root <export-directory>
```

此模式禁止包含 Git、凭据文件、环境和缓存。打包产物应解压到项目外检查；每个角色 ZIP 包含清单、项目许可元数据、技能、专业意见 Schema、LICENSE 和第三方声明。

修改技能定义或合成输入后，必须同步角色包的技能副本、技能合同中的 definition_sha256、授权输入引用哈希，以及输入不可变检查的校验清单。不得为了通过检查而改写真实运行证据。

Python 代码是命令行辅助脚本，不发布 Python wheel。构建对象为 AgentTeams 角色 ZIP；实际安装与模型执行依赖外部 AgentTeams 服务。
