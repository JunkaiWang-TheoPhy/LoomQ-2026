# Witness Chain：跨模块可重算审计链

LoomQ 的 ProofTrace、反事实比较、统计断言与 Hybrid 分支回放原本各有一套索引。Witness Chain 为同一份源电路建立稳定坐标：量子门依次记为 `g1`、`g2`，测量依次记为 `m1`、`m2`。评委因此可以从“哪扇源门首次产生状态分歧”，继续追到“哪些测量进入断言”，再追到“哪个测量影响经典分支”，而不必人工比对四份报告。

## 一键体验

```bash
python3 -m starter_kit.loomq.web
```

打开页面后保留默认 Bell 参考电路、Bell 反例、断言和 Hybrid 程序，点击“生成统一审计链”。页面会显示并下载 `loomq-witness-chain-v1` JSON。默认例中：

- `g2` 是参考 Bell 电路中的 `cx`，也是反事实比较定位的首个分歧门；
- `m1`、`m2` 是 support 断言读取的两个测量 witness；
- Hybrid 的 `if (c[1] == 1)` 映射到 `m2`；
- ProofTrace 的 lineage 与 rewrite source indices 同时带对应 witness ID。

## 可重算与篡改检查

审计 JSON 的 `integrity.audit_sha256` 是去掉 integrity block 和可选 Web `verification` 回执后的规范 JSON SHA-256。验证器不会只比对摘要，还会从嵌入的五类输入重新执行全部工具链并比较完整审计对象；即使修改者篡改语义字段后重新计算摘要，重建比较仍会拒绝：

```python
import json
from pathlib import Path
from starter_kit.loomq.witness import verify_causal_audit

audit = json.loads(Path("loomq-witness-chain.json").read_text(encoding="utf-8"))
print(verify_causal_audit(audit))
```

返回 `valid: true` 表示内容地址、ProofTrace、反事实比较、断言报告与 Hybrid 回放均能从归档代码重建。SHA-256 只用于发现内容篡改，不是数字签名，也不证明作者身份。

## 失败关闭边界

- Hybrid 量子部分必须与参考电路逐操作完全相同，否则拒绝建立跨模块 witness。
- Counterfactual 结构不同时保留 `structural-mismatch`，不虚构首个分歧 witness。
- 首门分歧仍限于最多 8 比特、`|0…0⟩` 输入、忽略全局相位的本地精确比较。
- 断言与 Hybrid provenance 仍只描述软件证据，不把真机偏差归因于具体物理噪声。

该设计建立在 ProofTrace 的可证明重写和来源谱系之上。它不声称发明 proof-carrying compilation、counterfactual debugging 或 provenance；这里实际提供的是一条可下载、可重算、失败关闭的统一审计链，让四种已有证据共享稳定 witness ID。
