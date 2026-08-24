# ProofTrace：证明携带的跨后端量子编译

## 目标

普通转译只返回目标文本，评审者无法判断优化改了什么、每个目标门来自哪里，或另外两个后端是否仍能表达同一线路。ProofTrace 在不改变正式 `transpile()` 返回契约的前提下，为一次编译生成确定性、JSON-safe 的证书：

```text
OpenQASM 2.0
  → 有界解析
  → 命名的局部恒等式重写
  → 优化后 Circuit IR
  → whole-circuit bounded recomputation
  → SpinQ / OriginQ / Braket 发射
  → 三种独立 parser 回读
  → SHA-256 + gate lineage + metrics 证书
```

这里引用两篇 primary sources 作为学术背景，而不是把等价检查本身说成我们的研究创新：

- [Giallar: Push-Button Verification for the Qiskit Quantum Compiler](https://arxiv.org/abs/2205.00661)
- [Equivalence checking of quantum circuits via intermediary matrix product operator](https://arxiv.org/abs/2410.10946)

ProofTrace 不声称这些单项技术由本项目首创；本项目做的是把可证明重写、bounded whole-circuit recomputation、三目标回读、来源谱系和可下载证书组合进 LoomQ 的零依赖评委路径。

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

普通 `transpile()` 一对一保留源操作，只编译和校验请求的目标；某个未请求后端的故障不会扩大它的失败面。显式 ProofTrace 接口才执行安全优化、whole-circuit bounded recomputation 和三目标 portability 检查。

## 证明边界

当前优化器只应用相邻、同操作数的恒等式：

| 规则 | 变换 |
|---|---|
| `cancel-self-inverse` | `H H`、`X X`、`CX CX`、`SWAP SWAP`、`CCX CCX` → 空 |
| `cancel-inverse` | `S S†`、`S† S`、`T T†`、`T† T` → 空 |
| `merge-rotations` | 相邻同操作数的 `RZ(a) RZ(b)`、`RY(a) RY(b)`、`CU1(a) CU1(b)` → 参数相加 |
| `cancel-zero-rotation` | 上述参数和精确为浮点零 → 空；非零小角度不会近似删除 |

优化器不交换门，不跨测量重写，也不改变测量的 qubit→clbit 顺序。证书的 `equivalence.scope` 因而写成 `universal-unitary-identities-with-unchanged-measurement-map`。这部分是符号恒等式证据，不是任意规模的形式化等价定理，也不是硬件保真度证明。

`whole_circuit_validation` 是另一层 supporting evidence。它会在 `<=8` qubit、`tol=1e-12` 的范围内重算整条电路的全部计算基列，只接受同一个全局相位，并要求终端测量映射一致。它能抓住“结构回读能过，但相对相位不对”的错误；它仍然不是无界形式化证明。完整边界见 [`WHOLE_CIRCUIT_VALIDATION.md`](WHOLE_CIRCUIT_VALIDATION.md)。

每个最终操作的 `lineage` 都列出对应的源操作索引。每条 `rewrite` 记录规则、输入操作、输出操作和被合并的源索引。`metrics` 分别报告优化前后的 gate count、依赖深度、双比特门、多比特门和测量数。`portability` 对三个目标保存 native IR SHA-256 与独立回读状态。

证书不写入时间戳、账号、Token、job ID 或本地绝对路径；相同输入得到逐字段相同的 JSON。

## 可复现变异基准

```bash
cd starter_kit
python3 -m scripts.prooftrace_benchmark --json
```

固定 corpus 使用 Bell、GHZ、Deutsch–Jozsa、Grover-3 和 QFT-4。对三种目标的优化后 native IR，基准逐条删除 225 条真实指令，并要求两层拒绝同时成立：

- `225/225` structural rejection：独立 parser 回读或结构验证拒绝篡改；
- `225/225` semantic rejection：whole-circuit bounded recomputation 拒绝篡改。

此外还执行 15 项三目标 portability 检查和 132 项安全重写检查，覆盖全部自逆门、相消逆门和参数门。

当前固定结果：

```json
{
  "total_mutants": 225,
  "detected_structure_mutants": 225,
  "detected_semantic_mutants": 225,
  "false_accepts": 0,
  "portability_checks": 15,
  "rewrite_checks": 132,
  "corpus_sha256": "2f8dedadd11c815acb89ef7e5dfc85292420c5a5df81b76bbb4c95ee9d4c8f49"
}
```

这些数字只适用于这组确定性的 native-IR 单指令删除 corpus，不能外推为对所有量子程序错误的 100% 检出率。公开仓库也没有私有 12 例 DeepSeek 评测结果，因此不申报那部分成绩。

## Web 复核

运行 `python3 -m starter_kit.loomq.web`，执行任一示例后展开“ProofTrace · 为什么可信”。页面会把三类证据分开写清：

- 局部重写是符号恒等式证据；
- whole-circuit validation 是 `<=8` qubit、`tol=1e-12` 的全矩阵重算支持证据；
- native IR structural round-trip 仍然必须通过。

页面还会显示查过多少 basis columns、是否存在同一个全局相位、最大误差，以及可下载的完整证书 JSON；服务端不保存下载文件。
