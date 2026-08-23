"""Beginner-facing command line interface for LoomQ."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import adapter


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

    chat = commands.add_parser("chat", help="让 Agent 生成、修复 QASM 或推荐后端")
    chat.add_argument("prompt", nargs="+", help="用自然语言描述你的目标")
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
        if args.command == "chat":
            print(adapter.agent_chat(" ".join(args.prompt)))
            return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
