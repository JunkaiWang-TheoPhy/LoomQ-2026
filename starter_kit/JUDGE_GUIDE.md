# LoomQ 评委快速复核

这套材料解决的是一个很具体的问题：如果评委不会 QASM，也不想先读一堆实现细节，怎样在 90 秒内判断这份电路有没有被改坏、测量后的经典路径是不是说得清、自然语言入口在出错时会不会安全回退。

先点这 3 个按钮：

1. `1 分钟看证据`
2. `列出所有可能分支`
3. `修复一段错误 QASM`

先看这 3 个结果：

1. `ProofTrace：这次转译改了什么`
   会看到同一份电路如何落到 3 个目标平台，以及每一步可下载的证书入口。
2. `列出所有可能分支`
   会看到每条路径的概率、可达/不可达 outcome 和死路径。
3. `修复一段错误 QASM`
   会看到 Agent 先给出答案，再由本地规则检查语法、白名单门和目标分布。

有一个边界需要先说清：这些证据说明的是本地可重算的软件结论，不把差异归因到某种真实硬件噪声，也不把 SHA-256 当成身份签名。

## 90 秒走法

1. 打开页面后先点 `1 分钟看证据`，确认首屏问题清单已经出现。
2. 在默认 Bell 例子上点击 `运行电路`，展开 `ProofTrace：这次转译改了什么`。
3. 看 `已应用的可证明重写`、`三后端独立回读`，再点下载 JSON。
4. 回到证据区点击 `列出所有可能分支`，确认会出现路径概率、不可达 outcome 和死路径。
5. 点击 `修复一段错误 QASM`，看输入框是否自动填入修复任务，再检查失败时不会跳过本地校验。

`112` 是赛题各项相加的理论上限，不是本项目已获得的分数。私有 case、人工体验和真机可追溯性仍由组委会判定。

## 60 秒索引

