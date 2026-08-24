# LoomQ Starter Kit v1.1.0

本工具包定义参赛提交协议，并提供公开自测。它不包含正式评分器、隐藏答案、Mock 得分路径或任何 Level 的参考解答。

运行 `python3 -m starter_kit.loomq.web`，打开 <http://127.0.0.1:8765/>。页面先进入 `Quantum Atlas · 无形世界调查局`：零基础用户从观测站学习四条调查规则，再解锁 Bell 对照实验与证据塔；逐项复核命令见 [`JUDGE_GUIDE.md`](JUDGE_GUIDE.md)，自然语言合同的字段与边界见 [`PROMPT_CONTRACT.md`](PROMPT_CONTRACT.md)。

最快复核只需三步：

1. 核对首屏 OriginQ 与 SpinQ 真机卡的 job ID、结果类型和原始文件。
2. 点击六步按钮，等待状态显示 `6/6`。
3. 沿状态条检查 ProofTrace、首门分歧、断言、Witness Chain、Hybrid 路径和 Prompt Contract。

零基础用户从同一页面的 `Quantum Atlas` 调查地图开始。页面在出现 H/CX 门名之前，先解释状态、多种可能、重复观察和只改一个条件；用户完成简报后才进入分岔原野，留下预测并运行 A/B 实验，最后在证据塔审计结论并取得 `loomq-inquiry-passport-v1` 护照。该路径不要求模型密钥、平台账号或 QASM 知识；地图只是教学隐喻，不作为量子态证据。

## 本 fork 的实现

本 fork 已实现 L1、L2 和 L3：

- L1 使用同一个解析器与 `Circuit` 中间表示生成 SpinQ OpenQASM 2.0、OriginIR 和 Braket OpenQASM 3.0；
- 内置无第三方依赖的状态向量运行时，统一输出 little-endian `counts`；
- ProofTrace 对安全冗余门做命名重写，记录源门到优化门的 lineage，并为三后端输出可下载的确定性证明证书；
- L2 通过 `LOOMQ_LLM_*` 调用组委会提供的模型服务；生成的 QASM 会验证 Bell/GHZ/W、计算基态和均匀叠加目标分布，后端推荐会复核比特数、排队、费用和设备类型；失败时携带诊断重试一次，两次无效回答后才由同一目标/能力表验证器生成安全回退；
- Prompt Contract 在模型调用前抽取 fence 外语义、目标态和后端约束；模型输入与结果验证器共用这份合同，服务端可从原 prompt 重建并核对摘要；
- Quantum Atlas 把 Bell 的 H/CX 问题组织成“背景简报—预测—对照实验—结论审计—护照”闭环；观测站、分岔原野和证据塔由真实完成状态依次解锁，错误结论会引用 A/B 主导态和首门分歧进行纠正，而不是由模型自由评分；
- L2 附带固定种子、可恢复且带完整性哈希的 500 例真实模型压力 campaign，覆盖生成、修复、后端推荐、对抗输入和表述稳定性；
- Witness Chain 用稳定的 `gN/mN` 源操作 ID，把 ProofTrace 谱系、反事实首门分歧、断言测量依赖与 Hybrid 分支 provenance 串成可下载、可重算的审计工件；
- L3 将有界 Hybrid-QASM 经典块解析为 AST，并生成官方轻量模拟器可执行的 RISC-V 控制流；
- Hybrid 路径证书穷举有界 declared clbits，精确处理 mid-circuit measurement 后续量子门，聚合路径概率并标出不可达 outcome 与 dead path；
- Bonus 使用真实 32 位 RISC-V `custom-0` 机器字编码全部 12 门和测量，扩展模拟器完成编码、解码与执行闭环；
- 固定种子离线活动以独立断言执行 40,000 项检查，覆盖 L1、三目标、L3 差分、量子 RISC-V 往返和拒绝路径；
- 零依赖 Web 实验台与命令行入口共同提供 Learn、Build、Repair、Backend Match、电路预览、三后端转译、运行、逐门概率/振幅/相位轨迹和受验证的多轮 Agent 对话。
- Deutsch–Jozsa、两轮 Grover 与 QFT-4 可运行展品同时进入 Web 和三 target 回归；每次转译还会由独立 native-IR 解析器回读并验证语义等价。
- 对 QASM、状态向量和 Hybrid-QASM 设置显式资源上限，恶意超大寄存器或 65 层嵌套会在分配/编译前得到可解释拒绝。

