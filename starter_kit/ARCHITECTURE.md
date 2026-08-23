# LoomQ 参赛实现架构

## 服务对象

本工具首先服务于会描述问题、但没有学习过 QASM，也不熟悉各家量子 SDK 的普通开发者和跨界创作者。用户可以用自然语言生成或修复电路；希望进一步理解细节的用户，可以看到标准 QASM、目标平台指令和采样分布，而无需先注册三个云平台账号。

## 端到端流程

```text
自然语言
  │
  ├─ agent_chat() ── 组委会注入的 OpenAI-compatible 模型
  │                    ├─ 生成/修复完整 OpenQASM 2.0
  │                    └─ 基于官方 JSON 能力表推荐规范后端 ID
  │
OpenQASM 2.0
  │
  ├─ qasm.py ── 有界解析器与语义校验
  │
统一 Circuit IR
  ├─ emitters.py ── SpinQ OpenQASM 2.0
  ├─ emitters.py ── OriginIR
  ├─ emitters.py ── Braket OpenQASM 3.0
  ├─ simulator.py ── 无依赖状态向量执行与统一 little-endian counts
  └─ quantum_riscv.py ── 32 位 custom-0 编码／解码 ── 扩展模拟器执行
```

## 模块边界

- `loomq/qasm.py`：解析赛题规定的 12 门子集，展开寄存器级操作，拒绝越界、未知门和不匹配的寄存器。
- `loomq/emitters.py`：只负责从统一 IR 生成三种目标文本，避免三套互不一致的字符串替换逻辑。
- `loomq/simulator.py`：实现 12 种门的状态向量语义和经典测量映射。
- `loomq/runtime.py`：把精确概率按最大余数法转换为整数 shots，并产生统一结果 Schema。
- `loomq/agent.py`：把官方后端能力表注入模型上下文；本地验证 Bell/GHZ 目标分布和后端约束，失败时携带具体诊断重试一次。
- `loomq/hybrid.py`：解析赋值、算术、`if/else` 和测量位引用，检查 `creg` 边界并生成 `li/add/sub/addi/beq/bne/j` 子集。
- `loomq/quantum_riscv.py`：把全部白名单量子门编码为真实 32 位 `custom-0` 机器字，并完成字节序列化和严格解码。
- `riscv_emulator.py`：保持官方 L3 文本汇编路径，同时增加量子机器码加载、解码和执行入口。
- `loomq_cli.py`：面向零基础用户提供转译、执行、文本柱状图、自然语言 Agent 和一键生成运行。

## 为什么基础评分路径不依赖平台 SDK

正式评测在固定 Linux/Python 3.10 容器中进行，并会直接解析目标 IR。基础路径使用 Python 标准库，因此三种目标在没有账号、网络或厂商 SDK 的情况下仍能复现相同语义。开发阶段另用 PyQuafu 0.4.5 对随机电路进行独立数值交叉验证，但 Quafu 不是题面规定的三个评分 target，不会伪装成 SpinQ、OriginQ 或 Braket 真机。

## 正确性保护

- 所有 target 都经过同一个 `Circuit` IR。
- 量子位 `q[0]` 使用状态索引最低位；输出经典位串最右侧固定为 `c[0]`。
- 公开 Bell/GHZ 电路覆盖跨比特纠缠；单元测试逐门覆盖所有 12 个门。
- 固定种子的随机三比特电路与 PyQuafu 状态向量交叉验证。
- L3 使用 1,000 个固定种子随机经典程序、每个程序穷举 4 种测量输入，并与独立 Python 参考语义比较。
- L2 每个 case 至少进行一次真实模型服务调用，模型地址、Key 和名称只从 `LOOMQ_LLM_*` 读取。
- 模型生成的 QASM 先由确定性解析器与状态向量目标检查，后端 ID 再与官方 JSON 能力表复核。
- Bonus 的 Bell 证明真实经历 `Circuit → 机器字 → 小端字节 → 解码 → 扩展模拟器 → counts`。
