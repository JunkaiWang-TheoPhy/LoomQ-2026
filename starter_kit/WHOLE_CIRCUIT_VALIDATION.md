# Whole-Circuit Validation

这份说明只解释 `whole_circuit_validation` 字段代表什么。

## 它检查什么

`whole_circuit_validation` 会对不超过 8 个量子比特的线路做一次有界、可重算的全矩阵比较：

- 逐个计算所有计算基输入列；
- 只接受同一个全局相位；
- 要求终端测量映射完全一致；
- 记录查过多少列、多少个振幅，以及最大绝对误差；
- 容差固定为 `1e-12`。

如果线路含有非终端测量，或测量后还有量子门，这条证据会直接失败关闭。

## 它不是什么

- 它不是无界形式化证明。
- 它不是硬件保真度证明。
- 它不替代 native IR structural round-trip。
- 它不声称“量子线路等价检查”是本项目的研究创新。

本仓库的用法更窄：把一个评委可独立重算的 supporting check 放进 ProofTrace 证书里，用来补足“只看结构回读还不够区分相对相位错误”的空缺。

## 三类证据的边界

1. `local rewrite`
   这是符号恒等式证据。它只覆盖列出的局部重写规则。
2. `whole_circuit_validation`
   这是 `<=8` qubit、`tol=1e-12` 的数值全矩阵重算支持证据。
3. `native IR structural round-trip`
   这是 emitter 输出能被独立 parser 回读成同一 `Circuit` 的结构证据。它仍然是 mandatory。

ProofTrace 只有在这三类证据都满足各自条件时，才把对应结果写进证书。

## 为什么这里引用这两篇论文

我们只引用两篇与“编译验证 / 等价检查”直接相关的 primary sources：

- Giallar: Push-Button Verification for the Qiskit Quantum Compiler
  https://arxiv.org/abs/2205.00661
- Equivalence checking of quantum circuits via intermediary matrix product operator
  https://arxiv.org/abs/2410.10946

前者代表“编译 pass 的自动化验证”这条线；后者代表“量子线路等价检查的可扩展方法”这条线。这里引用它们是为了给评委一个学术坐标，不是为了把本仓库的 bounded recomputation 包装成新的研究结论。