架构与边界见 [`ARCHITECTURE.md`](ARCHITECTURE.md)，固定强对手逐项覆盖见 [`COMPETITIVE_COVERAGE.md`](COMPETITIVE_COVERAGE.md)。

### 零基础首次运行

无需安装第三方包。在 fork 根目录启动本地 Web 实验台：

```bash
python3 -m starter_kit.loomq.web
```

打开 <http://127.0.0.1:8765/>，先在 Quantum Atlas 读完四条调查规则，完成 Bell A/B 探究；再选择 Bell、GHZ、W、均匀叠加、相位干涉、Deutsch–Jozsa、Grover 或 QFT 示例并点击“运行电路”。页面会同时显示量子门时间线、逐门概率/振幅/相位、测量概率、位序解释、目标平台原生指令，以及可下载的 ProofTrace 三后端证明证书；长轨迹默认折叠，服务只监听本机地址。

评委路径不要求先学 QASM。点击首屏六步按钮后，状态条会链接到产生每项结论的页面区域；模型调用是单独的可选步骤。

也可以使用 CLI：

```bash
python3 -m starter_kit.loomq_cli run \
  --target spinq \
  --shots 1024 \
  starter_kit/circuits/bell.qasm
```

输出会显示两个主导态的文本柱状图，并说明经典位序。Bell 电路中 `00` 与 `11` 各占约一半，表示两个量子比特的测量结果相关，而不是两个比特各自独立随机。

逐门查看精确状态向量（也可加 `--json` 交给其他工具）：

```bash
python3 -m starter_kit.loomq_cli trace starter_kit/circuits/bell.qasm
```

把电路转成目标平台指令：

```bash
python3 -m starter_kit.loomq_cli transpile \
  --target braket \
  starter_kit/circuits/ghz3.qasm
```

### 使用自然语言 Agent

本地调试时设置自己的 OpenAI-compatible 服务；不要把 Key 写进文件或命令历史。正式评测由组委会注入同名环境变量。

```bash
export LOOMQ_LLM_BASE_URL=https://api.deepseek.com
export LOOMQ_LLM_API_KEY='<在当前 shell 安全设置>'
export LOOMQ_LLM_MODEL=deepseek-v4-flash
export LOOMQ_LLM_TIMEOUT_SECONDS=55

python3 -m starter_kit.loomq_cli chat \
  生成一个三比特 GHZ 态并测量所有量子比特
```

生成后立即在本地运行并解释结果：

```bash
python3 -m starter_kit.loomq_cli ask \
  --target spinq --shots 1024 \
  生成一个三比特 GHZ 态并测量所有量子比特
```

### 干净环境验证

```bash
python3 starter_kit/verify_submission.py

# 完整开发测试与容器复核
python3 -m unittest discover -s tests -v
(cd starter_kit && python3 -m unittest discover -s tests -v)
python3 starter_kit/evaluator.py --level l1 --target spinq,originq,braket
python3 starter_kit/evaluator.py --level l3
docker build -t loomq-submission starter_kit
docker run --rm loomq-submission

# 无需凭据检查 500 例压力语料；真实模型运行见 L2_STRESS_CAMPAIGN.md
python3 -m starter_kit.scripts.l2_stress_campaign --dry-run

# 校验已归档的 40,000 项离线活动与 120 项 PyQuafu 交叉验证摘要
python3 -m starter_kit.scripts.offline_stress_campaign --validate
python3 -m starter_kit.scripts.quafu_cross_validate --validate
```

