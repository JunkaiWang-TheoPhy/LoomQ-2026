# LoomQ：从量子 Agent 到可重放证据链

**参赛队伍**：JunkaiWang-TheoPhy
**参赛提交**：`1aacb23b350df124ac8bd5a446ea3e7635a0fc8a`
**官方归档**：[Final Submission #169](https://github.com/QAIDAO/LoomQ-2026/issues/169)

## 摘要

LoomQ 将自然语言量子编程、统一电路中间表示、三平台转译、混合量子—经典执行和证据复核组织为一条可重放链路。系统的关键设计是把“模型提出的候选程序”和“系统确认的实验结论”分开：候选 QASM 必须经过白名单、语义、目标分布和资源边界检查，执行结果随后进入 ProofTrace、Witness Chain、断言面板或 Hybrid 路径证书。

本提交的公开证据包含 225/225 个 ProofTrace 变异检出、132 项安全重写检查、15 项 portability 检查、40,000 项固定种子离线压力、500 条 L2 语料、120 项 PyQuafu 交叉验证、4 个 Hybrid 路径证书样例、6/6 L1 公开电路、L3 分支语义和量子 RISC-V 端到端检查。证据材料同时包含 OriginQ 与 SpinQ 两个平台的可追溯 Bell 运行记录。

本文的中心命题、贡献边界、基线比较和非声明见 [`INNOVATION_POSITIONING.md`](INNOVATION_POSITIONING.md)。摘要中的数字是公开脚本在声明输入范围内的工程证据，不代表隐藏评测成绩或物理量子优势。

## 0. 中心命题与创新边界

LoomQ 将 Agent 输出定义为“带证据的实验候选”：模型提出源电路，确定性验证器确认语义与资源约束，执行层保留 provider provenance，ProofTrace、Witness Chain 和 Hybrid path certificate 将结果重新连接到源操作。这个分解使生成、执行和结论可以分别替换与审计。

这项定位不宣称无界形式化证明、作者身份签名、量子优势或既有研究中的优先权。完整的形式化对象、评价协议、基线比较和局限见 [`INNOVATION_POSITIONING.md`](INNOVATION_POSITIONING.md)。

## 1. 系统目标与用户路径

LoomQ 面向三类用户：第一次接触量子计算的学习者、需要自然语言辅助的开发者，以及需要复核转译结果的工程评审者。系统提供 Learn、Build、Repair、Backend Match 四条入口，并用 Quantum World 旅程把一次实验拆成“预测—A/B 实验—结论审计—回放护照”四个动作。

学习路径的每一步都对应真实 API 结果。用户可以先写下预测，再运行保留 CX 与移除 CX 的两份电路，系统将首个状态分歧定位到 `g2 · CX`，随后生成 `loomq-inquiry-passport-v1` JSON。护照包含问题、预测、两份 QASM、counts、首门分歧、结论审计和回放入口，适合课堂讲解和评委快速复核。

## 2. 端到端架构

```text
自然语言 / OpenQASM 2.0
          │
          ▼
确定性语义合同与 Prompt Contract
          │
          ▼
Circuit IR ──► 门白名单与资源边界
          │
          ├──► SpinQ OpenQASM 2.0
          ├──► OriginQ OriginIR
          └──► Braket OpenQASM 3.0
          │
          ▼
本地模拟 / 厂商适配器 / 真机证据
          │
          ▼
ProofTrace · P1 断言 · P2 Hybrid trace
          │
          ▼
Witness Chain · Hybrid path certificate · Replay Passport
```

`adapter.py` 是统一入口。转译器输出会被目标 parser 重新读回，并与源 Circuit 做完全相等检查；因此目标 IR 既是展示材料，也是可执行、可回读的工程对象。

## 3. 三层证据设计

### 3.1 ProofTrace：证明转译仍然携带源语义

ProofTrace 为每个源门分配稳定 lineage，记录安全重写、优化 metrics、目标哈希和独立回读结果。五个算法展品在三种 target 上执行 225 个单指令删除变异，全部被检测，结果为 `225/225`；同时完成 `15` 项 portability 与 `132` 项 rewrite checks。

验证命令：

```bash
python3 -m starter_kit.scripts.prooftrace_benchmark --json
```

### 3.2 Witness Chain：把多个证据坐标对齐

Witness Chain 使用稳定的 `gN/mN` 源操作 ID，把首门分歧、统计断言、Hybrid 分支 provenance 与 ProofTrace lineage 对齐。下载的 JSON 可以由 `verify_causal_audit()` 从输入全量重算，摘要用于快速发现内容变化。

验证入口：Web 默认 Bell 实验中的“生成统一审计链”，以及 `starter_kit/WITNESS_CHAIN.md` 中的重算命令。

### 3.3 Hybrid path certificate：把分支概率变成可审计对象

Hybrid 路径证书穷举全部 declared classical bits，在有界资源内精确聚合分支概率，记录 live path、dead path、unreachable outcome、路径总概率和重算结果。实现覆盖 mid-circuit measurement 后继续施加量子门的程序形态；证书验证器从源程序重新计算并拒绝篡改数据。

验证命令：

```bash
python3 -m starter_kit.scripts.hybrid_path_benchmark --json
```

公开 benchmark 包含 4 个 fixture，4/4 验证通过，4/4 篡改样例被拒绝。

## 4. L1：统一适配与真实平台证据

同一个 Circuit IR 生成三种目标语法，覆盖赛题 12 门白名单。公开 Bell 与 GHZ3 电路在 SpinQ、OriginQ、Braket 三目标上完成 `6/6` L1 检查。

本提交的证据目录包含 OriginQ 与 SpinQ 两个平台的原始结果、QASM、截图、任务元数据、统计重算和 SHA-256 manifest。OriginQ 证据按 finite-shot counts 给出 Wilson 区间；SpinQ 证据按 provider probability 报告投影概率和总变差距离。两种返回类型分别保留，便于评审者按平台语义复核。

独立的 PyQuafu 交叉验证覆盖 40 个唯一电路、全部 12 门和三个 target，共 `120/120` 项通过，最大状态向量振幅误差为 `1.1802326323952682e-15`。

## 5. L2：模型提出候选，验证器确认结果

L2 通过 `LOOMQ_LLM_BASE_URL`、`LOOMQ_LLM_API_KEY`、`LOOMQ_LLM_MODEL` 注入模型服务。自然语言请求先生成 Prompt Contract，随后由确定性验证器检查：

- OpenQASM 2.0 语法与 12 门白名单；
- Bell、GHZ、W、均匀叠加和计算基态的目标分布；
- 后端 capability ID、比特数、费用、排队和设备类型；
- 一次诊断重试与安全回退；
- 受限多轮上下文、角色交替和凭据边界。

固定种子 L2 campaign 共 500 条唯一语料：生成 150、修复 150、后端推荐 120、对抗输入 50、稳定性 30。离线压力活动进一步执行 40,000 项固定判据，覆盖概率归一化、三目标 IR/Schema、量子 RISC-V 往返、L3 差分和拒绝路径。

## 6. L3 与量子 RISC-V

L3 编译器将有界 Hybrid-QASM classical block 解析为 AST，并生成官方轻量模拟器可执行的 RISC-V 控制流。公开分支语义测试通过；离线活动包含 20,000 项 L3 四输入差分执行。

量子 RISC-V 扩展使用真实 32 位 `custom-0` machine word，提供无损参数表、严格解码、字节序检查、字面 Bell 执行、随机线路和扩展模拟器闭环。官方 verifier 的量子 RISC-V 阶段通过，Bell counts 为 `00=512, 11=512`。

## 7. 工程与产品化

仓库提供零依赖本地 Web 实验台、CLI trace 入口、固定 Python 3.10 Bookworm 容器基线、统一测试入口和完整证据索引。Web 侧提供桌面与移动端布局、键盘焦点、语义结果表、`role=alert`、`aria-live`、减少动画偏好和错误恢复路径。

快速复核：

```bash
python3 starter_kit/verify_submission.py
python3 -m unittest discover -s tests
```

当前归档验证结果：根目录 88 项测试通过，2 项可选 SDK 检查跳过；官方 verifier 全部阶段通过。

## 8. 评委 3 分钟体验路径

1. 打开 Web，进入 Quantum World 序章。
2. 选择“CX 建立最初的两个分支”，留下预测。
3. 运行 A/B 电路，查看 `g2 · CX` 首个状态分歧。
4. 打开结论审计，查看 counts、证据模式和科学解释。
5. 下载 Inquiry Passport。
6. 生成 Witness Chain，并进入 Hybrid path certificate 查看 live/dead path 与概率重算。

这条路径把新手体验、实验设计、可解释结果和工程证据放在同一个可操作流程里，评委可以从页面直接进入代码、测试和归档证据。

## 9. 结语

LoomQ 的核心贡献是把量子 Agent 的“生成”扩展为一条完整的工程证据链：候选程序可执行，目标 IR 可回读，实验结果可解释，分支概率可重算，跨模块 provenance 可对齐，用户结论可回放。ProofTrace、Witness Chain、Hybrid path certificate 与 Inquiry Passport 共同构成面向量子软件生态的可复核工作流。

### 主要来源

- [LoomQ README](../README.md)
- [Starter Kit README](../starter_kit/README.md)
- [Judge Guide](../starter_kit/JUDGE_GUIDE.md)
- [ProofTrace specification](../starter_kit/PROOFTRACE.md)
- [Witness Chain specification](../starter_kit/WITNESS_CHAIN.md)
- [Scientific claims audit](../starter_kit/SCIENTIFIC_CLAIMS_AUDIT.md)
- [Official accepted archive #169](https://github.com/QAIDAO/LoomQ-2026/issues/169)
