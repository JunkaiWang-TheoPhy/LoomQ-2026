# Web 体验验收记录

本记录对应仓库中可直接运行的 `starter_kit/web/`，不是设计稿。验收时间为 2026-08-24（UTC+8），使用本地服务 `python3 -m loomq.web`。

## 自动化合同

```bash
cd starter_kit
python3 -m unittest tests.test_web tests.test_inquiry_frontend -v
```

`tests.test_web`、`tests.test_inquiry_frontend` 与 `tests.test_atlas_game_frontend` 覆盖：Quantum Atlas 三地点解锁、独立 2D 游戏的角色移动/碰撞/近距离交互/任务门和 100 分状态机、锁定路径失败关闭、四条零基础调查规则、延迟展示 H/CX 探究、护照与错误结论纠正、本地资源、四条任务路径、六步评委状态条、Prompt Contract API、反事实首门分歧与结构拒绝、`/api/causal-audit` Witness Chain、三种目标后端、Bell 计数与逐门状态轨迹、Hybrid trace/path、非法输入、20,000 字符 Agent 上限、有界多轮历史、无凭据降级、安全头、favicon 和移动端防溢出样式。协议 fixture 还验证 Web API 到 OpenAI-compatible HTTP 服务再到 `agent_chat` 确定性校验的完整请求链；它不冒充真实 DeepSeek 成绩。

像素版额外覆盖：`/pixel.html` 独立路由、16×16 网格移动、墙体碰撞、碎片拾取、NPC/量子井门槛、像素地图 PNG 静态资源和触屏控制 DOM；像素地图只负责视觉，不替代 `/api/inquiry` 的证据返回。

## 真实浏览器验收

| 场景 | 结果 | 证据 |
|---|---|---|
| Quantum Atlas 旧地图版 | 1440×1000 与 390×844；旧版地点卡链路曾完成真实 API 点击与 visual-verdict `93/100` | 已由 2D 游戏取代；仅作为历史记录，不代表当前画面验收 |
| Quantum Atlas 2D 游戏 | 全屏 Canvas、连续世界、角色移动、动态封锁门、NPC/装置近距离交互；窄屏提供虚拟摇杆与调查按钮 | 状态机、碰撞和静态资源自动化通过；当前版本待人工设备体验 |
| 桌面评委入口 | 1440×1000；页面 `scrollWidth=innerWidth=1440`。证据附录位于首次探究之后、任务卡之前，双入口可直接跳转 | 2026-08-24 Chrome 验收，visual-verdict `93/100` |
| 移动端评委入口 | 390×844；页面 `scrollWidth=innerWidth=390`。真机卡单列，六步状态条横向滚动，不造成页面级横向溢出 | 2026-08-24 Chrome 验收，visual-verdict `93/100` |
| 六步初始状态 | 两个 viewport 重新加载后均为 `未运行 × 6`，没有复用前一会话结果 | 真实浏览器 DOM 读取 |
| 一键本地路径 | 桌面与移动端均完成 `6/6`：三后端回读、第 2 门分歧、3 项 exact-local pass、Witness 重建、Hybrid 语义重算、backend Prompt Contract | 最终代码的真实 Chrome 点击；本机分别约 131 ms 与 137 ms，不作为性能保证 |
| 键盘顺序 | 两个 viewport 依次到达 skip link、brand、Quantum World 双入口、预测/实验/结论控件，再进入证据附录的快速入口、真机卡、六步按钮和状态链接；链接目标均为现有页面区域或固定证据文件 | 2026-08-24 Chrome 连续 `Tab` 复核 |
| Bell 运行 | 1024 shots 输出 `00=512, 11=512`；概率图、文本表、位序说明与原生指令同步更新 | 浏览器 DOM 与 `tests.test_web` |
| ProofTrace | 点击 Run 后 `proof-status=已验证`；下载链接变为 `blob:` 且文件名为 `loomq-prooftrace-*.json` | 本次 Playwright/Chromium 交互与 `tests.test_prooftrace`、`tests.test_web` |
| P1 断言报告 | 默认断言返回 `exact-local`，显示 `3` 条通过结果与“本地精确断言不归因具体噪声机制。” | 本次 Playwright/Chromium 交互与 `tests.test_web`、`tests.test_assertions` |
| P2 Hybrid 回放 | 默认回放显示 `if1:F`、`1` 条分支证据、`6` 条机器事件与 branch/source caveat | 本次 Playwright/Chromium 交互与 `tests.test_web`、`tests.test_hybrid_trace` |
| Hybrid 路径证书 | 点击 `列出所有可能分支` 后可见路径概率、不可达 outcome 和死路径摘要 | `tests.test_web`、`tests.test_hybrid_paths` 与 2026-08-24 Chromium 复核 |
| Prompt Contract | 默认请求显示 `backend`、`originq`、`simulator`、`20`、`免费`、`未要求零排队`、`不需要账号`；服务端重建通过，页面明确摘要不是身份签名 | `/api/prompt-contract` 集成测试、前端字段合同与本次 Chrome 交互 |
| 反事实电路实验 | 默认 Bell 反例显示“第 2 扇门”、参考 `CX q[0], q[1]`、候选 `X q[1]`、最大振幅差 `0.707107`、TV 距离 `0.500000`；结构不同不指认某扇门 | `evidence/files/counterfactual-desktop.jpg`、`counterfactual-mobile.jpg` 与两项 `/api/compare` 集成测试 |
| 逐门状态 | Bell 显示 `|00⟩ → (|00⟩+|01⟩)/√2 → (|00⟩+|11⟩)/√2`；`H-S-S-H` 显示中间相位 `0 → π/2 → π` 并最终得到 `|1⟩` | 浏览器 DOM、`tests.test_state_trace` 与 CLI `trace` |
| 算法画廊 | Deutsch–Jozsa 输出 `11=100%`；Grover 输出 `111=94.53125%`；QFT 为 16 个等概率态且 UI 显示 π/8 相位递进 | 浏览器 DOM 与 `tests.test_algorithm_gallery` |
| 长轨迹 | Bell 等短电路自动展开；40 门 Grover 轨迹默认折叠，用户可用原生 `details/summary` 展开 | 浏览器交互验收 |
| 多轮 Agent | 前四个完成轮次作为 `user/assistant` 交替历史发送；清空按钮立即恢复新会话；畸形或超长历史在调用模型前拒绝 | 本地 OpenAI-compatible 协议 fixture 与 `tests.test_web` |
| Repair 引导 | 点击 Repair 后预填一个越界 CX 的修复任务，并把焦点移到 Agent 输入 | 浏览器交互验收 |
| 无模型凭据 | 显示 `role=alert` 的配置提示，同时明确本地模拟和转译仍可用 | 浏览器交互验收 |
| 控制台与网络 | 两个 viewport 均 `consoleErrors=[]`、`pageErrors=[]`、`requestFailures=[]`、`responseErrors=[]` | 2026-08-24 Chrome 验收 |

