# LoomQ 人工评分证据

这份文件是人工评分材料的统一入口。请直接编辑它，只填写要申报的项目。截图、原始结果或图表统一放在 `starter_kit/evidence/files/`，也可以引用 `starter_kit/` 中已有的代码和文档。

证据包是可选的。没有申报某项人工分时，留空即可，不影响自动评分。

## 提交前填写

把要申报项目的方框改成 `[x]`，并填写对应内容：

- [ ] L1 真机
- [x] L2 交互体验
- [x] 工程与产品化
- [x] 自定义量子 RISC-V Bonus
- [x] 新手引导与视觉叙事 Bonus

## L1 真机

每个有效真机平台计 5 分，最多两个平台。模拟器不计真机分。每个平台复制并填写一次下面的信息：

```text
平台名称：[填写]
平台 job ID：[填写]
运行时间：[填写，带时区]
shots：[填写]
实际执行的 QASM：[填写仓库内路径]
平台返回的原始结果：[填写仓库内路径]
任务页截图：[选填，填写仓库内路径]
```

建议把文件放进 `evidence/files/`，比如：

```text
evidence/files/spinq-circuit.qasm
evidence/files/spinq-result.json
evidence/files/spinq-screenshot.png
```

工作人员会核对 job ID、运行时间、电路、shots 和原始结果。截图只能辅助说明，不能代替 job ID 和原始结果。

## L2 交互体验

请填写：

```text
启动界面或 CLI 的命令：python3 -m starter_kit.loomq_cli --help
测试入口或页面地址：无，使用仓库内 CLI
用于交互体验评测的 3 个用户任务：
1. 运行 `python3 -m starter_kit.loomq_cli ask --target spinq --shots 1024 生成一个三比特 GHZ 态并测量所有量子比特`，一次获得经过目标态验证的 QASM、运行结果和解释。
2. 运行 `python3 -m starter_kit.loomq_cli chat 修复下面用于制备 Bell 态的代码：H q[0]; CX q[0] q[1]`，观察错误代码如何恢复为完整程序。
3. 运行 `python3 -m starter_kit.loomq_cli run --target spinq --shots 1024 starter_kit/circuits/bell.qasm`，阅读文本柱状图与位序提示。
截图或演示视频：无；所有流程均由最终 commit 中的代码直接运行。
```

工作人员会在组委会统一模型环境中运行最终代码，测试新手是否看得懂、出错后能否得到有效帮助、结果是否清楚，以及多轮回答是否一致。选手自己的对话截图只用于说明产品流程，不直接证明得分。

## 工程与产品化

已有内容可以直接引用主 README 或其他项目文档，不必复制到本目录。

```text
干净环境中的构建和启动命令：`python3 starter_kit/verify_submission.py`；完整命令见 starter_kit/README.md 的“干净环境验证”
架构说明：starter_kit/ARCHITECTURE.md
目标用户和使用场景：会描述问题但没有学习 QASM、也不了解厂商 SDK 差异的普通开发者和跨界创作者；用于第一次生成、修复、转译并理解量子电路。
完整使用流程：starter_kit/README.md 的“零基础首次运行”和“使用自然语言 Agent”
```

工作人员会按最终 commit 实际构建和启动，并检查文档与代码是否一致、产品是否真的降低了量子计算的使用门槛。

## 自定义量子 RISC-V Bonus

以下三项必须齐全且测试通过，才获得 8 分：

```text
指令编码规格：starter_kit/QUANTUM_RISCV_SPEC.md
模拟器扩展实现：starter_kit/loomq/quantum_riscv.py 与 starter_kit/riscv_emulator.py
端到端测试命令：`python3 starter_kit/bonus_evaluator.py`（完整开发测试：`python3 -m unittest tests.test_quantum_riscv -v`）
```

## 新手引导与视觉叙事 Bonus

请填写已有材料的路径，不要求为评分另写一套文档：

```text
零基础首次运行指南：starter_kit/README.md 的“零基础首次运行”
量子概念解释：starter_kit/README.md 的 Bell 结果解释，以及 starter_kit/QUANTUM_101.md
结果可视化：starter_kit/loomq_cli.py 的文本柱状图；运行命令见本文件 L2 第 3 个任务
错误恢复或无障碍引导：starter_kit/loomq/agent.py 的确定性 QASM 校验和诊断重试；CLI 错误以中文输出且不显示 traceback
```

以上四项各 1 分。普通项目 README 完整不代表自动获得 Bonus。

## 提交规则

- 所有材料都要在截止前进入最终提交的 commit，工作人员不接受截止后补交。
- 外部视频可以用稳定只读链接，源码、原始结果和复现命令应保存在仓库中。
- 整个 fork commit 的归档包不得超过 100 MiB。
- 不要提交 API Key、Token、Cookie、个人身份信息或平台账户隐私。
- 如申报 L1 真机分，在最终提交 Issue 的 `Hardware evidence` 中填写 `starter_kit/evidence/README.md`。
