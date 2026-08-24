# 固定提交能力覆盖矩阵

本表只比较截止前已由官方机器人归档的固定 commit，不比较赛后分支，也不把“申报”当成“得分”。当前公开可审对手基线为：

- [mayloveless #75](https://github.com/QAIDAO/LoomQ-2026/issues/75)，`9b1fe15596f8c63f51ddd08caaa323ca51dbcf77`
- [0Dionysus0 #80](https://github.com/QAIDAO/LoomQ-2026/issues/80)，`e9c273dab15447827df8ca093bdea43b6fef8101`
- [EndlessTR #71](https://github.com/QAIDAO/LoomQ-2026/issues/71)，`10febabd97785055f239d8f24716fb053d9f95b7`
- [WayneYu1212 #69](https://github.com/QAIDAO/LoomQ-2026/issues/69)，`02e94e68251592523ecc089b89795dee964b48df`
- [Huxingyu #85](https://github.com/QAIDAO/LoomQ-2026/issues/85)，`d6cc9225571e3685bed4c8e04b35d7a9e34cf0ce`
- [Duanice #89](https://github.com/QAIDAO/LoomQ-2026/issues/89)，`e306067c406f401809b8a8d7a6e68b58e92b6d04`
- [UokyI #82](https://github.com/QAIDAO/LoomQ-2026/issues/82)，`cb803353034f1c2bc27e9a77fcbba2ecb7c1f95b`
- [orange-city #77](https://github.com/QAIDAO/LoomQ-2026/issues/77)，`35d628d607fe9a89fef276e53f08177787366513`

“覆盖”表示当前仓库有可运行实现和直接验证证据；“外部证据缺口”表示代码路径存在，但没有凭据或新真机 job 时不能诚实伪造实验结果。本文件只声称公开可审能力覆盖；私有 12 例 DeepSeek 评测、未公开提交与组委会最终人工体验分仍然未知。

| 能力 | 强对手公开实现 | 本仓库直接证据 | 判定 |
|---|---|---|---|
| 12 门 × SpinQ / OriginQ / Braket | 所列强队均覆盖 | `test_archive_core.py` 的 36 项门/target 矩阵；`evaluator.py --level l1` | 覆盖 |
| 目标 IR 不是占位文本 | mayloveless、Wayne 的原生输出审计 | `loomq/native_ir.py` 独立回读三种语法；每次 `adapter.transpile()` 强制语义 round-trip | 覆盖并加强 |
| 证明携带编译与门谱系 | 对手未展示统一证书路径 | ProofTrace 记录命名重写、source→optimized lineage、metrics、三目标哈希与独立回读；Web 可下载 JSON | 新增差异化能力 |
| 编译篡改基准 | mayloveless hidden-like、Wayne fuzz | 五个算法 × 三目标的 225 个单指令删除变异全部检出；另有 15 portability + 132 rewrite checks | 新增量化证据 |
| 独立数值 oracle | Wayne 的 vendor SDK 检查 | PyQuafu 0.4.5 固定 40 电路、三 target 共 120/120；最大振幅误差 `1.19e-15` | 覆盖 |
| 可运行算法展品 | 0Dionysus0 的 Deutsch；其他队的 Grover/QFT/教学示例 | `deutsch_jozsa_balanced.qasm`、`grover3.qasm`、`qft4.qasm`；三 target 运行测试 | 覆盖并合并到 Web |
| 逐门调试与教学解释 | mayloveless 的 trace/debug/explainer | Web 与 CLI `trace` 展示每门后的概率、复振幅、相位和作用说明 | 覆盖 |
| P1 断言证据面板 | 新增公开审计重点：Huxingyu、Duanice、UokyI、orange-city 均需人工点开验证 | `/api/assert` 与 Web 断言面板区分 exact-local、finite-shots、provider-probabilities；显式展示 pass/fail/inconclusive 和不归因具体噪声机制 | 新增差异化能力 |
| P2 Hybrid 分支回放 | 新增公开审计重点：Huxingyu、Duanice、UokyI、orange-city 均需人工点开验证 | `/api/hybrid-trace` 与 Web 回放面板显示 branch path、machine jump vs source condition、measurement provenance、寄存器增量与机器字 | 新增差异化能力 |
| 多轮 Agent 会话 | 0Dionysus0 的 session 交互 | 严格 `user/assistant` 交替、最多四轮、40k 字符总限额、清空上下文 | 覆盖并加边界 |
| 生成、修复、后端推荐 | 四队 Web Agent | Web 四条引导路径；能力表 grounding；QASM 语法、门集、目标态确定性复核与一次诊断重试 | 覆盖 |
| 新手 Web 与可视化 | mayloveless React、EndlessTR 引导页、Wayne Web QA | 零依赖响应式 Web；概率柱图+表格；ProofTrace 证书、P1 断言、P2 Hybrid 回放、逐门故事；桌面/390px 浏览器验收；无障碍语义 | 功能覆盖；不复制框架栈 |
| 对抗性资源边界 | mayloveless L3 resource audit、Wayne adversarial tests | QASM 1MB/256 bit/100k op；稠密状态向量 20 qubit；有界稀疏执行匹配 SpinQ 24 / OriginQ 30 / Braket 25；trace 8 qubit；L3 1MB/20k token/4096 statement/64 nesting | 覆盖并形成拒绝合同 |
| L2 大规模 campaign | Wayne 真实模型压力材料 | 500 条唯一语料、可执行真实调用的 runner、断点恢复、逐记录哈希、脱敏摘要校验；另有 40,000 项无凭据断言 | 工具覆盖；真实模型结果仍需凭据 |
| L1 随机/隐藏式压力 | mayloveless hidden-like、Wayne fuzz | 40,000 项固定离线活动 + PyQuafu 随机三比特 corpus + 全门全 target 回读 | 覆盖并加强 |
| L3 差分验证 | mayloveless、Wayne 的随机/对抗 L3 | 1,000 程序 × 4 测量输入的独立参考差分；归档内另有 250 程序回归 | 覆盖 |
| 量子 RISC-V Bonus | 四队均申报 | 真实 32 位 `custom-0` 机器字、序列化、严格解码、扩展模拟器和 Bell counts 闭环 | 覆盖 |
| 两平台真机 | 四队均有 OriginQ + SpinQ | 两个可追溯 job、原始 JSON/MessagePack、截图、QASM、统计重算和 SHA-256 manifest | 覆盖并加强证据完整性 |
| 真机统计与科学边界 | Wayne 的 tomography/claims audit | OriginQ Wilson 区间、SpinQ 总变差距离、原始文件一致性、`SCIENTIFIC_CLAIMS_AUDIT.md` | 基础统计覆盖；额外层析缺新 job |
| 一键无凭据复核 | Wayne shell/PowerShell、各队测试入口 | `python3 starter_kit/verify_submission.py` 依次验证归档测试、L1/L3/RISC-V、压力摘要、双真机 manifest | 覆盖 |
| 厂商 SDK 示例诚信 | mayloveless、Wayne 的 native runners | 三个 `examples/run_*.py` 可选导入；缺 SDK 明确失败；无 provider job ID 时返回 null，本机观察时间显式标注来源；Braket 直接运行自验证 emitter 输出 | 覆盖并去除 Mock 成功路径 |

## 仍需外部事实才能关闭的两项

1. **真实 DeepSeek 成绩**：runner、500 例语料和防篡改 summary 都已存在，但当前没有获授权的 `LOOMQ_LLM_*` 服务。仓库不会把本地 fixture 或其他模型冒充正式 DeepSeek。
2. **额外真机层析/多电路 job**：现有两平台 Bell job 合法且完整；若要覆盖 Wayne 的补充层析，必须在赛程窗口内获得新的平台登录、真实 job ID 和原始返回。模拟器不能替代这项证据。

这两项是外部实验材料差距，不是本地软件缺少接口。基于上述八个公开固定提交，我们只声称本仓库在公开可审的软件能力覆盖上处于领先位置；私有 12 例 DeepSeek 评测和未公开 entrant 的最终比较结论仍然未知。
