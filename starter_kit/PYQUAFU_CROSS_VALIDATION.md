# PyQuafu 独立数值交叉验证

核心评分路径只依赖 Python 标准库。本验证在隔离环境安装 `pyquafu==0.4.5`，用独立维护的 PyQuafu 状态向量引擎复核 LoomQ，不把 Quafu 当成 SpinQ、OriginQ 或 Braket 真机。

## 固定协议

- seed：`20260824`
- 40 个唯一三比特电路，每个 18 门
- 全部 12 个赛题白名单门均出现
- 每个电路检查三个 LoomQ target，共 120 项
- 状态向量先对齐不可观测的全局相位，再要求最大振幅误差不超过 `1e-9`
- 每个 target 使用 997 shots；由于两个数学等概率态可能因 `~1e-15` 浮点差异交换最大余数的最后一枚 shot，counts 允许 L1 距离不超过 2，即最多一枚 shot 换位
- 语料 SHA-256：`fa7328082a572c99a1b7b51af79b68faaf4647f037ae0dc112669098432e1c64`

## 2026-08-24 结果

真实 PyQuafu 0.4.5 运行得到 120/120 通过，最大振幅误差为 `1.1802326323952682e-15`，最大 counts L1 距离为 2。机器可读摘要位于 `evidence/files/pyquafu-cross-validation-summary.json`。

首次严格使用 counts 字典相等时有 18/120 项失败：涉及 6 个电路，状态向量误差仍只有 `1.1e-16` 到 `3.4e-16`，每项都只是一枚 shot 在并列余数态之间换位。现有判据保留状态向量严格阈值，并把 counts 容差显式限制为“一枚 shot”，没有删除或隐藏该数值边界。

## 复现

```bash
python3.11 -m venv .venv-quafu
.venv-quafu/bin/python -m pip install pyquafu==0.4.5
.venv-quafu/bin/python -m starter_kit.scripts.quafu_cross_validate
python3 -m starter_kit.scripts.quafu_cross_validate --validate
```

最后一条命令无需安装 PyQuafu，只验证已归档摘要与固定语料、门集、目标数、误差阈值和完整通过计数一致；重新计算数值结果需要 PyQuafu。
