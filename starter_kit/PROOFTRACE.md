# ProofTrace：证明携带的跨后端量子编译

## 目标

普通转译只返回目标文本，评审者无法判断优化改了什么、每个目标门来自哪里，或另外两个后端是否仍能表达同一线路。ProofTrace 在不改变正式 `transpile()` 返回契约的前提下，为一次编译生成确定性、JSON-safe 的证书：

```text
OpenQASM 2.0
  → 有界解析
  → 命名的局部恒等式重写
  → 优化后 Circuit IR
  → SpinQ / OriginQ / Braket 发射
  → 三种独立 parser 回读
  → SHA-256 + gate lineage + metrics 证书
```

它受近年“工具增强量子代码生成、执行反馈、编译验证与 gate lineage”工作的启发，包括 [QUASAR](https://arxiv.org/abs/2510.00967)、[QuanBench+](https://arxiv.org/abs/2604.08570)、[Qompiler](https://arxiv.org/abs/2509.16272) 与[参数化量子线路等价检查](https://arxiv.org/abs/2404.18456)。这些工作分别说明了执行验证、多框架可靠性、门来源追踪和参数线路验证的重要性。ProofTrace 不声称这些单项技术由本项目首创；本项目的贡献是把可证明重写、三目标回读、来源谱系和评委可下载证书组合进 LoomQ 的零依赖评分路径。

## 公共接口

正式契约保持不变：

```python
native_ir = adapter.transpile(qasm_str, "spinq")
```

需要证书的工具和 Web 使用显式接口：

```python
native_ir, certificate = adapter.transpile_with_proof(qasm_str, "spinq")
certificate_only = adapter.prooftrace(qasm_str, "spinq")
```

普通 `transpile()` 一对一保留源操作，只编译和校验请求的目标；某个未请求后端的故障不会扩大它的失败面。显式 ProofTrace 接口才执行安全优化和三目标 portability 检查。

## 证明边界

当前优化器只应用相邻、同操作数的恒等式：

| 规则 | 变换 |
|---|---|
| `cancel-self-inverse` | `H H`、`X X`、`CX CX`、`SWAP SWAP`、`CCX CCX` → 空 |
| `cancel-inverse` | `S S†`、`S† S`、`T T†`、`T† T` → 空 |
| `merge-rotations` | 相邻同操作数的 `RZ(a) RZ(b)`、`RY(a) RY(b)`、`CU1(a) CU1(b)` → 参数相加 |
| `cancel-zero-rotation` | 上述参数和精确为浮点零 → 空；非零小角度不会近似删除 |

优化器不交换门，不跨测量重写，也不改变测量的 qubit→clbit 顺序。证书的 `equivalence.scope` 因而写成 `universal-unitary-identities-with-unchanged-measurement-map`。它证明的是列出的数学恒等式及未改动的测量序列，不是任意规模的形式化等价定理，也不是硬件保真度证明。

每个最终操作的 `lineage` 都列出对应的源操作索引。每条 `rewrite` 记录规则、输入操作、输出操作和被合并的源索引。`metrics` 分别报告优化前后的 gate count、依赖深度、双比特门、多比特门和测量数。`portability` 对三个目标保存 native IR SHA-256 与独立回读状态。

证书不写入时间戳、账号、Token、job ID 或本地绝对路径；相同输入得到逐字段相同的 JSON。

## 可复现变异基准

```bash
cd starter_kit
python3 -m scripts.prooftrace_benchmark --json
```

固定 corpus 使用 Bell、GHZ、Deutsch–Jozsa、Grover-3 和 QFT-4。对三种目标的优化后 native IR，基准逐条删除 225 条真实指令并要求独立 parser/语义比较拒绝篡改；同时执行 15 项三目标 portability 检查和 132 项安全重写检查，覆盖全部自逆门、相消逆门和参数门。

当前固定结果：

```json
{
  "total_mutants": 225,
  "detected_mutants": 225,
  "false_accepts": 0,
  "portability_checks": 15,
  "rewrite_checks": 132,
  "corpus_sha256": "2f8dedadd11c815acb89ef7e5dfc85292420c5a5df81b76bbb4c95ee9d4c8f49"
}
```

`225/225` 只适用于这组确定性的 native-IR 单指令删除 corpus，不能外推为对所有量子程序错误的 100% 检出率。基准没有模型凭据，因此也不申报真实 DeepSeek 修复率。

## Web 复核

运行 `python3 -m starter_kit.loomq.web`，执行任一示例后展开“ProofTrace · 为什么可信”。页面显示三目标回读、门数/深度/双比特门变化、重写规则和来源覆盖，并可在浏览器内下载证书 JSON；服务端不保存下载文件。
