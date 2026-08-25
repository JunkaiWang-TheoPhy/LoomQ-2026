# LoomQ 的论文式创新定位

## 中心命题

LoomQ 将量子 Agent 的输出定义为一项**带证据的实验候选**，而不是一段可以直接相信的 QASM。候选程序只有在源电路、目标 IR、执行观测和验证结果能够被同一条可重放链路连接时，才进入用户可见的结论层。

该命题对应一个明确的对象分解。设自然语言请求为 `x`，Agent 产生候选源电路 `C`，目标平台为 `p`，转译为 `T_p(C)`，执行返回观测 `O_p`。LoomQ 额外构造证书：

```text
E(C, p) =
  (source lineage,
   rewrite record,
   target round-trip,
   execution provenance,
   assertion result,
   replay hash)
```

`E` 不是作者签名，也不等价于物理定理。它的作用是固定证据坐标，使评审者能够从一个观测结果回到源门、重写、目标语法和判定条件。

## 贡献陈述

### 贡献一：证据携带的量子 Agent 接口

传统的自然语言量子编程接口通常将生成和执行作为连续动作。LoomQ 将二者拆开：模型只提出候选 `C`，确定性验证器负责语法、门集、资源边界、目标分布和后端能力检查。修复过程保留原候选、诊断、修复候选和复核结果。

这一边界使模型可以被替换，而不会改变判定规则。它也为失败提供可定位对象：首个偏差门、目标分布距离、缺失后端能力或违反的资源约束。

### 贡献二：跨模块 Witness 坐标

ProofTrace、统计断言、反事实首门分歧和 Hybrid 分支证书分别产生不同类型的报告。LoomQ 为源门和测量分配稳定的 `gN/mN` 坐标，并在规范化 JSON 上计算摘要，从而把这些报告对齐到同一源电路。

因此，“转译发生变化”“统计断言失败”和“经典分支选择变化”可以在同一坐标系中比较。Witness Chain 只证明软件证据之间的一致性，不扩展各子报告的物理含义。

### 贡献三：Hybrid 路径的概率证书

对含有 mid-circuit measurement 和经典控制流的程序，仅展示最终 counts 无法说明某条分支是否可达。LoomQ 在声明的资源上限内穷举 declared classical bits，重放每个测量结果组合，记录 live path、dead path、不可达 outcome、聚合概率和终态寄存器摘要。

证书验证器不信任提交的概率或摘要，而是从源 Hybrid-QASM 重新计算。这一设计把“某条路径发生了多少概率”转化为可重算的软件对象，同时明确排除真机噪声归因。

### 贡献四：将量子概念教学嵌入实验协议

Quantum World 的教学步骤与 API 结果一一对应。用户先提出预测，再运行电路变体，最后根据 counts、首门分歧和边界说明修正结论。量子村庄与宇宙贴图分别对应测量结果 `0` 和 `1`；贴图是交互表示，量子结论仍由电路和统计数据给出。

这使“新手引导”成为一个可复放实验，而不是预先录制的解释动画。Bell 不等式在教学路径中用于提出可检验的问题；单次 Z 基测量不会被表述为完整 Bell 检验。

## 与常见基线的差异

| 基线 | 可以回答的问题 | LoomQ 额外固定的对象 |
|---|---|---|
| 文本型量子 Agent | 模型生成了什么电路？ | 候选 QASM 的语法、门集、目标分布和修复前后差异 |
| 只做转译的工具链 | 电路能否变成目标语法？ | 源 lineage、目标 IR 回读、重写记录和 replay hash |
| 只展示真机结果的 Demo | 平台返回了什么 counts？ | job ID、timestamp、bit order、原始结果和 provenance |
| 只展示最终 counts 的 Hybrid 工具 | 最终结果是什么？ | 每个 declared outcome 的路径、概率、不可达性和终态寄存器 |
| 静态量子教程 | 用户看到了哪些概念？ | 预测—实验—审计—回放的真实交互闭环 |

该表是系统边界比较，不是对既有研究的优先权判断。若将本文定位为论文，仍需在正式文稿中补充相关工作检索，并逐项说明与已有 quantum programming agent、compiler provenance、program certificate 和 quantum education systems 的关系。

## 可复核评价协议

评价对象分为四层：

1. **语义层**：源 Circuit 与三种目标 IR 的 parser round-trip、目标分布和门白名单。
2. **执行层**：本地精确模拟、provider 概率或 finite-shot counts；不同证据模式不混合。
3. **证据层**：ProofTrace、Witness Chain、Hybrid path certificate 和篡改拒绝。
4. **交互层**：无模型凭据的 Learn / Inquiry / Replay 路径，以及配置凭据后的 Agent 和硬件 gateway。

当前归档材料给出以下公开工程证据：ProofTrace 变异检出 `225/225`，安全重写检查 `132` 项，PyQuafu 交叉验证 `120/120`，离线固定判据 `40,000/40,000`，Hybrid 路径 fixture `4/4`，以及 OriginQ 和 SpinQ 的可溯源实验记录。上述数字只说明对应脚本和输入范围内的复核结果，不替代组委会的隐藏评测或真机物理结论。命令和边界见 [`SCIENTIFIC_CLAIMS_AUDIT.md`](../starter_kit/SCIENTIFIC_CLAIMS_AUDIT.md) 与 [`JUDGE_GUIDE.md`](../starter_kit/JUDGE_GUIDE.md)。

## 局限与非声明

- `E(C, p)` 是可重放的工程证书，不是作者身份签名，也不是无界形式化证明。
- 本地精确模拟不等于真机执行；provider 概率不等于 finite-shot 统计置信区间。
- Hybrid 路径证书受量子比特、稀疏状态和 outcome 枚举上限约束。
- Bell 教学关卡建立相关性和统计检验的直觉，不以单次 Z 基结果宣称 Bell 不等式被违反。
- Agent 的公开 fixture 证明协议和验证器链路，不证明未公开模型服务上的正式得分。
- 该文档使用“创新定位”描述本仓库的系统构造；在没有系统相关工作和同行评审前，不使用“首次”“普遍优于”或“证明量子优势”等优先权和性能断言。

## 一句话摘要

LoomQ 的技术贡献不是让 Agent 更自由地生成量子电路，而是让每个候选电路都携带一条可检查、可解释、可重放的执行证据链，并将这条证据链延伸到跨平台转译、Hybrid 分支和零基础用户的实验学习路径。
