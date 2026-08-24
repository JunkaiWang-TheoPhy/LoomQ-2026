# L2 真实模型压力 Campaign

`scripts/l2_stress_campaign.py` 提供固定种子、可断点续跑且可校验的 500 例
L2 压力测试。它调用公开的 `adapter.agent_chat()`，不会绕过正式模型链路；每个回复
仍由提交中的 QASM 语法、目标态分布或后端能力表校验器判定。

## 覆盖范围

| 类别 | 数量 | 覆盖内容 |
|---|---:|---|
| generation | 150 | Bell、GHZ、W、计算基态、均匀叠加，中英文与不同比特数 |
| repair | 150 | 非白名单门、越界、缺测量、寄存器错误和目标态错误 |
| backend | 120 | 比特数、免费、零排队、QPU 与 simulator 组合约束 |
| adversarial | 50 | 冲突指令、伪造 job ID、泄露凭据和绕过门集等诱导 |
| stability | 30 | 同一目标的多种表述、修复与推荐一致性 |

固定 seed 为 `20260824`。完整语料由代码生成，必须同时满足 500 个唯一 case ID
与 500 条唯一 prompt；`--dry-run` 会在不读取凭据、不调用模型的情况下检查这些约束。

```bash
python3 -m starter_kit.scripts.l2_stress_campaign --dry-run
```

## 运行真实模型

凭据只通过正式的 `LOOMQ_LLM_*` 环境变量注入：

```bash
export LOOMQ_LLM_BASE_URL=https://api.deepseek.com
export LOOMQ_LLM_API_KEY='<仅在当前 shell 中设置>'
export LOOMQ_LLM_MODEL=deepseek-v4-flash
export LOOMQ_LLM_TIMEOUT_SECONDS=55

python3 -m starter_kit.scripts.l2_stress_campaign \
  --output-dir starter_kit/evidence/files/l2-stress
```

中途中断后使用同一输出目录继续；已经通过且摘要哈希仍有效的 case 不会重复请求：

```bash
python3 -m starter_kit.scripts.l2_stress_campaign \
  --output-dir starter_kit/evidence/files/l2-stress \
  --resume
```

## 证据边界与校验

记录文件不保存原始 prompt、原始模型回答、API Key 或完整 endpoint，只保存 case/category、
prompt 与回复的 SHA-256、回复字符数、耗时、通过状态和脱敏诊断。每条记录还有覆盖整条记录的
`record_sha256`，摘要再绑定整个 JSONL 的 SHA-256。以下命令会重新生成固定语料，
检查 prompt 映射、逐条摘要、文件摘要以及分类计数：

```bash
python3 -m starter_kit.scripts.l2_stress_campaign \
  --output-dir starter_kit/evidence/files/l2-stress \
  --validate
```

`passed=true` 表示本次选中的 case 全部通过；只有 `complete_corpus=true` 且
`total_cases=500` 才表示完整 campaign 已经执行。真实模型报告是参赛者侧鲁棒性证据，
不替代组委会的 12 个私有 case，也不应表述成官方得分。
