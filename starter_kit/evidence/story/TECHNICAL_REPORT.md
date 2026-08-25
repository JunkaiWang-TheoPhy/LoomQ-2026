# Quantum Atlas 技术报告

## 摘要

Quantum Atlas 在 LoomQ 的既有量子适配器、证书和 Web 实验室之上增加一层故事世界。主线《零点之后的观测者》把“预测—单变量对照—测量—审计”组织成一个新手可以走完的任务。五个地图案件使用同一套服务器端故事合同和 QASM 比较协议，因此故事内容、实验输入和解锁进度可以被复核。

## 交付边界

故事层负责人物、地图、案件、进度和叙事语言。量子层负责 QASM 解析、模拟、counts、state comparison、ProofTrace 和证书。二者之间通过显式 API 连接，不允许插画、对话或模型回答伪造实验结果。

## 核心文件

| 文件 | 作用 |
| --- | --- |
| `starter_kit/loomq/story_world.py` | 主线、五案、解锁协议、确定性 body hash |
| `starter_kit/loomq/web.py` | `/api/story-world`、既有 `/api/compare` 和 `/api/inquiry` |
| `starter_kit/web/game.html` | Quantum Atlas 主游戏页面和案件板 |
| `starter_kit/web/game.js` | 案件板渲染、主线状态刷新、逐案对照实验 |
| `starter_kit/web/game.css` | 案件板、窄屏和键盘焦点样式 |
| `starter_kit/evidence/story/Story.PR` | 评委可直接阅读的完整故事稿 |
| `starter_kit/evidence/story/GAME_CATALOG.md` | 所有游戏入口和主游戏位置 |
| `starter_kit/evidence/story/DEMO_GUIDE.md` | 五分钟演示路径 |

## Story contract

`GET /api/story-world` 返回以下结构：

- `mainline`：`observer-zero` 主线和四步实验节奏；
- `cases`：五个案件，每案包含公开身份、隐藏身份、问题、证据物、reference QASM、variant QASM、changed variable 和 claim boundary；
- `progress`：主线、五案和档案塔的 current、locked 或 complete 状态；
- `integrity.body_sha256`：canonical JSON 内容摘要；
- `completed_node_ids`：当前完成节点，支持确定性重算。

案件顺序固定为：

```text
observer-zero
  ├─ eightieth-year
  ├─ second-badge
  ├─ inside-tide-line
  ├─ night-grid
  └─ testimony-checker
```

完成主线后五案开放。五案归档后，档案塔开放。未知节点、越级完成和篡改 body hash 都会失败关闭。

## 实验协议

主线使用 `/api/inquiry` 的 Bell A/B 任务。它固定保留测量协议，只移除 CX，并从实际 counts 推导观察文字。五案使用各自声明的最小 QASM 对照，通过 `/api/compare` 得到：

- `first_divergent_gate`，首个精确状态分歧；
- `final_distribution_distance`，最终测量分布距离；
- `scope_note`，最多 8 qubits、本地精确比较、全局相位和硬件噪声边界；
- `structural-mismatch` 时的失败原因。

五案的社会问题是叙事问题。电路结果只证明电路结果，不能证明气候政策、劳动公平、人格连续性、能源分配或真实证词的事实真伪。

## 证据完整性

主线实验通过 `loomq-inquiry-passport-v1` 返回 replay request。ProofTrace 为优化和三目标 IR 提供结构谱系、重写记录、三后端回读和全电路语义证书。Witness Chain 将源操作坐标对齐到反事实、断言和 Hybrid provenance。案件层只引用这些可重算接口，不自建第二套物理解释器。

## 复核记录

- 根测试 88 项通过，2 项可选 PyQuafu oracle 跳过；
- Pixel/Atlas 聚焦测试 10/10；
- 五案逐一 POST `/api/compare`，全部返回 200；
- `/game.html`、`/api/story-world`、主线完成后的解锁查询返回 HTTP 200；
- Node checks 覆盖 `game.js`、`pixel.js`、`app.js` 和 Atlas engine；
- `verify_submission.py` 全阶段通过；
- ProofTrace 225/225 mutation、132 rewrite checks、15 portability；
- 所有故事插图均标为叙事资产，不参与科学评分。

## 已知限制

当前五案是证据驱动的故事预告和最小实验入口。它们共享真实比较协议，但还没有把每个社会案件扩展成独立的多轮社会科学模拟器。官方私有 DeepSeek 评测和人工体验分仍由组委会决定，不能从本地测试推断。