| 区域 | 一条复核命令 | 主要证据 |
|---|---|---|
| 全部无凭据路径 | `python3 starter_kit/verify_submission.py` | 168 项归档回归、Node present 时执行前端语法检查，否则显式 `SKIP`、Web/API/assert/compare/hybrid/witness 焦点套件、ProofTrace、L2 固定语料、真机 manifest、L1/L3/RISC-V |
| ProofTrace 证明 | `cd starter_kit && python3 -m scripts.prooftrace_benchmark --json` | 225/225 native-IR 删除变异检出、15 项 portability、132 项安全重写；固定 corpus SHA-256 |
| Web 因果学习与 P1/P2 证据 | `cd starter_kit && python3 -m unittest tests.test_web -v` | 27 项 Web 集成测试覆盖首屏证据导航、`/api/causal-audit` Witness Chain、`/api/compare` 首门分歧与结构拒绝、`/api/assert`、`/api/hybrid-trace`、ProofTrace、favicon 与移动端防溢出样式 |
| 离线压力证据 | `python3 -m starter_kit.scripts.offline_stress_campaign --validate` | 40,000/40,000 项、六条断言通道、固定语料 SHA-256 |
| L1 三目标 | `python3 starter_kit/evaluator.py --level l1 --target spinq,originq,braket` | 统一 Circuit IR、12 门 × 3 target 归档测试 |
| L1 语义回读 | `cd starter_kit && python3 -m unittest tests.test_native_ir_verifier -v` | SpinQ QASM 2、OriginIR、Braket QASM 3 独立 parser；篡改门负例 |
| 算法画廊 | Web 点击 Deutsch–Jozsa / Grover / QFT，或运行 `tests.test_algorithm_gallery` | `11=100%`、`111=94.53125%`、QFT 等概率但多相位 |
| L1 独立数值 oracle | `python3 -m starter_kit.scripts.quafu_cross_validate --validate` | `PYQUAFU_CROSS_VALIDATION.md`；真实 PyQuafu 0.4.5 的 120/120 摘要 |
| L1 两平台真机 | `python3 -m starter_kit.scripts.validate_hardware_evidence` | OriginQ、SpinQ job ID，provider 原始结果、截图、统计分析和 SHA-256 manifest |
| L2 客观路径 | 正式环境执行 `python3 starter_kit/evaluator.py --level l2` | 环境注入模型、能力表 grounding、语法/门集/目标分布校验、一次诊断重试；两次无效回答后用同一确定性判据安全回退 |
| L2 资格链 | `cd starter_kit && python3 -m unittest tests.test_l2_qualification -v` | 12 个私有集同形任务的 20 次本地 HTTP 请求；另以 2 次错误后端回答证明调用后约束回退；8 组独立 counts、4 个规范 ID；协议 fixture 不申报真实 DeepSeek 成绩 |
| L2 鲁棒性工具 | `python3 -m starter_kit.scripts.l2_stress_campaign --dry-run` | 500 个唯一生成/修复/推荐/对抗/稳定性 case；注入式 completion 最坏路径连续返回 1000 次无效内容，500/500 case 仍由确定性验证器安全恢复；完整 HTTP payload 契约另由 12 例资格链断言，没有凭据时不伪造真实模型成绩 |
| L2 体验 | `python3 -m starter_kit.loomq.web` | Learn / Build / Repair / Backend Match、反事实电路实验、ProofTrace 证书下载、P1 断言报告、P2 Hybrid 分支回放、逐门状态故事、受限多轮上下文、桌面/移动端验收、`WEB_QA.md` |
| 统一 Witness Chain | Web 默认 Bell 例点击“生成统一审计链” | `g2 → m1/m2 → m2` 对齐 ProofTrace、首门分歧、断言和 Hybrid 分支；下载 JSON 后用 `verify_causal_audit()` 全量重算，见 `WITNESS_CHAIN.md` |
| L3 | `python3 starter_kit/evaluator.py --level l3` | AST 编译器、独立参考语义与固定种子随机程序 |
| 对抗边界 | `cd starter_kit && python3 -m unittest tests.test_resource_boundaries -v` | 超大寄存器、稠密 21-qubit 拒绝、稀疏执行匹配 24/30/25 比特能力表、31-qubit Web 400、65 层分支拒绝 |
| 自定义量子 RISC-V | `python3 starter_kit/bonus_evaluator.py`；`cd starter_kit && python3 -m unittest tests.test_quantum_riscv -v` | 32 位 `custom-0` 编码、字节序列、严格解码、12 门固定机器字、字面 Bell 执行、无损参数表、100 条随机线路与扩展模拟器闭环 |
| 科学边界 | 阅读 `SCIENTIFIC_CLAIMS_AUDIT.md` | 模拟器、Z 基相关、真机噪声、模型 fixture 的允许结论与非声明 |

## 建议体验的三个任务

1. 保留默认 Bell、候选反例、断言与 Hybrid 程序，点击“生成统一审计链”；核对 `g2` 首门分歧、`m1/m2` 断言依赖、`m2` 分支来源，并下载可重算 JSON。
2. 点击 Learn，运行 Bell，读取逐门概率/相位与 ProofTrace 三目标证书；随后进入 Counterfactual Circuit Lab 单独查看 `CX` 对 `X` 与 TV 距离 `0.5`。
3. 点击 Repair 验证错误 QASM 的确定性恢复，再用 Backend Match 询问“免费、零排队、至少 20 比特的模拟器”，核对规范 capability ID。

与十二个公开可审固定提交的逐项映射及仍需外部凭据的材料见 `COMPETITIVE_COVERAGE.md`。该比较只记录公开可审事实；私有 12 例 DeepSeek 评测和未公开提交仍然未知。

Web 不接收或保存模型 Key；启动进程只从 `LOOMQ_LLM_*` 读取。未配置模型时，L1 本地实验仍可完整使用。