上述 Docker 命令是 **L1 隔离环境烟测**，不会假装覆盖需要模型服务的 L2。L2 已在 `submission.yaml` 中声明参赛，正式运行必须由环境注入可用的 `LOOMQ_LLM_*`；仓库级 `tests/test_agent.py` 与 `tests/test_l2_contract.py` 使用本地 HTTP 服务验证真实请求、模型参数、能力表 grounding、QASM 诊断重试和凭据安全，无需把真实 Key 交给测试代码。若要手动运行公开 L2 evaluator，先按“使用自然语言 Agent”设置服务环境，再执行：

```bash
python3 starter_kit/evaluator.py --level l2
```

## 提交结构

```text
starter_kit/
├── __init__.py
├── VERSION
├── CHANGELOG.md
├── submission.yaml
├── adapter.py
├── llm_client.py
├── l2_policy.json
├── evaluator.py
├── prepare_submission.py
├── verify_submission.py
├── bonus_evaluator.py
├── riscv_emulator.py
├── QUANTUM_RISCV_SPEC.md
├── L2_STRESS_CAMPAIGN.md
├── WITNESS_CHAIN.md
├── PYQUAFU_CROSS_VALIDATION.md
├── PROOFTRACE.md
├── JUDGE_GUIDE.md
├── SCIENTIFIC_CLAIMS_AUDIT.md
├── WEB_QA.md
├── backend_capabilities.md
├── backend_capabilities.json
├── QUANTUM_101.md
├── gate_identities.md
├── target_ir_contract.md
├── requirements.txt
├── Dockerfile
├── evidence/
│   ├── README.md
│   └── files/                # 可选附件
├── tests/                    # 随正式提交归档的完整回归测试
├── scripts/                  # 压力活动、交叉验证与真机证据验证器
├── web/                      # 零依赖响应式 Web UI
├── circuits/
│   ├── bell.qasm
│   └── ghz3.qasm
└── examples/
```

在正式 fork 中，本 `starter_kit/` 目录就是构建与评测根目录，必须保留并填写 `submission.yaml`，同时提供 `adapter.py`。非 Python 项目可以在 `adapter.py` 中通过 `subprocess` 调用自己的 CLI 或二进制。

目录名使用下划线，因此从 fork 根目录编写测试时可以按标准 Python 包导入：

```python
from starter_kit import adapter
```

## 环境

公开 evaluator 只使用 Python 标准库，无需安装依赖。推荐 Python 3.10，与官方基础镜像一致（spinqit 最高只提供 cp310 wheel）：

```bash
python3 evaluator.py --level l1 --target spinq,originq --json-out report.json
```

参赛项目使用第三方 SDK 时，必须把依赖写入 `requirements.txt` 并精确锁定版本，例如 `package==1.2.3`。不要提交 `package>=1.2`，正式评测不会替参赛队选择依赖版本。

也可以先验证基础容器：

```bash
docker build -t loomq-submission .
docker run --rm loomq-submission
```

## Adapter 契约

L1 必须实现：

```python
def transpile(qasm_str: str, target: str) -> str: ...
def run(qasm_str: str, target: str, shots: int) -> dict: ...
```

`transpile()` 的三个目标格式不是任意字符串，规范子集见 `target_ir_contract.md`。正式评测会由组织方解析并模拟返回的目标 IR。

L2、L3 为可选接口：

```python
def agent_chat(prompt: str) -> str: ...
def compile_hybrid(hybrid_qasm_str: str) -> tuple[list, str]: ...
```

未参赛的 Level 保持 `NotImplementedError`，并在 `submission.yaml` 中标为 `false`。Starter Kit 原样运行会失败，这是预期行为，也确保原样提交不会获得功能分。

## 公开自测

```bash
# 默认只测试 submission.yaml 中声明为 true 的 Level
python3 evaluator.py --json-out report.json

# 单独测试
python3 evaluator.py --level l1 --target spinq,originq,braket
python3 evaluator.py --level l2
python3 evaluator.py --level l3
python3 bonus_evaluator.py
```

退出码：全部公开测试通过为 `0`，存在失败为 `1`。`report.json` 只表示公开契约自测结果，不是正式分数。

