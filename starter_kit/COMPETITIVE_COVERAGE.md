# 固定提交能力覆盖矩阵

本表只比较截止前已由官方机器人归档的固定 commit，不比较赛后分支，也不把“申报”当成“得分”。当前公开可审对手基线为：

- [mayloveless #75](https://github.com/QAIDAO/LoomQ-2026/issues/75)，`9b1fe15596f8c63f51ddd08caaa323ca51dbcf77`
- [0Dionysus0 #80](https://github.com/QAIDAO/LoomQ-2026/issues/80)，`e9c273dab15447827df8ca093bdea43b6fef8101`
- [EndlessTR #71](https://github.com/QAIDAO/LoomQ-2026/issues/71)，`10febabd97785055f239d8f24716fb053d9f95b7`
- [WayneYu1212 #119](https://github.com/QAIDAO/LoomQ-2026/issues/119)，`ac0eb3b9f37b1b85f1d7b05ab83b8ee1a7331fd5`（V7.1 相对 #69 只重做 Web 静态资源、Web 资产测试与四份引导文档；L1/L2/L3、真机和量子 RISC-V 实现保持不变）
- [Huxingyu #85](https://github.com/QAIDAO/LoomQ-2026/issues/85)，`d6cc9225571e3685bed4c8e04b35d7a9e34cf0ce`
- [Duanice #94](https://github.com/QAIDAO/LoomQ-2026/issues/94)，`ceaca08736070baa3f5f3b06272de5176f5cd61d`
- [UokyI #82](https://github.com/QAIDAO/LoomQ-2026/issues/82)，`cb803353034f1c2bc27e9a77fcbba2ecb7c1f95b`
- [orange-city #77](https://github.com/QAIDAO/LoomQ-2026/issues/77)，`35d628d607fe9a89fef276e53f08177787366513`
- [talk2joan #125](https://github.com/QAIDAO/LoomQ-2026/issues/125)，`f74b3d68bd2875fffa2df4934c7fea14d2197961`（相对 #122 只修改根 README；#122 的 Web/demo、样式、像素猫开场和宽屏双栏保持不变）
- [3dmove #102](https://github.com/QAIDAO/LoomQ-2026/issues/102)，`1c7b4e74ee968819bc88a78240aafee938c6892c`（仅申报 L1/L2，无真机证据或 L3）
- [danjituya #103](https://github.com/QAIDAO/LoomQ-2026/issues/103)，`5773b3f451f0163030cee3c15ba008a8246fd10e`（L1/L2/L3、零依赖 Web；未申报真机或量子 RISC-V）
- [Pennie514 #126](https://github.com/QAIDAO/LoomQ-2026/issues/126)，`2878b858d981d6b1667c434b8550deb662c895df`（L1/L2/L3、Web/CLI、量子 RISC-V；已归档 SpinQ 与 OriginQ 两平台真机结果）
- [QBridge #108](https://github.com/QAIDAO/LoomQ-2026/issues/108)，`ef58b3387b8c942581f4a507fdf1f06fd929006f`（四页零依赖 Web、L1/L2/L3、单个 SpinQ 真机 job）
- [jessicaruan #120](https://github.com/QAIDAO/LoomQ-2026/issues/120)，`434b01daf12b165dc18dd458c241a8977e4f62f4`（相对 #112 只修改 `evidence/README.md` 14 行；L1/L2/L3、双厂商真机材料、随机 L3 差分与 `CUSTOM-0` 机器码闭环保持不变）
- [yiyuanrvk77 #115](https://github.com/QAIDAO/LoomQ-2026/issues/115)，`d85e5c2cd39f19082e640a435ec1a38d65844329`（Quantum Cave、四个纠错交互、L1/L2/L3、三门 `QUANT custom-0` 与单个 SpinQ 真机 job）

“覆盖”表示当前仓库有可运行实现和直接验证证据；“外部证据缺口”表示代码路径存在，但没有凭据或新真机 job 时不能诚实伪造实验结果。本文件只声称公开可审能力覆盖；截至 2026-08-24，私有 12 例 DeepSeek 评测、未公开提交与组委会最终人工体验分仍然未知。

容器判断固定到公开文件与发行版索引：talk2joan [#125 Dockerfile](https://github.com/talk2joan/LoomQ-2026/blob/f74b3d68bd2875fffa2df4934c7fea14d2197961/starter_kit/Dockerfile) 和 Pennie514 [#126 Dockerfile](https://github.com/Pennie514/LoomQ-2026/blob/2878b858d981d6b1667c434b8550deb662c895df/starter_kit/Dockerfile) 均为浮动 `python:3.10-slim` + `libcurl4`；[Debian Trixie](https://packages.debian.org/trixie/libcurl4t64) 提供 `libcurl4t64`，[Bookworm](https://packages.debian.org/bookworm/libcurl4) 提供 `libcurl4`。本仓库因此固定 Bookworm，而不把未执行的 Docker build 写成成功。

| 能力 | 强对手公开实现 | 本仓库直接证据 | 判定 |
|---|---|---|---|
| 12 门 × SpinQ / OriginQ / Braket | 所列强队均覆盖 | `test_archive_core.py` 的 36 项门/target 矩阵；`evaluator.py --level l1` | 覆盖 |
| 目标 IR 不是占位文本 | mayloveless、Wayne 的原生输出审计 | `loomq/native_ir.py` 独立回读三种语法；每次 `adapter.transpile()` 强制语义 round-trip | 已实现并提供复核入口 |
| 证明携带编译与门谱系 | 对手未展示统一证书路径 | ProofTrace 记录命名重写、source→optimized lineage、metrics、whole-circuit validation、三目标哈希与独立回读；Web 可下载 JSON | 额外提供可重算证书，不把等价检查本身说成研究创新 |
| 编译篡改基准 | mayloveless hidden-like、Wayne fuzz | 五个算法 × 三目标的 225 个单指令删除变异全部触发 structure rejection，且全部触发 semantic rejection；另有 15 portability + 132 rewrite checks | 225 个固定变异全部被两层证据拒绝 |
| 独立数值 oracle | Wayne 的 vendor SDK 检查 | PyQuafu 0.4.5 固定 40 电路、三 target 共 120/120；最大振幅误差 `1.19e-15` | 覆盖 |
| 可运行算法展品 | 0Dionysus0 的 Deutsch；其他队的 Grover/QFT/教学示例 | `deutsch_jozsa_balanced.qasm`、`grover3.qasm`、`qft4.qasm`；三 target 运行测试 | 已实现并放进 Web 入口 |
| 逐门调试与教学解释 | mayloveless 的 trace/debug/explainer | Web 与 CLI `trace` 展示每门后的概率、复振幅、相位和作用说明 | 已实现并提供复核入口 |
| 反事实因果学习 | talk2joan #125 的六关游戏化新手任务与概念解释路由 | Counterfactual Circuit Lab 允许用户改写候选 QASM，逐门精确定位首个状态分歧，展示参考/候选门、振幅差与 TV 距离；结构不同则拒绝伪因果结论 | 已实现首门分歧复核入口 |
| P1 断言证据面板 | 新增公开审计重点：Huxingyu、Duanice、UokyI、orange-city 均需人工点开验证 | `/api/assert` 与 Web 断言面板区分 exact-local、finite-shots、provider-probabilities；显式展示 pass/fail/inconclusive 和不归因具体噪声机制 | 已实现并提供复核入口 |
| P2 Hybrid 分支回放 | 新增公开审计重点：Huxingyu、Duanice、UokyI、orange-city 均需人工点开验证 | `/api/hybrid-trace` 与 Web 回放面板显示 branch path、machine jump vs source condition、measurement provenance、寄存器增量与机器字 | 已实现并提供复核入口 |
| Hybrid 路径证书 | jessicaruan #120 有随机 L3 差分和量子 RISC-V 闭环，但未归档路径概率或不可达路径证书 | `/api/hybrid-paths` 穷举有界 declared clbits，正确处理 mid-circuit measurement 后续量子门，聚合精确路径概率并标出 dead/unreachable path；验证端从源程序重新计算 | 额外提供可重算的概率完备证书 |
| 跨模块 Witness Chain | 十五份固定提交未展示共享源操作坐标的统一审计工件 | 稳定 `gN/mN` ID 对齐 ProofTrace、反事实、断言与 Hybrid provenance；内容地址 JSON 可下载并从输入全量重算，结构不匹配时失败关闭 | 额外提供可重算审计链 |
| 多轮 Agent 会话 | 0Dionysus0 的 session 交互 | 严格 `user/assistant` 交替、最多四轮、40k 字符总限额、清空上下文 | 已实现并补充边界检查 |
| 生成、修复、后端推荐 | talk2joan、danjituya、Pennie514、QBridge 与 jessicaruan 等公开 Web Agent | Web 四条引导路径；能力表 grounding；QASM 语法、门集、目标态确定性复核与一次诊断重试；最坏路径中模型连续返回 1000 次无效内容，500/500 固定语料仍由同一判据安全恢复 | 500 条固定语料可安全回退 |
| Prompt Contract | jessicaruan #120、QBridge #108 与 yiyuanrvk77 #115 均有 prompt 分类或 QASM 验证，未展示由模型与验证器共享、可重建的请求合同 | fence 外语义抽取、否定与混合意图、目标基态和后端约束进入同一确定性合同；原文/语义/合同 SHA-256 可重建并明确不是数字签名 | 额外提供模型前后的同一语义判据 |
| 新手 Web 与可视化 | mayloveless React、EndlessTR 引导页、Wayne #119 长篇教程、talk2joan #125 像素猫/flashcard/quest/XP、QBridge 四页任务流、jessicaruan 真机首屏、yiyuanrvk77 Quantum Cave/四个纠错交互，以及 danjituya/Pennie514 零依赖 Web | 零依赖响应式 Web；概率柱图+表格；一键 Witness Chain、反事实因果实验、ProofTrace 证书、P1 断言、P2 Hybrid 回放、路径概率和 Prompt Contract；桌面/390px 浏览器验收；无障碍语义 | 已实现证据优先的不同路径；不复制框架栈、洞穴素材或游戏机制 |
| 可复现容器基线 | talk2joan #125 与 Pennie514 #126 均仍使用浮动 `python:3.10-slim` 并安装 `libcurl4`；该 tag 当前随 Debian Trixie，而 Trixie 包名为 `libcurl4t64` | `starter_kit/Dockerfile` 固定 `python:3.10.21-slim-bookworm` 并保留 Bookworm 的 `libcurl4`；`tests/test_docker_contract.py` 绑定发行版与 curl ABI | 消除公开提交中的干净构建阻断；本机无 Docker daemon，因此只申报官方源核对与静态合同通过 |
| 对抗性资源边界 | mayloveless L3 resource audit、Wayne adversarial tests | QASM 1MB/256 bit/100k op；稠密状态向量 20 qubit；有界稀疏执行匹配 SpinQ 24 / OriginQ 30 / Braket 25；trace 8 qubit；L3 1MB/20k token/4096 statement/64 nesting | 已实现拒绝合同 |
| L2 大规模 campaign | Wayne 真实模型压力材料、talk2joan 14 题申报 | 500 条唯一语料、可执行真实调用的 runner、断点恢复、逐记录哈希、脱敏摘要校验；12 例同形资格链 20 次主链请求 + 错误后端双调用回退；40,000 项无凭据断言 | 工具已实现；真实模型结果仍需凭据 |
| L1 随机/隐藏式压力 | mayloveless hidden-like、Wayne fuzz | 40,000 项固定离线活动 + PyQuafu 随机三比特 corpus + 全门全 target 回读 | 40,000 项固定活动可复核 |
| L3 差分验证 | mayloveless、Wayne 的随机/对抗 L3；Pennie514 #126 记录 700+ Hybrid fuzz；jessicaruan #120 归档两组各 300 个随机程序差分 | 1,000 程序 × 4 测量输入的独立参考差分；归档内另有 250 程序回归 | 本仓库固定主实验为 4,000 次路径比对 |
| 量子 RISC-V Bonus | Huxingyu、Duanice #94 与 Pennie514 #126 展示可执行 `custom-0`；jessicaruan #120 归档五条 `CUSTOM-0` 指令；yiyuanrvk77 #115 实现 H/X/Z 三门四态 `QUANT`；talk2joan 展示量子助记符模拟器 | 真实 32 位 `custom-0` 机器字、无损参数表、序列化、严格解码、12 门独立固定字、字面 Bell 执行、100 条随机线路、3,000 项往返、扩展模拟器与 Hybrid 分支回放闭环 | 已实现并提供逐机器字、PC、分支和测量来源复核 |
| 两平台真机 | 四支较早强队、jessicaruan #120 与 Pennie514 #126 有 OriginQ + SpinQ 材料；QBridge #108 与 yiyuanrvk77 #115 归档单个 SpinQ job | 两个可追溯 job、原始 JSON/MessagePack、截图、QASM、统计重算和 SHA-256 manifest | 2 个可追溯 job 已归档 |
| 真机统计与科学边界 | Wayne 的 tomography/claims audit | OriginQ Wilson 区间、SpinQ 总变差距离、原始文件一致性、`SCIENTIFIC_CLAIMS_AUDIT.md` | 基础统计覆盖；额外层析缺新 job |
| 一键无凭据复核 | Wayne shell/PowerShell、各队测试入口 | `python3 starter_kit/verify_submission.py` 依次验证归档测试、L1/L3/RISC-V、压力摘要、双真机 manifest | 覆盖 |
| 厂商 SDK 示例诚信 | mayloveless、Wayne 的 native runners | 三个 `examples/run_*.py` 可选导入；缺 SDK 明确失败；无 provider job ID 时返回 null，本机观察时间显式标注来源；Braket 直接运行自验证 emitter 输出 | 覆盖并去除 Mock 成功路径 |

## 仍需外部事实才能关闭的两项

1. **真实 DeepSeek 成绩**：runner、500 例语料和防篡改 summary 都已存在，但当前没有获授权的 `LOOMQ_LLM_*` 服务。仓库不会把本地 fixture 或其他模型冒充正式 DeepSeek。
2. **额外真机层析/多电路 job**：现有两平台 Bell job 合法且完整；若要覆盖 Wayne 的补充层析，必须在赛程窗口内获得新的平台登录、真实 job ID 和原始返回。模拟器不能替代这项证据。

这两项是外部实验材料差距，不是本地软件缺少接口。基于上述十五个公开固定提交，本表只记录当前仓库已经放进仓库、且能直接复核的软件能力；私有 12 例 DeepSeek 评测和未公开 entrant 的最终比较结论仍然未知。
