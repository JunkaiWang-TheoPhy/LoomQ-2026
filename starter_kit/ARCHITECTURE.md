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
  ├─ prooftrace.py ── 安全重写、gate lineage、跨目标证书
  ├─ emitters.py ── SpinQ OpenQASM 2.0
  ├─ emitters.py ── OriginIR
  ├─ emitters.py ── Braket OpenQASM 3.0
  ├─ native_ir.py ── 三目标独立回读与语义等价检查
  ├─ simulator.py ── 稠密/有界稀疏状态向量执行、逐门轨迹与统一 little-endian counts
  └─ quantum_riscv.py ── 32 位 custom-0 编码／解码 ── 扩展模拟器执行

Web / CLI
  └─ 只调用 adapter.py 公共契约，不复制解析、运行或 Agent 逻辑
```

## 模块边界

- `loomq/qasm.py`：解析赛题规定的 12 门子集，展开寄存器级操作，拒绝越界、未知门和不匹配的寄存器。
- `loomq/emitters.py`：只负责从统一 IR 生成三种目标文本，避免三套互不一致的字符串替换逻辑。
- `loomq/native_ir.py`：用与 emitter 分离的解析器回读 SpinQ QASM 2、OriginIR 和 Braket QASM 3；公开 `transpile()` 返回前必须与源 `Circuit` 完全相等，显式 ProofTrace API 则与安全优化后的 `Circuit` 比较。
- `loomq/prooftrace.py`：只执行命名的相邻恒等式，记录每个最终操作的源索引、优化前后 metrics、三目标 SHA-256 与独立回读结果；普通 `transpile()` 保持单目标失败隔离，显式 ProofTrace API 才生成完整证书。
- `loomq/simulator.py`：实现 12 种门的状态向量语义和经典测量映射；20 比特内使用稠密状态向量，21–30 比特使用最多 1,000,000 个非零基态的有界稀疏表示，逐门概率/振幅/相位轨迹最多 8 比特。
- `loomq/runtime.py`：把精确概率按最大余数法转换为整数 shots，并产生统一结果 Schema。
- `loomq/assertions.py`：对 `support`、`parity`、`uniformity` 断言提供三种证据模式：本地精确 `exact-local`、有限 shots Wilson/总变差区间、以及 provider 概率；只报告一致/偏差/不确定，不归因具体噪声机制。
- `loomq/agent.py`：把官方后端能力表注入模型上下文；本地验证 Bell/GHZ/W、计算基态、均匀叠加目标分布和后端约束，失败时携带具体诊断重试一次；两次无效回答后才用同一目标合成器或能力表约束求解器安全回退；单次传输配置最多 55 秒，使两次请求的配置上限合计 110 秒；多轮历史严格交替并限制为 8 条消息。
- `loomq/prompt_contract.py`：在模型调用前把自然语言请求规范化为任务类型、目标态和后端约束；原 prompt、语义字段与合同分别摘要，并可从原 prompt 确定性重建。摘要只检测内容变化，不承担身份认证。
- `loomq/witness.py`：为源门与测量分配稳定 `gN/mN` witness，把 ProofTrace lineage/rewrite、counterfactual first divergence、assertion measurement dependencies 与 Hybrid branch provenance 对齐；规范 JSON SHA-256 后再从嵌入输入全量重算，篡改或 Hybrid 量子部分不一致时失败关闭。
- `scripts/l2_stress_campaign.py`：通过公开 `adapter.agent_chat()` 执行固定的 500 例真实模型语料，支持断点续跑、脱敏记录和逐层 SHA-256 完整性复核。
- `scripts/offline_stress_campaign.py`：执行固定的 40,000 项无凭据断言，分别统计 L1 模拟、三目标契约、L3 差分、量子 RISC-V 往返及拒绝路径，并锁定语料哈希。
- `scripts/prooftrace_benchmark.py`：逐条删除五个算法在三目标 native IR 中的 225 条指令，验证全部篡改被拒绝；另执行 15 项 portability 与 132 项安全重写检查。
- `loomq/hybrid.py`：解析赋值、算术、`if/else` 和测量位引用，检查 `creg` 边界并生成 `li/add/sub/addi/beq/bne/j` 子集。
- `loomq/hybrid_trace.py`：在不改变 `compile_hybrid()` 公共 tuple 契约的前提下，复用编译器与 RISC-V trace 引擎回放 branch path、machine jump、source condition、measurement provenance、机器字和寄存器增量。
- `loomq/quantum_riscv.py`：把全部白名单量子门编码为真实 32 位 `custom-0` 机器字，并完成字节序列化和严格解码。
- `riscv_emulator.py`：保持官方 L3 文本汇编路径，同时增加量子机器码加载、解码和执行入口。
- `loomq_cli.py`：面向零基础用户提供转译、执行、文本柱状图、逐门状态轨迹、自然语言 Agent 和一键生成运行。
- `loomq/web.py` 与 `web/`：标准库 HTTP API、Quantum Atlas 零基础调查地图、由真实动作驱动的三地点状态、Bell 对照实验、响应式实验台、电路预览、概率图、反事实首门分歧实验、ProofTrace 面板、P1 断言报告、P2 Hybrid 分支回放、Prompt Contract 检查、六步评委路径、逐门状态故事、多轮对话和原生 IR 展示；默认仅监听 `127.0.0.1`。地图插画不进入任何科学判定。
- `circuits/`：除 Bell/GHZ 外归档 Deutsch–Jozsa、Grover-3 与 QFT-4；相同源码跨三 target 转译和运行。

## 为什么基础评分路径不依赖平台 SDK

正式评测在固定 Linux/Python 3.10 容器中进行，并会直接解析目标 IR。基础路径使用 Python 标准库，因此三种目标在没有账号、网络或厂商 SDK 的情况下仍能复现相同语义。开发阶段另用 PyQuafu 0.4.5 对随机电路进行独立数值交叉验证，但 Quafu 不是题面规定的三个评分 target，不会伪装成 SpinQ、OriginQ 或 Braket 真机。

## 正确性保护

- 所有 target 都经过同一个 `Circuit` IR。
- 量子位 `q[0]` 使用状态索引最低位；输出经典位串最右侧固定为 `c[0]`。
- 公开 Bell/GHZ 电路覆盖跨比特纠缠；归档内测试逐门、逐目标交叉覆盖全部 12 门 × 3 target。
- 固定种子的随机三比特电路与 PyQuafu 状态向量交叉验证。
- L3 使用 1,000 个固定种子随机经典程序、每个程序穷举 4 种测量输入，并与独立 Python 参考语义比较。
- L2 campaign 在获得授权的 `LOOMQ_LLM_*` 配置时为每个 case 发起至少一次真实模型服务调用；当前归档只证明 runner、固定语料与验证链，不把无凭据 fixture 申报为真实 DeepSeek 成绩。
- 模型生成的 QASM 先由确定性解析器与状态向量目标检查，后端 ID 再与官方 JSON 能力表复核。
- L2 压力 campaign 的 500 条 prompt 在归档测试中检查唯一性和分类配额；证据验证器会重新生成语料并核对 prompt、记录及 JSONL 摘要。
- Bonus 的 Bell 证明真实经历 `Circuit → 机器字 → 小端字节 → 解码 → 扩展模拟器 → counts`。
- `verify_submission.py` 会从提取后的 `starter_kit/` 根目录在 Node present 时执行 `node --check web/app.js`，否则显式 `SKIP`；并显式运行 Web/API/assert/compare/hybrid/witness 焦点套件，再用 `python3 -m unittest discover -s tests -v` 运行完整归档回归，复核 Web→多轮模型协议→确定性校验、反事实首门分歧、跨模块 Witness Chain 重算、12 例 L2 同形 HTTP 资格链、500 例注入式 completion 两次无效回复后的确定性恢复（1000 次回调）、ProofTrace 225 项变异基准、算法展品、三 native IR 回读、量子 RISC-V 固定机器字与随机线路、资源拒绝边界、SDK 示例诚信、逐门状态轨迹、40,000 项离线活动摘要、PyQuafu 摘要与真机 evidence manifest，避免依赖仓库外层测试。
- 可选的 PyQuafu 0.4.5 独立 oracle 使用固定 40 电路覆盖全部 12 门，对三个 target 完成 120 项状态向量与 counts 交叉检查；第三方包隔离在核心环境之外。
- 离线活动的每个计数对应具体断言：概率归一化、目标 IR/Schema、机器码语义往返、四输入差分执行或恶意输入拒绝；不是仅循环不检查结果的数量指标。
- 真机证据验证器从 provider MessagePack、counts JSON 与 QASM 重算统计结果，并用 SHA-256 manifest 锁定原始材料、派生分析和桌面/移动端截图。
- 资源合同在解析或分配前拒绝超过 1,000,000 字符、256 个声明 bit、100,000 个 QASM 操作、超过目标能力表的本地 qubit（SpinQ 24 / OriginQ 30 / Braket 25）、超过 1,000,000 个稀疏基态，以及超过 20,000 token、4,096 statement 或 64 层分支的 classical block；直接申请稠密状态向量仍限制为 20 qubit。
- Web 断言诊断依赖 `assertions.py` 的证据模式区分；逐门 first-divergence 诊断只在最多 8 qubit 的精确状态比较上作出结论，不外推到更大电路或真机内部物理原因。
