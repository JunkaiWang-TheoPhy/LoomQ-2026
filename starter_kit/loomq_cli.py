"""Beginner-facing command line interface for LoomQ."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence

from . import adapter
from .loomq.qasm import parse_qasm
from .loomq.simulator import trace_statevector


def _read_qasm(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _render_counts(payload: dict) -> str:
    counts = payload["counts"]
    maximum = max(counts.values())
    lines = [
        f"后端：{payload['backend']}",
        f"采样次数：{payload['shots']}",
        "结果（位串最右侧是 c[0]）：",
    ]
    for state, count in sorted(counts.items()):
        width = round(32 * count / maximum) if maximum else 0
        ratio = count / payload["shots"]
        lines.append(f"{state} | {'█' * width:<32} {count:>6}  {ratio:6.2%}")
    lines.append("提示：柱越长，测得该状态的次数越多。")
    return "\n".join(lines)


def _extract_qasm(reply: str) -> str:
    match = re.search(
        r"OPENQASM\s+2\.0;.*?(?=^\s*```|\Z)",
        reply,
        re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        raise ValueError("Agent 回答中没有可运行的 OpenQASM 2.0 程序")
    return match.group(0).strip()


def _render_trace(events: list[dict]) -> str:
    lines = ["逐门状态故事（精确状态向量；φ 为弧度）："]
    for index, event in enumerate(events):
        operation = event["operation"]
        kind = operation["kind"]
        if kind == "initial":
            title = "初始态 |0…0⟩"
        elif kind == "measure":
            title = "测量映射"
        else:
            qubits = ", ".join(f"q[{qubit}]" for qubit in operation["qubits"])
            title = f"{operation['gate'].upper()} · {qubits}"
        lines.append(f"{index:02d} · {title}")
        lines.append(f"     {event['explanation']}")
        for state in event["states"]:
            lines.append(
                f"     |{state['basis']}⟩ P={state['probability']:.2%} "
                f"amp={state['amplitude_real']:+.4f}{state['amplitude_imag']:+.4f}i "
                f"φ={state['phase_radians']:+.4f}"
            )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loomq",
        description="用统一接口转译、运行并理解量子电路。QASM 文件可写为 - 以从标准输入读取。",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    transpile = commands.add_parser("transpile", help="把 OpenQASM 2.0 转成目标平台指令")
    transpile.add_argument("qasm", help="OpenQASM 2.0 文件路径，或 -")
    transpile.add_argument("--target", choices=adapter.SUPPORTED_TARGETS, required=True)

    run = commands.add_parser("run", help="在统一的本地状态向量引擎中运行电路")
    run.add_argument("qasm", help="OpenQASM 2.0 文件路径，或 -")
    run.add_argument("--target", choices=adapter.SUPPORTED_TARGETS, required=True)
    run.add_argument("--shots", type=int, default=8192)
    run.add_argument("--json", action="store_true", help="输出机器可读 JSON")

    trace = commands.add_parser("trace", help="逐门查看概率、振幅与相位如何变化")
    trace.add_argument("qasm", help="OpenQASM 2.0 文件路径，或 -")
    trace.add_argument("--json", action="store_true", help="输出机器可读 JSON")

    chat = commands.add_parser("chat", help="让 Agent 生成、修复 QASM 或推荐后端")
    chat.add_argument("prompt", nargs="+", help="用自然语言描述你的目标")

    ask = commands.add_parser("ask", help="从自然语言生成电路并立即在本地验证")
    ask.add_argument("prompt", nargs="+", help="用自然语言描述希望运行的量子电路")
    ask.add_argument("--target", choices=adapter.SUPPORTED_TARGETS, default="spinq")
    ask.add_argument("--shots", type=int, default=1024)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "transpile":
            print(adapter.transpile(_read_qasm(args.qasm), args.target), end="")
            return 0
        if args.command == "run":
            payload = adapter.run(_read_qasm(args.qasm), args.target, args.shots)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            else:
                print(_render_counts(payload))
            return 0
        if args.command == "trace":
            events = trace_statevector(parse_qasm(_read_qasm(args.qasm)))
            if args.json:
                print(json.dumps(events, ensure_ascii=False, sort_keys=True))
            else:
                print(_render_trace(events))
            return 0
        if args.command == "chat":
            print(adapter.agent_chat(" ".join(args.prompt)))
            return 0
        if args.command == "ask":
            reply = adapter.agent_chat(" ".join(args.prompt))
            qasm = _extract_qasm(reply)
            payload = adapter.run(qasm, args.target, args.shots)
            print("Agent 生成并通过语义检查的电路：")
            print(qasm)
            print()
            print(_render_counts(payload))
            print("自然语言目标已经转换并完成本地验证；无需云平台账号。")
            return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
