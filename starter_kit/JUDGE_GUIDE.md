# LoomQ 评委快速复核

本 fork 的目标是让没有 QASM 和厂商 SDK 背景的用户完成“理解、生成或修复电路 → 选择后端 → 三目标转译 → 运行并解释结果”。核心路径只使用 Python 标准库。

`112` 是赛题各项相加的理论上限，不是本项目已获得的分数。私有 case、人工体验和真机可追溯性仍由组委会判定。

## 60 秒索引

| 区域 | 一条复核命令 | 主要证据 |
|---|---|---|
| 全部无凭据路径 | `python3 starter_kit/verify_submission.py` | 71 项归档回归、L2 固定语料、真机 manifest、L1/L3/RISC-V |
| 离线压力证据 | `python3 -m starter_kit.scripts.offline_stress_campaign --validate` | 40,000/40,000 项、六条断言通道、固定语料 SHA-256 |
| L1 三目标 | `python3 starter_kit/evaluator.py --level l1 --target spinq,originq,braket` | 统一 Circuit IR、12 门 × 3 target 归档测试 |
| L1 独立数值 oracle | `python3 -m starter_kit.scripts.quafu_cross_validate --validate` | `PYQUAFU_CROSS_VALIDATION.md`；真实 PyQuafu 0.4.5 的 120/120 摘要 |
| L1 两平台真机 | `python3 -m starter_kit.scripts.validate_hardware_evidence` | OriginQ、SpinQ job ID，provider 原始结果、截图、统计分析和 SHA-256 manifest |
| L2 客观路径 | 正式环境执行 `python3 starter_kit/evaluator.py --level l2` | 环境注入模型、能力表 grounding、语法/门集/目标分布校验、一次诊断重试与安全 fallback |
| L2 鲁棒性工具 | `python3 -m starter_kit.scripts.l2_stress_campaign --dry-run` | 500 个唯一生成/修复/推荐/对抗/稳定性 case；没有凭据时不伪造真实模型成绩 |
| L2 体验 | `python3 -m starter_kit.loomq.web` | Learn / Build / Repair / Backend Match、桌面/移动端截图、`WEB_QA.md` |
| L3 | `python3 starter_kit/evaluator.py --level l3` | AST 编译器、独立参考语义与固定种子随机程序 |
| 自定义量子 RISC-V | `python3 starter_kit/bonus_evaluator.py` | 32 位 `custom-0` 编码、字节序列、严格解码与扩展模拟器执行 |
| 科学边界 | 阅读 `SCIENTIFIC_CLAIMS_AUDIT.md` | 模拟器、Z 基相关、真机噪声、模型 fixture 的允许结论与非声明 |

## 建议体验的三个任务

1. 点击 Learn，运行 Bell，再切换均匀叠加和 Braket，读取概率图、文本表、位序与原生 IR。
2. 点击 Repair，提交预填的越界 Bell QASM；只让通过确定性验证的完整 QASM 到达用户。
3. 点击 Backend Match，询问“免费、零排队、至少 20 比特的模拟器”；回答必须包含官方能力表的兼容规范 ID。

Web 不接收或保存模型 Key；启动进程只从 `LOOMQ_LLM_*` 读取。未配置模型时，L1 本地实验仍可完整使用。
