# LoomQ 评委快速复核

页面首屏是 `Quantum Atlas · 无形世界调查局`。零基础用户先在观测站理解四条调查规则，随后解锁分岔原野的 Bell A/B 实验和证据塔的结论审计；后方仍保留标题为“每项结论都能复核”的评委附录。附录中的真机卡区分 OriginQ finite-shot counts 与 SpinQ provider probabilities；本地路径不需要模型密钥、平台账号或网络服务。地图由内置图像生成工具生成，不参与科学判定。

## 30 秒入口

1. 打开页面，点击“熟悉量子计算？直接查看证据附录”，核对两张真机卡的 provider、job ID、结果类型和原始文件链接。
2. 点击 `一键运行 6 项本地证据`。
3. 等状态显示 `6/6 已由真实本地 API 完成`。沿深色状态条点开任意一项，可查看产生该状态的完整结果。

每个状态都由对应 API 的语义检查产生。点击按钮或收到 HTTP 200 不足以把状态改成完成；输入变化也会清除受影响的旧状态。

## 3 分钟零基础用户路径

1. 在观测站读完“状态、多种可能、重复观察、只改一个条件”，确认简报后检查分岔原野从 locked 变为 current。
2. 进入 Bell 实验，选择“CX 才建立最初的两个分支”，再运行 A/B。实验 A 保留 H+CX，实验 B 保留 H、禁用 CX；两组使用相同 shots。
3. 页面应显示 A 的主导态为 `00/11`、B 为 `00/01`，将首次状态分歧定位到 `g2 · CX`，并把证据塔变为 current。
4. 继续选择结论“CX 建立了最初的两个分支”，点击结论审计。页面必须指出该结论不受实验支持，同时保留“单次 Z 基实验不能完整证明 Bell 非定域性”的边界。
5. 下载 `loomq-inquiry-bell-gates.json`。护照包含问题、预测、两份 QASM、A/B 结果、首门分歧、结论审计和重放入口；证据塔此时才变为 complete。

地图进度必须由真实交互驱动：简报前只有观测站可用；确认简报后开放分岔原野；A/B 返回后开放证据塔；审计完成后才允许案件归档。错误结论同样可以完成学习旅程，但护照中的审计状态必须保持 `unsupported`，不能把“完成”偷换成“正确”。

这条路径不要求用户先读 QASM 或 assertions JSON。它使用 `/api/inquiry` 编排现有模拟与精确比较能力，不调用模型充当裁判。

## 3 分钟独立 HTML 游戏

打开 `/game.html` 并点击“开始调查”。这是一个连续的 Canvas 2D 世界：用 WASD / 方向键控制调查员，靠近发光物品或角色后按 E / 空格交互。玩家需要在观测站实际寻找四件工具、穿过任务门、操作原野中的 A/B 装置，再将同一份实验护照送到证据塔。

四件工具各贡献 5 分；运行前预测得 10 分，真实 A/B 护照返回后得 20 分并开放证据塔，结论审计得 50 分。总分只记录流程完成度，审计结果仍保留 `supported / unsupported / inconclusive`，不会把错误结论包装成正确答案。移动端显示虚拟摇杆和“调查”按钮，不要求精确点击地图热点。

如果想体验参考图式的像素 RPG，打开 `/pixel.html`。这是 Atlas-7 轨道前哨的科幻序章：银河/舱壁背景和白色空间站建筑分层，三步引导先讲清移动、观察、过桥。故事线索会从失联呼叫推进到三枚调查碎片、纠缠能道、量子井回声和未知观察者；地图场景依次为量子前哨、纠缠能道、证据环站。能道不可直接通过，必须走桥；建筑和障碍是独立碰撞对象。PHASE HUD、纠缠轨迹和量子井脉冲是量子风格反馈；点击开始调查后可用右上角音乐开关打开程序化 chiptune 环境音乐。SheNicest 像素徽章和移动控制贴图作为独立 PNG 资源接入。用方向键或 WASD 在地图里走，靠近三枚发光碎片按 E 收集，再去找小满启动量子井；量子井会调用真实 `/api/inquiry`，不是假的剧情数字。

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
| Web 因果学习与 P1/P2 证据 | `cd starter_kit && python3 -m unittest tests.test_web tests.test_inquiry_frontend -v` | Web 集成与前端状态模型覆盖 Quantum World 探究护照、错误结论纠正、六步评委路径、Prompt Contract、`/api/causal-audit`、首门分歧、统计断言、Hybrid trace/path、ProofTrace、安全头与移动端防溢出样式 |
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

1. 完成 Quantum World 的 Bell A/B 探究：先做错误预测，运行实验，再让证据纠正结论并下载可重放护照。
2. 点击 Learn，运行 Bell，读取逐门概率/相位与 ProofTrace 三目标证书；随后进入 Counterfactual Circuit Lab 单独查看 `CX` 对 `X` 与 TV 距离 `0.5`。
3. 点击 Repair 验证错误 QASM 的确定性恢复，再用 Backend Match 询问“免费、零排队、至少 20 比特的模拟器”，核对规范 capability ID。

与十五个公开可审固定提交的逐项映射及仍需外部凭据的材料见 `COMPETITIVE_COVERAGE.md`。该比较只记录 accepted archive 中可复核的事实；私有 12 例 DeepSeek 评测和未公开提交仍然未知。

Web 不接收或保存模型 Key；启动进程只从 `LOOMQ_LLM_*` 读取。未配置模型时，L1 本地实验仍可完整使用。
