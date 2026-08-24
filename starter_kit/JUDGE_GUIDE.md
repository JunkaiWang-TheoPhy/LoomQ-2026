# LoomQ 评委快速复核

页面首屏先给出两张真机证据卡，再提供一个本地评委路径。真机卡区分 OriginQ finite-shot counts 与 SpinQ provider probabilities；本地路径不需要模型密钥、平台账号或网络服务。

## 30 秒入口

1. 打开页面，核对两张真机卡的 provider、job ID、结果类型和原始文件链接。
2. 点击 `一键运行 6 项本地证据`。
3. 等状态显示 `6/6 已由真实本地 API 完成`。沿深色状态条点开任意一项，可查看产生该状态的完整结果。

每个状态都由对应 API 的语义检查产生。点击按钮或收到 HTTP 200 不足以把状态改成完成；输入变化也会清除受影响的旧状态。

## 90 秒页面验收

1. `运行与 ProofTrace`：默认 Bell 电路必须通过等价性检查，SpinQ、OriginQ、Braket 三种目标 IR 都要独立回读成功。
2. `首个因果分歧`：默认 Bell 反例必须定位到第 2 扇门，并显示 `CX` 对 `X`。
3. `统计断言`：默认 support、parity 和 uniformity 断言必须带 `exact-local` evidence mode、可识别状态和不归因具体噪声机制的边界说明。
4. `Witness Chain`：`verification.valid` 必须来自对输入的本地重建，下载件使用稳定 `gN/mN` 坐标。
5. `Mid-circuit 路径`：服务端重新计算全部 declared clbits outcome，页面显示精确路径概率、不可达 outcome 和 dead path。该实现支持测量后继续施加量子门。
6. `Prompt Contract`：默认自然语言请求应解析为 OriginQ、免费、至少 20 比特、simulator、无需账号；合同通过服务端重建。SHA-256 用于发现内容变化，不是身份签名，也不证明某个后端唯一兼容。

Agent 生成是可选的第 7 步。配置 `LOOMQ_LLM_*` 后再运行它；模型回答仍需通过独立的 QASM 或后端能力验证器。私有 case 和人工体验分由组委会判定。

## 60 秒索引

| 区域 | 一条复核命令 | 主要证据 |
|---|---|---|
| 全部无凭据路径 | `python3 starter_kit/verify_submission.py` | 完整归档回归、Node present 时执行前端语法检查，否则显式 `SKIP`、Web/API/assert/compare/hybrid/witness 焦点套件、ProofTrace、L2 固定语料、真机 manifest、L1/L3/RISC-V |
| ProofTrace 证明 | `cd starter_kit && python3 -m scripts.prooftrace_benchmark --json` | 225/225 native-IR 删除变异检出、15 项 portability、132 项安全重写；固定 corpus SHA-256 |
| Web 因果学习与 P1/P2 证据 | `cd starter_kit && python3 -m unittest tests.test_web -v` | 29 项 Web 集成测试覆盖六步评委路径、Prompt Contract、`/api/causal-audit`、首门分歧、统计断言、Hybrid trace/path、ProofTrace、安全头与移动端防溢出样式 |
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

与十四个公开可审固定提交的逐项映射及仍需外部凭据的材料见 `COMPETITIVE_COVERAGE.md`。该比较只记录 accepted archive 中可复核的事实；私有 12 例 DeepSeek 评测和未公开提交仍然未知。

Web 不接收或保存模型 Key；启动进程只从 `LOOMQ_LLM_*` 读取。未配置模型时，L1 本地实验仍可完整使用。