## 包容性设计

- 游戏不把 Canvas 作为唯一操作入口：任务、分数、对话、选项与触屏控制均有语义化 DOM；键盘使用 WASD/方向键移动、E/空格交互，窄屏提供虚拟摇杆与独立调查按钮。
- Quantum Atlas 在 H/CX 门名出现前先解释状态、多种可能、重复观察和只改一个条件；简报后才开放预测与 A/B，用户选择结论后才启用护照下载。
- 概率同时用柱图和语义化表格表达；逐门状态还以文本列出概率、振幅和相位，不依赖颜色或图形才能读取。
- Learn 文案区分“模拟得到经典相关性”与“真机纠缠证明”，避免给新手过度结论。
- Counterfactual Circuit Lab 让用户通过删改一扇门学习中间态变化；输出显式限定为 8 比特、零输入、忽略全局相位的本地精确比较，不把它包装成真机噪声诊断。
- Witness Chain 以 `gN/mN` 把 ProofTrace、首门分歧、断言测量位和 Hybrid 分支来源对齐；下载件带可重算 SHA-256，并明确不是身份签名或真机因果证明。
- Repair 和 Backend Match 使用同一个受确定性校验约束的 Agent，而模型不可用时保留完整 L1 本地路径。
- 支持窄屏断点、可见焦点和 `prefers-reduced-motion`。
- 复杂算法不会一次铺满页面；超过 15 个事件的逐门轨迹默认折叠，但内容仍可键盘展开和复制。

## 本轮已知非阻塞风险

- 一键展开全部结果后，页面高度约为桌面 `7058 px`、移动端 `12826 px`。六步状态条提供直接锚点，移动端没有横向溢出；后续压缩只能删重复说明，不能再增加首屏 section。
