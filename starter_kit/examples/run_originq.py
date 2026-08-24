#!/usr/bin/env python3
"""
本源量子 pyqpanda 平台接入最小可跑示例
演示如何导入 OpenQASM 2.0 字符串，转译为本源量子程序，并运行在 CPU 模拟器上。
"""

import json
import re
from datetime import datetime, timezone

try:
    import pyqpanda as pq
except ImportError:
    # 允许没有安装 pyqpanda 时仅做语法和结构提示
    pq = None


def _normalize_counts(raw_counts: dict, num_bits: int) -> dict:
    """Normalize SDK count keys without treating binary strings as decimal."""
    formatted_counts = {}
    for key, value in raw_counts.items():
        if isinstance(key, int):
            normalized = format(key, f"0{num_bits}b")
        elif isinstance(key, str) and re.fullmatch(r"[01]+", key):
            normalized = key.zfill(num_bits)
        elif isinstance(key, str) and key.isdigit():
            normalized = format(int(key), f"0{num_bits}b")
        else:
            normalized = str(key)
        formatted_counts[normalized] = formatted_counts.get(normalized, 0) + value
    return formatted_counts

def run_on_originq_simulator(qasm_str: str, shots: int = 1024) -> dict:
    if pq is None:
        raise RuntimeError("pyqpanda 未安装；请安装可选厂商 SDK 后运行本示例")

    # 1. 初始化量子虚拟机器 (QVM)
    machine = pq.CPUQVM()
    machine.init_qvm()

    # 2. 转换 QASM 2.0 字符串为 pyqpanda 内部的 QProg (量子程序)
    # pyqpanda 支持通过 convert_qasm_to_qprog 或 convert_qasm_string_to_qprog 导入 QASM
    try:
        # 兼容不同版本 pyqpanda 接口
        if hasattr(pq, 'convert_qasm_string_to_qprog'):
            prog, qreg, creg = pq.convert_qasm_string_to_qprog(qasm_str, machine)
        else:
            prog = pq.convert_qasm_to_qprog(qasm_str, machine)
            # 如果接口只返回 prog，需要从机器获取比特列表
            qreg = machine.get_allocate_qubits()
            creg = machine.get_allocate_cbits()
    except Exception as e:
        raise RuntimeError(f"QASM 转译失败，请检查语法兼容性: {e}")

    # 3. 运行线路
    # 使用 run_with_configuration 进行多次测量采样 (shots)
    result = machine.run_with_configuration(prog, creg, shots)
    
    # 4. 统计结果
    # pyqpanda 返回的 counts 是以十进制或二进制字符串作为 key
    # 我们确保将其标准化为二进制 key，如 "00", "11"
    # 获取比特总数，以便将十进制格式化为对应长度的二进制串
    num_bits = len(creg)
    formatted_counts = _normalize_counts(result, num_bits)

    # 5. 释放量子虚拟机器资源
    machine.finalize()

    return {
        "backend": "originq_cpu_simulator",
        "job_id": None,
        "shots": shots,
        "counts": formatted_counts,
        "bit_order": "little",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "meta": {
            "qubits_count": num_bits,
            "depth": "N/A (Local Simulator)",
            "execution": "local-simulator",
            "job_id_source": "unavailable",
            "timestamp_source": "local-observation",
        }
    }

def main():
    qasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg c[2];
    h q[0];
    cx q[0],q[1];
    measure q[0] -> c[0];
    measure q[1] -> c[1];
    """
    print("--- 待转译的 QASM 2.0 电路 ---")
    print(qasm_str.strip())
    print("----------------------------")

    res = run_on_originq_simulator(qasm_str, shots=1024)
    print("\n运行并标准化后的统一输出结果:")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
