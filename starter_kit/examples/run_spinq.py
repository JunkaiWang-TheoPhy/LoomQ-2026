#!/usr/bin/env python3
"""
量旋 SpinQit 平台接入最小可跑示例
演示如何导入 OpenQASM 2.0 并使用 SpinQit 运行于本地模拟器。
基于官方文档：spinqit 0.2.x API
"""

import json
import os
import tempfile
from datetime import datetime, timezone

try:
    import spinqit as sq
    from spinqit import BasicSimulatorConfig, get_basic_simulator, get_compiler
except ImportError:
    sq = None


def run_on_spinq_simulator(qasm_str: str, shots: int = 1024) -> dict:
    if sq is None:
        raise RuntimeError("spinqit 未安装；请安装可选厂商 SDK 后运行本示例")

    # 1. 将 QASM 2.0 字符串写入临时文件（QASMCompiler 接受文件路径）
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".qasm", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(qasm_str)
        tmp.close()
        # 2. 使用 QASM 编译器编译为中间表示（IR）
        compiler = get_compiler("qasm")
        ir = compiler.compile(tmp.name, 0)
    finally:
        os.unlink(tmp.name)

    # 3. 初始化 BasicSimulator 后端并配置 shots
    engine = get_basic_simulator()
    config = BasicSimulatorConfig()
    config.configure_shots(shots)

    # 4. 运行程序并获取结果
    result = engine.execute(ir, config)
    # spinqit 0.2.x 的 counts 直接返回二进制字符串 key 格式 {'00': ..., '11': ...}
    counts = result.counts
    provider_job_id = getattr(result, "job_id", None) or getattr(result, "task_id", None)

    return {
        "backend": "spinq_basic_simulator",
        "job_id": str(provider_job_id) if provider_job_id is not None else None,
        "shots": shots,
        "counts": {str(key): value for key, value in counts.items()},
        "bit_order": "little",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "meta": {
            "qubits_count": ir.qnum,
            "execution": "local-simulator",
            "job_id_source": "provider" if provider_job_id is not None else "unavailable",
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
    measure q -> c;
    """
    print("--- 待转译的 QASM 2.0 电路 ---")
    print(qasm_str.strip())
    print("----------------------------")

    res = run_on_spinq_simulator(qasm_str, shots=1024)
    print("\n运行并标准化后的统一输出结果:")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