正式评测由组织方在隔离环境运行：每个 case 使用独立进程、私有随机种子和私有期望值；提交进程不会获得理想分布文件。组织方还会分别验证目标原生 IR、真机证据、架构与交互体验。

## 最终提交

截止时间为 **2026-08-25 12:00 UTC+8**。先在 fork 根目录运行：

```bash
python3 starter_kit/prepare_submission.py --team-id <GITHUB_USERNAME>
```

当前不使用预登记队伍名单。每队指定一个 GitHub 提交账号，该账号的用户名就是 Team ID；fork 必须归该账号所有，并由同一账号创建最终提交 Issue。其他成员仍可作为协作者参与开发。预检通过后，在上游 `QAIDAO/LoomQ-2026` 的“LoomQ 最终提交” Issue Form 中填写输出的 fork 地址和 40 位 commit SHA。出现 `submission:accepted` 标签与归档哈希回执后才算提交成功。更新代码后必须新建 Issue，截止前最后一次有效提交生效。

如申报 L1 真机、L2 交互体验、工程与产品化或 Bonus，只需填写 [`evidence/README.md`](evidence/README.md)。截图、原始结果或图表可以统一放入 `evidence/files/`。证据必须随最终 commit 归档；未提交某项证据只影响对应人工分，不影响自动评分。

## L2 统一模型与环境变量

正式 L2 客观评测统一使用 DeepSeek `deepseek-v4-flash`，最终答案仍由确定性的官方测试判定，不使用 LLM 充当裁判。组委会在赛前**不提供 API 地址、API Key、代理或调用额度**。选手本地可使用自己的 DeepSeek API，也可使用其他 OpenAI-compatible 服务调试；组委会只保证正式 DeepSeek 环境下的结果。

`agent_chat(prompt: str) -> str` 接口不变。实现不得硬编码 URL、Key 或模型名，必须读取：

| 环境变量 | 含义 |
|---|---|
| `LOOMQ_LLM_BASE_URL` | OpenAI-compatible API 根地址 |
| `LOOMQ_LLM_API_KEY` | 当前运行凭证 |
| `LOOMQ_LLM_MODEL` | 当前模型；正式评测为 `deepseek-v4-flash` |
| `LOOMQ_LLM_TIMEOUT_SECONDS` | 单次请求超时 |

正式限制为每个 case 时限 120 秒；两组固定私有种子共 12 个 case。机器可读版本见 `l2_policy.json`。

`llm_client.py` 是可选的无依赖传输示例，不包含 Prompt、Agent 策略或参考答案。使用自己的 DeepSeek Key 调试时可设置：

```bash
export LOOMQ_LLM_BASE_URL=https://api.deepseek.com
export LOOMQ_LLM_API_KEY=<YOUR_OWN_KEY>
export LOOMQ_LLM_MODEL=deepseek-v4-flash
export LOOMQ_LLM_TIMEOUT_SECONDS=55
python3 evaluator.py --level l2
```

缺少配置时应立即失败，错误信息不得包含任何 Key。正式评测时，组委会将统一注入 DeepSeek 模型服务及调用预算；评测环境不保证能够访问其他外部网络服务。若参加 L2，请把 `submission.yaml` 中的 `levels.l2` 与 `network.required_for_l2` 同时改为 `true`；`allowed_hosts` 不用于申请正式评测中的任意公网访问。

正式限制是每个 case 总计 120 秒，而 Agent 最多调用模型两次。传输层因此把每次请求配置限制为 `min(LOOMQ_LLM_TIMEOUT_SECONDS, 55)` 秒，使两次请求的配置上限合计 110 秒，并为本地确定性验证留出名义余量；`NaN` 或无穷 timeout 会在发请求前被拒绝。

## 版本政策

合同版本为 `1.0`。开赛后，`1.x` 只允许增加向后兼容的文档、诊断信息和公开测试，不改变已有接口语义；破坏性修改必须发布新的合同版本并为旧版保留评测通道。
