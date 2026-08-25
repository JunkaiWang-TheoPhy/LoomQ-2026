# Quantum Atlas 游戏与实验入口

这份目录告诉评委每个入口在哪里，以及它和真实证据接口的关系。地图、插画和角色是叙事层；实验结果仍由服务器端的 LoomQ 接口返回。

## 主游戏

### Quantum Atlas · 无形世界调查局

位置：`starter_kit/web/game.html`
启动地址：`http://127.0.0.1:8767/game.html`

这是主游戏，也是《零点之后的观测者》的可玩入口。玩家从观测站出发，先收集四条调查方法，再留下预测，运行 Bell A/B 对照实验，前往证据塔审计结论。

主线完成后，右侧案件板从 `GET /api/story-world` 读取五个案件，并按以下顺序开放：

1. 《她的第八十年》
2. 《第二个工牌》
3. 《潮线以内》
4. 《电网的夜班》
5. 《证词校验器》

点击已开放案件，可以运行它自己的最小 QASM 对照。前端调用 `/api/compare`，展示首个分歧门、最终分布距离和 scope boundary。案件故事不能直接把量子实验结果解释成社会结论。

## 像素 RPG 支线

位置：`starter_kit/web/pixel.html`
启动地址：`http://127.0.0.1:8767/pixel.html`

这是较轻量的像素支线，强调人物、移动、碰撞和近距离交互。它和主游戏共享调查方法、证据护照和故事世界语义，但不替代主游戏的完整实验路径。

## 原证据实验室

位置：`starter_kit/web/index.html`
启动地址：`http://127.0.0.1:8767/`

这是技术优先入口，适合评委直接查看：

- 概率柱图和 counts；
- 逐门 state trace；
- Inquiry Passport；
- ProofTrace；
- Witness Chain；
- Counterfactual Circuit Lab；
- Hybrid path certificate；
- RISC-V trace；
- 真机证据和边界声明。

## 入口关系

```text
game.html
  ├─ /api/inquiry       主线预测—对照—审计—护照
  ├─ /api/story-world   五案目录、解锁进度、内容地址
  └─ /api/compare       五案最小 QASM 对照

pixel.html              角色与地图支线

index.html
  ├─ /api/run
  ├─ /api/assert
  ├─ /api/hybrid-paths
  ├─ /api/prompt-contract
  └─ ProofTrace / Witness / RISC-V / 真机证据
```

## 评委最短路径

1. 启动 `python3 -m loomq.web --host 127.0.0.1 --port 8767`。
2. 打开 `/game.html`。
3. 完成主线调查，查看五案案件板。
4. 点击《她的第八十年》，运行最小对照实验。
5. 点击 `/` 查看完整证书和边界。
