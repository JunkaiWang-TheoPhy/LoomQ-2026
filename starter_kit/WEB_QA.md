# Web 体验验收记录

本记录对应仓库中可直接运行的 `starter_kit/web/`，不是设计稿。验收时间为 2026-08-24（UTC+8），使用本地服务 `python3 -m loomq.web`。

## 自动化合同

```bash
cd starter_kit
python3 -m unittest tests.test_web -v
```

9 项测试覆盖：首页与四条任务路径、三种目标后端、Bell 计数与概率、非法 QASM、畸形 JSON、不支持的方法、20,000 字符 Agent 输入上限、无凭据安全降级，以及成功/失败响应的安全头。

## 真实浏览器验收

| 场景 | 结果 | 证据 |
|---|---|---|
| 桌面首屏 | 1440×1000；四条任务路径和实验台同时可见 | `evidence/files/web-lab-desktop-current.jpg` |
| 移动端首屏 | 390×844；单列任务卡；页面 `scrollWidth=innerWidth=390` | `evidence/files/web-lab-mobile-current.jpg` |
| Bell 运行 | 1024 shots 输出 `00=512, 11=512`；概率图、文本表、位序说明与原生指令同步更新 | 浏览器 DOM 与 `tests.test_web` |
| Repair 引导 | 点击 Repair 后预填一个越界 CX 的修复任务，并把焦点移到 Agent 输入 | 浏览器交互验收 |
| 无模型凭据 | 显示 `role=alert` 的配置提示，同时明确本地模拟和转译仍可用 | 浏览器交互验收 |
| 控制台 | 完整流程无 JavaScript error | 浏览器控制台验收 |

## 包容性设计

- 跳转链接允许键盘用户直达实验区；运行结束后焦点进入结果区。
- 概率同时用柱图和语义化表格表达，不依赖颜色或图形才能读取。
- Learn 文案区分“模拟得到经典相关性”与“真机纠缠证明”，避免给新手过度结论。
- Repair 和 Backend Match 使用同一个受确定性校验约束的 Agent，而模型不可用时保留完整 L1 本地路径。
- 支持窄屏断点、可见焦点和 `prefers-reduced-motion`。
