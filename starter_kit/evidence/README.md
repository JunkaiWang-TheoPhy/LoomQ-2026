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

### 评分快速索引

| 官方人工评分项 | 本 fork 申报 | 首要可复核证据 |
|---|---:|---|
| L1 真机 | 10/10 分上限 | 下方两个平台的 job ID、原始结果、QASM、截图；`python3 -m starter_kit.scripts.validate_hardware_evidence` |
| L2 交互体验 | 10/10 分上限 | 下方 3 个用户任务、可下载并重算的 Witness Chain、反事实首门分歧、ProofTrace 证书、P1 断言、P2 Hybrid 回放、Hybrid 路径证书、三算法画廊、逐门状态故事、受限多轮上下文、`starter_kit/WEB_QA.md`、桌面/移动端截图、22 项 Web 测试 |
| 工程与产品复核 | 10/10 分上限 | `starter_kit/JUDGE_GUIDE.md`、`ARCHITECTURE.md`、零依赖启动、`python3 starter_kit/verify_submission.py` |
| 自定义量子 RISC-V | 8/8 分上限 | `starter_kit/QUANTUM_RISCV_SPEC.md`、扩展模拟器、`bonus_evaluator.py` |
| 新手引导与视觉叙事 | 4/4 分上限 | Learn/Build/Repair/Backend Match、双通道结果表达、错误恢复和键盘/移动端支持 |

