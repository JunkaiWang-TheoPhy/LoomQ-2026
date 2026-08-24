# LoomQ 评委快速复核

本 fork 的目标是让没有 QASM 和厂商 SDK 背景的用户完成“理解、生成或修复电路 → 选择后端 → 三目标转译 → 运行并解释结果”。核心路径只使用 Python 标准库。

`112` 是赛题各项相加的理论上限，不是本项目已获得的分数。私有 case、人工体验和真机可追溯性仍由组委会判定。

## 60 秒索引

| 区域 | 一条复核命令 | 主要证据 |
|---|---|---|
| 全部无凭据路径 | `python3 starter_kit/verify_submission.py` | 158 项归档回归、Node present 时执行前端语法检查，否则显式 `SKIP`、Web/API/assert/compare/hybrid 焦点套件、ProofTrace、L2 固定语料、真机 manifest、L1/L3/RISC-V |
| ProofTrace 证明 | `cd starter_kit && python3 -m scripts.prooftrace_benchmark --json` | 225/225 native-IR 删除变异检出、15 项 portability、132 项安全重写；固定 corpus SHA-256 |
| Web 因果学习与 P1/P2 证据 | `cd starter_kit && python3 -m unittest tests.test_web -v` | 21 项 Web 集成测试覆盖 `/api/compare` 首门分歧与结构拒绝、`/api/assert`、`/api/hybrid-trace`、ProofTrace、favicon 与移动端防溢出样式 |
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
| L3 | `python3 starter_kit/evaluator.py --level l3` | AST 编译器、独立参考语义与固定种子随机程序 |
| 对抗边界 | `cd starter_kit && python3 -m unittest tests.test_resource_boundaries -v` | 超大寄存器、稠密 21-qubit 拒绝、稀疏执行匹配 24/30/25 比特能力表、31-qubit Web 400、65 层分支拒绝 |
| 自定义量子 RISC-V | `python3 starter_kit/bonus_evaluator.py`；`cd starter_kit && python3 -m unittest tests.test_quantum_riscv -v` | 32 位 `custom-0` 编码、字节序列、严格解码、12 门固定机器字、字面 Bell 执行、无损参数表、100 条随机线路与扩展模拟器闭环 |
| 科学边界 | 阅读 `SCIENTIFIC_CLAIMS_AUDIT.md` | 模拟器、Z 基相关、真机噪声、模型 fixture 的允许结论与非声明 |

## 建议体验的三个任务

1. 点击 Learn，运行 Bell，再进入 Counterfactual Circuit Lab 比较默认反例：页面应精确定位第 2 扇门、显示 `CX` 对 `X` 与 TV 距离 `0.5`；随后可读取逐门概率/相位和 ProofTrace 三目标证书。
2. 点击 Repair，提交预填的越界 Bell QASM；只让通过确定性验证的完整 QASM 到达用户。
3. 点击 Backend Match，询问“免费、零排队、至少 20 比特的模拟器”；回答必须包含官方能力表的兼容规范 ID。

与十二个公开可审固定提交的逐项映射及仍需外部凭据的材料见 `COMPETITIVE_COVERAGE.md`。该比较只声称公开可审能力覆盖领先；私有 12 例 DeepSeek 评测和未公开提交仍然未知。

Web 不接收或保存模型 Key；启动进程只从 `LOOMQ_LLM_*` 读取。未配置模型时，L1 本地实验仍可完整使用。
