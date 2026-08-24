# Web 体验验收记录

本记录对应仓库中可直接运行的 `starter_kit/web/`，不是设计稿。验收时间为 2026-08-24（UTC+8），使用本地服务 `python3 -m loomq.web`。

## 自动化合同

```bash
cd starter_kit
python3 -m unittest tests.test_web -v
```

27 项测试覆盖：首页与四条任务路径、首屏证据导航顺序、3 个固定锚点、反事实首门分歧与结构不可比防护、`/api/causal-audit` Witness Chain、三种目标后端、Bell 计数与逐门状态轨迹、前端振幅渲染与清空会话合同、超过 8 比特时的可恢复轨迹边界、非法 QASM、畸形 JSON、不支持的方法、20,000 字符 Agent 输入上限、严格交替且最多 8 条的多轮历史、无凭据安全降级、安全头、favicon 资源、证据面板的移动端防溢出样式，以及 Web API → OpenAI-compatible HTTP 服务 → `agent_chat` 确定性校验的完整链路。协议 fixture 分别通过生成、修复和后端选择三类任务；它验证真实网络协议，不冒充真实 DeepSeek 成绩。

## 真实浏览器验收

| 场景 | 结果 | 证据 |
|---|---|---|
| 桌面首屏 | 1440×1000；页面 `scrollWidth=innerWidth=1440`，无横向溢出；首屏先出现证据清单，再出现任务卡片 | 2026-08-24 Chromium 1440 验收，visual-verdict `92/100` |
| 移动端首屏 | 390×844；页面 `scrollWidth=innerWidth=390`，证据区单列且无横向溢出 | 2026-08-24 Chromium 390 验收，visual-verdict `92/100` |
| 键盘首屏顺序 | 在 1440×1000 与 390×844 下，连续 5 次 `Tab` 依次到达 skip link、brand、`1 分钟看证据`、`3 分钟跑示例`、`查看原始材料`；第 5 个链接指向 fork 内的 evidence 目录 | 2026-08-24 Chromium 键盘验收 |
| Bell 运行 | 1024 shots 输出 `00=512, 11=512`；概率图、文本表、位序说明与原生指令同步更新 | 浏览器 DOM 与 `tests.test_web` |
| ProofTrace | 点击 Run 后 `proof-status=已验证`；下载链接变为 `blob:` 且文件名为 `loomq-prooftrace-*.json` | 本次 Playwright/Chromium 交互与 `tests.test_prooftrace`、`tests.test_web` |
| P1 断言报告 | 默认断言返回 `exact-local`，显示 `3` 条通过结果与“本地精确断言不归因具体噪声机制。” | 本次 Playwright/Chromium 交互与 `tests.test_web`、`tests.test_assertions` |
| P2 Hybrid 回放 | 默认回放显示 `if1:F`、`1` 条分支证据、`6` 条机器事件与 branch/source caveat | 本次 Playwright/Chromium 交互与 `tests.test_web`、`tests.test_hybrid_trace` |
| Hybrid 路径证书 | 点击 `列出所有可能分支` 后可见路径概率、不可达 outcome 和死路径摘要 | `tests.test_web`、`tests.test_hybrid_paths` 与 2026-08-24 Chromium 复核 |
| 反事实电路实验 | 默认 Bell 反例显示“第 2 扇门”、参考 `CX q[0], q[1]`、候选 `X q[1]`、最大振幅差 `0.707107`、TV 距离 `0.500000`；结构不同不指认某扇门 | `evidence/files/counterfactual-desktop.jpg`、`counterfactual-mobile.jpg` 与两项 `/api/compare` 集成测试 |
| 逐门状态 | Bell 显示 `|00⟩ → (|00⟩+|01⟩)/√2 → (|00⟩+|11⟩)/√2`；`H-S-S-H` 显示中间相位 `0 → π/2 → π` 并最终得到 `|1⟩` | 浏览器 DOM、`tests.test_state_trace` 与 CLI `trace` |
| 算法画廊 | Deutsch–Jozsa 输出 `11=100%`；Grover 输出 `111=94.53125%`；QFT 为 16 个等概率态且 UI 显示 π/8 相位递进 | 浏览器 DOM 与 `tests.test_algorithm_gallery` |
| 长轨迹 | Bell 等短电路自动展开；40 门 Grover 轨迹默认折叠，用户可用原生 `details/summary` 展开 | 浏览器交互验收 |
| 多轮 Agent | 前四个完成轮次作为 `user/assistant` 交替历史发送；清空按钮立即恢复新会话；畸形或超长历史在调用模型前拒绝 | 本地 OpenAI-compatible 协议 fixture 与 `tests.test_web` |
| Repair 引导 | 点击 Repair 后预填一个越界 CX 的修复任务，并把焦点移到 Agent 输入 | 浏览器交互验收 |
| 无模型凭据 | 显示 `role=alert` 的配置提示，同时明确本地模拟和转译仍可用 | 浏览器交互验收 |
| 控制台与网络 | `errors=[]`；无 console/page/network 错误；favicon 不再产生 404 | 2026-08-24 Chromium 验收 |

## 包容性设计

- 跳转链接允许键盘用户直达实验区；运行结束后焦点进入结果区。
- 概率同时用柱图和语义化表格表达；逐门状态还以文本列出概率、振幅和相位，不依赖颜色或图形才能读取。
- Learn 文案区分“模拟得到经典相关性”与“真机纠缠证明”，避免给新手过度结论。
- Counterfactual Circuit Lab 让用户通过删改一扇门学习中间态变化；输出显式限定为 8 比特、零输入、忽略全局相位的本地精确比较，不把它包装成真机噪声诊断。
- Witness Chain 以 `gN/mN` 把 ProofTrace、首门分歧、断言测量位和 Hybrid 分支来源对齐；下载件带可重算 SHA-256，并明确不是身份签名或真机因果证明。
- Repair 和 Backend Match 使用同一个受确定性校验约束的 Agent，而模型不可用时保留完整 L1 本地路径。
- 支持窄屏断点、可见焦点和 `prefers-reduced-motion`。
- 复杂算法不会一次铺满页面；超过 15 个事件的逐门轨迹默认折叠，但内容仍可键盘展开和复制。

## 本轮已知非阻塞风险

- 移动端总页面高度从约 `7.4k px` 增长到约 `8.1k px`。当前 verdict 仍通过，滚动与布局也没有溢出，但后续如果继续压缩首屏材料，优先从重复说明而不是再加新 section 下手。
