# LoomQ 人工评分证据

这份文件是人工评分材料的统一入口。请直接编辑它，只填写要申报的项目。截图、原始结果或图表统一放在 `starter_kit/evidence/files/`，也可以引用 `starter_kit/` 中已有的代码和文档。

证据包是可选的。没有申报某项人工分时，留空即可，不影响自动评分。

## 提交前填写

把要申报项目的方框改成 `[x]`，并填写对应内容：

- [x] L1 真机
- [x] L2 交互体验
- [x] 工程与产品化
- [x] 自定义量子 RISC-V Bonus
- [x] 新手引导与视觉叙事 Bonus

## L1 真机

每个有效真机平台计 5 分，最多两个平台。模拟器不计真机分。每个平台复制并填写一次下面的信息：

```text
平台名称：本源量子云 — 本源悟空 180
平台 job ID：9D182FA1EF76FF3807697CDF69DE7483
运行时间：2026-08-24 04:34:05.914 至 04:35:07.744（平台页面显示时间；提交浏览器所在时区为 UTC+8）
shots：1000
实际执行的 QASM：starter_kit/evidence/files/originq-bell.qasm
平台返回的原始结果：starter_kit/evidence/files/originq-result.json
平台实际 OriginIR：starter_kit/evidence/files/originq-bell.originir
任务页截图：starter_kit/evidence/files/originq-task.jpg
```

任务状态为“计算成功”，实际映射到 `q[157]`、`q[166]`。真机 counts 为 `00=482, 01=18, 10=24, 11=476`；Bell 理想主峰 `00/11` 共 958/1000 shots（95.8%）。JSON 中的数值逐项抄录自已登录的任务详情页；截图保留了可追溯任务元数据和结果主峰。

```text
平台名称：SpinQ Cloud — 2 比特核磁量子计算机
平台 job ID：G-260824-0001（任务页 ID：61458）
运行时间：2026-08-24 05:17:01 至 05:18:36（平台页面显示时间；提交浏览器所在时区为 UTC+8）
结果类型：投影概率（核磁平台不返回 shots counts）
实际执行的 QASM：starter_kit/evidence/files/spinq-bell.qasm
平台返回的原始结果：starter_kit/evidence/files/spinq-result.msgpack
原始结果的无损 JSON 解码：starter_kit/evidence/files/spinq-result.json
任务页截图：starter_kit/evidence/files/spinq-task.jpg
```

任务状态为“运行成功”，平台明确标记为“2比特核磁量子计算机”。平台下载的原始 MessagePack 投影概率为 `00=0.42313008, 01=0.24553040, 10=0.08580911, 11=0.24553040`；Bell 理想峰 `00/11` 合计 `0.66866048`，全局主峰为理想态 `00`。核磁真机结果受噪声与标定偏差影响，因此这里只申报平台可追溯的实际结果，不把它描述为理想双峰或高保真结果。

### 真机证据完整性与统计复核

```bash
python3 -m starter_kit.scripts.validate_hardware_evidence
```

`hardware-analysis.json` 从上述原始文件确定性重算：本源理想支持集命中率为 0.958，Wilson 95% 区间为 `[0.9437156, 0.9687791]`；SpinQ 的结果是投影概率而非 shots，因此只报告理想支持集概率 `0.66866048` 和相对理想 Bell 分布的总变差距离 `0.331339515`，不伪造置信区间。`manifest.json` 记录全部原始材料、截图与派生分析的字节数和 SHA-256；验证器还会检查赛程时间窗、QASM 语义、counts 求和、JSON/MessagePack 无损一致性以及文件篡改。

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
启动界面或 CLI 的命令：`python3 -m starter_kit.loomq.web`（CLI 备用入口：`python3 -m starter_kit.loomq_cli --help`）
测试入口或页面地址：http://127.0.0.1:8765/
用于交互体验评测的 3 个用户任务：
1. 在 Web 首页选择“Bell 纠缠”，点击“运行电路”，观察 q[0]/q[1] 门时间线、`00`/`11` 概率、位序解释和 SpinQ 原生指令。
2. 切换“均匀叠加”和 Braket，比较 8 个等概率基态，并展开 OpenQASM 3.0 目标指令。
3. 配置 `LOOMQ_LLM_*` 后在页面输入“生成三比特 W 态并测量”，观察 Agent 回答经过门集、语法和目标分布验证；未配置时页面给出具体环境变量提示且不显示凭据。
截图或演示视频：桌面 `starter_kit/evidence/files/web-lab-desktop-current.jpg`，移动端 `starter_kit/evidence/files/web-lab-mobile-current.jpg`；完整验收矩阵见 `starter_kit/WEB_QA.md`。所有流程均由最终 commit 中的代码直接运行。
```

工作人员会在组委会统一模型环境中运行最终代码，测试新手是否看得懂、出错后能否得到有效帮助、结果是否清楚，以及多轮回答是否一致。选手自己的对话截图只用于说明产品流程，不直接证明得分。

### L2 压力测试能力

可复现入口：`python3 -m starter_kit.scripts.l2_stress_campaign --dry-run`；真实模型运行、断点续跑与证据校验命令见 `starter_kit/L2_STRESS_CAMPAIGN.md`。固定语料共 500 例：生成 150、修复 150、后端推荐 120、对抗输入 50、稳定性 30。

本仓库只在真实 `LOOMQ_LLM_*` 服务实际完成后才会提交模型结果 JSONL/summary。没有真实凭据或只运行本地 fake server 时，不把协议测试写成真实 DeepSeek 成绩，也不声称替代组委会私有评测。

## 工程与产品化

已有内容可以直接引用主 README 或其他项目文档，不必复制到本目录。

```text
干净环境中的构建和启动命令：`python3 starter_kit/verify_submission.py`；Web：`python3 -m starter_kit.loomq.web`；完整命令见 starter_kit/README.md 的“干净环境验证”
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
结果可视化：starter_kit/web/ 的响应式电路时间线与概率图，以及 starter_kit/loomq_cli.py 的文本柱状图
错误恢复或无障碍引导：starter_kit/loomq/agent.py 的确定性 QASM 校验和诊断重试；Web 提供 Learn、Build、Repair、Backend Match 四条路径，并使用跳转链接、语义结果表、错误 `role=alert`、键盘焦点、`aria-live`、移动端断点和减少动画偏好
```

以上四项各 1 分。普通项目 README 完整不代表自动获得 Bonus。

## 提交规则

- 所有材料都要在截止前进入最终提交的 commit，工作人员不接受截止后补交。
- 外部视频可以用稳定只读链接，源码、原始结果和复现命令应保存在仓库中。
- 整个 fork commit 的归档包不得超过 100 MiB。
- 不要提交 API Key、Token、Cookie、个人身份信息或平台账户隐私。
- 如申报 L1 真机分，在最终提交 Issue 的 `Hardware evidence` 中填写 `starter_kit/evidence/README.md`。
