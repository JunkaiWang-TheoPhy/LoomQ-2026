# Web 体验验收记录

本记录对应仓库中可直接运行的 `starter_kit/web/`，不是设计稿。验收时间为 2026-08-24（UTC+8），使用本地服务 `python3 -m loomq.web`。

## 自动化合同

```bash
cd starter_kit
python3 -m unittest tests.test_web -v
```

14 项测试覆盖：首页与四条任务路径、三种目标后端、Bell 计数与逐门状态轨迹、前端振幅渲染与清空会话合同、超过 8 比特时的可恢复轨迹边界、非法 QASM、畸形 JSON、不支持的方法、20,000 字符 Agent 输入上限、严格交替且最多 8 条的多轮历史、无凭据安全降级、安全头，以及 Web API → OpenAI-compatible HTTP 服务 → `agent_chat` 确定性校验的完整链路。协议 fixture 分别通过生成、修复和后端选择三类任务；它验证真实网络协议，不冒充真实 DeepSeek 成绩。

## 真实浏览器验收

| 场景 | 结果 | 证据 |
|---|---|---|
| 桌面首屏 | 1440×1000；四条任务路径和实验台同时可见 | `evidence/files/web-lab-desktop-current.jpg` |
| 移动端首屏 | 390×844；单列任务卡；页面 `scrollWidth=innerWidth=390` | `evidence/files/web-lab-mobile-current.jpg` |
| Bell 运行 | 1024 shots 输出 `00=512, 11=512`；概率图、文本表、位序说明与原生指令同步更新 | 浏览器 DOM 与 `tests.test_web` |
| 逐门状态 | Bell 显示 `|00⟩ → (|00⟩+|01⟩)/√2 → (|00⟩+|11⟩)/√2`；`H-S-S-H` 显示中间相位 `0 → π/2 → π` 并最终得到 `|1⟩` | 浏览器 DOM、`tests.test_state_trace` 与 CLI `trace` |
| 算法画廊 | Deutsch–Jozsa 输出 `11=100%`；Grover 输出 `111=94.53125%`；QFT 为 16 个等概率态且 UI 显示 π/8 相位递进 | 浏览器 DOM 与 `tests.test_algorithm_gallery` |
| 长轨迹 | Bell 等短电路自动展开；40 门 Grover 轨迹默认折叠，用户可用原生 `details/summary` 展开 | 浏览器交互验收 |
| 多轮 Agent | 前四个完成轮次作为 `user/assistant` 交替历史发送；清空按钮立即恢复新会话；畸形或超长历史在调用模型前拒绝 | 本地 OpenAI-compatible 协议 fixture 与 `tests.test_web` |
| Repair 引导 | 点击 Repair 后预填一个越界 CX 的修复任务，并把焦点移到 Agent 输入 | 浏览器交互验收 |
| 无模型凭据 | 显示 `role=alert` 的配置提示，同时明确本地模拟和转译仍可用 | 浏览器交互验收 |
| 控制台 | 完整流程无 JavaScript error | 浏览器控制台验收 |

## 包容性设计

- 跳转链接允许键盘用户直达实验区；运行结束后焦点进入结果区。
- 概率同时用柱图和语义化表格表达；逐门状态还以文本列出概率、振幅和相位，不依赖颜色或图形才能读取。
- Learn 文案区分“模拟得到经典相关性”与“真机纠缠证明”，避免给新手过度结论。
- Repair 和 Backend Match 使用同一个受确定性校验约束的 Agent，而模型不可用时保留完整 L1 本地路径。
- 支持窄屏断点、可见焦点和 `prefers-reduced-motion`。
- 复杂算法不会一次铺满页面；超过 15 个事件的逐门轨迹默认折叠，但内容仍可键盘展开和复制。