“申报上限”表示材料按满项要求提交，最终得分仍由组委会复核；本表不把公开自测表述成官方成绩。

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
启动界面或 CLI 的命令：`python3 -m starter_kit.loomq.web`（逐门 CLI：`python3 -m starter_kit.loomq_cli trace starter_kit/circuits/bell.qasm`）
测试入口或页面地址：http://127.0.0.1:8765/
用于交互体验评测的 3 个用户任务：
1. **Learn + Counterfactual Build**：选择“第一次理解量子电路”，运行 Bell 后观察 H/CX 时间线、`00`/`11` 概率图和文本表；进入 Counterfactual Circuit Lab 比较默认反例，确认系统定位第 2 扇门、显示 `CX` 对 `X`、最大振幅差 `0.707107` 与 TV 距离 `0.500000`，再自行删改一扇门重试。
2. **Repair**：点击“修复一段错误 QASM”，页面预填含越界 `cx q[0],q[2]` 的 Bell 修复任务；配置 `LOOMQ_LLM_*` 后提交，检查返回完整 OpenQASM 2.0，并确认语法、白名单门与 Bell 分布通过确定性校验，错误回答会携带诊断重试一次。
3. **Backend Match + Judge Evidence**：点击“选择合适的后端”，把任务改为“推荐一个免费、零排队、至少 20 比特的模拟器后端”；回答必须包含能力表中的兼容规范 ID。随后在同一页打开 P1 断言面板，检查 exact-local / finite-shot / provider-probabilities 三种证据标签与“不归因具体噪声机制”提示，再在 P2 Hybrid 面板核对 `branch_path`、`machine_jump_taken`、`source_condition_true` 与寄存器增量，并在 Hybrid 路径证书中确认可达路径概率与零概率不可达投影分离。
截图或演示视频：首屏桌面 `starter_kit/evidence/files/web-lab-desktop-current.jpg`，移动端 `starter_kit/evidence/files/web-lab-mobile-current.jpg`；反事实结果桌面 `starter_kit/evidence/files/counterfactual-desktop.jpg`，移动端 `starter_kit/evidence/files/counterfactual-mobile.jpg`；完整验收矩阵见 `starter_kit/WEB_QA.md`。所有流程均由最终 commit 中的代码直接运行。
```

默认 Bell 例还提供一键审计动作：点击“生成统一审计链”，`loomq-witness-chain-v1` 会把反事实 `g2`、断言 `m1/m2`、Hybrid 分支 `m2` 与 ProofTrace source lineage 对齐。下载 JSON 后可按 `starter_kit/WITNESS_CHAIN.md` 使用 `verify_causal_audit()` 重算；摘要用于发现篡改，不冒充作者签名或真机物理证明。

工作人员会在组委会统一模型环境中运行最终代码，测试新手是否看得懂、出错后能否得到有效帮助、结果是否清楚，以及多轮回答是否一致。选手自己的对话截图只用于说明产品流程，不直接证明得分。

### L2 压力测试能力

可复现入口：`python3 -m starter_kit.scripts.l2_stress_campaign --dry-run`；真实模型运行、断点续跑与证据校验命令见 `starter_kit/L2_STRESS_CAMPAIGN.md`。固定语料共 500 例：生成 150、修复 150、后端推荐 120、对抗输入 50、稳定性 30。

本仓库只在真实 `LOOMQ_LLM_*` 服务实际完成后才会提交模型结果 JSONL/summary。没有真实凭据或只运行本地 fake server 时，不把协议测试写成真实 DeepSeek 成绩，也不声称替代组委会私有评测。

归档内 `tests.test_web.WebLabTests.test_web_agent_end_to_end_covers_generation_repair_and_backend_tasks` 使用本地 OpenAI-compatible HTTP fixture 验证 Web API、模型协议、三类任务路由和确定性结果校验的完整网络链路；fixture 只证明工程链路，不记作真实模型成绩。

`cd starter_kit && python3 -m unittest tests.test_l2_qualification -v` 进一步执行 12 个私有集同形任务：8 个生成/修复任务分别观察两次 HTTP Chat Completions 请求，并用独立 `adapter.run()` counts 判定 Bell、GHZ、W、均匀叠加和计算基态；4 个后端任务分别观察一次请求并核对规范能力 ID。主链共 20 个协议请求；附加测试再让后端模型连续错误两次，确认两次调用后才由官方能力表约束求解器返回兼容 ID。模型字段、零温度和关闭 thinking 均被断言。`tests.test_l2_stress_campaign` 还对全部 500 例固定语料注入两次无效 completion：观察到恰好 1000 次回调，500/500 最终回答均通过同一确定性验证器；这项核心逻辑压测不冒充 500 例完整 HTTP 协议测试。fixture 仍不等于真实 DeepSeek，也不申报私有 12 例得分。

### 独立数值 Oracle

PyQuafu 0.4.5 的固定种子验证覆盖 40 个唯一电路、全部 12 门和三个 target，共 120/120 项通过；最大状态向量振幅误差为 `1.1802326323952682e-15`。协议、counts 浮点余数 tie 边界和复现命令见 `starter_kit/PYQUAFU_CROSS_VALIDATION.md`，摘要见 `starter_kit/evidence/files/pyquafu-cross-validation-summary.json`。它是软件交叉验证，不申报为第四个真机平台。

此外，公开 `transpile()` 不直接信任自己的 emitter：`loomq/native_ir.py` 会把三种输出重新解析成 `Circuit` 并做完全相等检查。Deutsch–Jozsa、Grover 与 QFT 三个展品均跨三 target 回读和运行；恶意资源输入由 `tests.test_resource_boundaries` 验证在分配前拒绝。P1 断言报告明确区分本地精确、有限 shots 与 provider 概率三类证据；P2 Hybrid 回放显示 bit 顺序 `c[0], c[1], …`、branch path 与机器寄存器事件，而 Hybrid 路径证书再把 exact measurement distribution 投影到分支路径、把零概率投影显式列为不可达，但这些工程证据都不外推成噪声归因。

ProofTrace 在此基础上增加可审计的安全重写、源门 lineage、优化 metrics 和三目标证书。`python3 -m starter_kit.scripts.prooftrace_benchmark --json` 对五个算法的三目标输出执行 225 个单指令删除变异，结果 225/225 检出、0 false accept，并完成 15 项 portability 与 132 项重写检查。范围和不能外推的结论见 `starter_kit/PROOFTRACE.md`。

### 40,000 项离线活动

`python3 -m starter_kit.scripts.offline_stress_campaign --validate` 校验固定摘要和语料哈希。实际活动为 3,000 项概率归一化、9,000 项三目标 IR/Schema、3,000 项量子 RISC-V 语义往返、20,000 项 L3 四输入差分执行，以及 QASM/机器码各 2,500 项拒绝检查；结果为 40,000/40,000。摘要位于 `starter_kit/evidence/files/offline-stress-summary.json`。每一项都有具体判据，失败会记录活动、case 和异常；该活动是公开工程证据，不替代官方隐藏评分。

## 工程与产品化

已有内容可以直接引用主 README 或其他项目文档，不必复制到本目录。

```text
干净环境中的构建和启动命令：`python3 starter_kit/verify_submission.py`；Web：`python3 -m starter_kit.loomq.web`；完整命令见 starter_kit/README.md 的“干净环境验证”
架构说明：starter_kit/ARCHITECTURE.md；60 秒评委索引：starter_kit/JUDGE_GUIDE.md；物理结论边界：starter_kit/SCIENTIFIC_CLAIMS_AUDIT.md
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
错误恢复或无障碍引导：starter_kit/loomq/agent.py 的确定性 QASM 校验、诊断重试与有界多轮历史；Web 提供 Learn、Build、Repair、Backend Match、反事实首门分歧、逐门状态故事和清空会话，并使用跳转链接、语义结果表、错误 `role=alert`、键盘焦点、`aria-live`、移动端断点和减少动画偏好
```

以上四项各 1 分。普通项目 README 完整不代表自动获得 Bonus。

## 提交规则

- 所有材料都要在截止前进入最终提交的 commit，工作人员不接受截止后补交。
- 外部视频可以用稳定只读链接，源码、原始结果和复现命令应保存在仓库中。
- 整个 fork commit 的归档包不得超过 100 MiB。
- 不要提交 API Key、Token、Cookie、个人身份信息或平台账户隐私。
- 如申报 L1 真机分，在最终提交 Issue 的 `Hardware evidence` 中填写 `starter_kit/evidence/README.md`。
