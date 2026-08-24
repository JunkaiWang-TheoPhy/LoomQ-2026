#!/usr/bin/env python3
"""
LoomQ 量子接入平权计划 - 轻量级 RISC-V 寄存器与控制流模拟器

本模拟器用于在本地评估和调试 L3 (量子-经典混合编程) 的经典部分代码。
支持基础的通用寄存器操作和控制流分支跳转指令，无需选手配置重型 QEMU。
"""

import copy
import hashlib
import json
from typing import Dict, List, Tuple, Any, Mapping

class TinyRISCVEmulator:
    def __init__(self):
        # 32个通用寄存器 x0 - x31，x0 恒为 0
        self.registers = [0] * 32
        self.pc = 0
        self.labels: Dict[str, int] = {}
        self.instructions: List[Tuple[str, List[str]]] = []
        self.max_steps = 1000  # 防止死循环
        self.quantum_program = None
        self._program_digest = self._compute_program_digest([], {})

    def set_register(self, reg: str, value: int):
        idx = self._parse_reg_idx(reg)
        if idx != 0:
            self.registers[idx] = value

    def get_register(self, reg: str) -> int:
        idx = self._parse_reg_idx(reg)
        return self.registers[idx]

    def _parse_reg_idx(self, reg: str) -> int:
        reg = reg.strip().replace(",", "")
        if not reg.startswith("x") and not reg.startswith("X"):
            raise ValueError(f"无效的寄存器名称: {reg}")
        idx = int(reg[1:])
        if idx < 0 or idx > 31:
            raise ValueError(f"寄存器索引超出范围 (x0-x31): {reg}")
        return idx

    def load_program(self, asm_code: str):
        """
        解析汇编代码并建立标签索引
        """
        self.instructions = []
        self.labels = {}
        self.pc = 0
        self.registers = [0] * 32
        self._program_digest = self._compute_program_digest([], {})
        
        lines = asm_code.split("\n")
        temp_instructions = []
        
        # 第一次解析：过滤注释、空行并建立指令列表与 Label 映射
        for line in lines:
            line = line.strip()
            # 过滤注释和空行
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            
            # 分割行内注释
            if "#" in line:
                line = line.split("#")[0].strip()
            
            # 提取标签，例如 "LABEL_A:"
            if line.endswith(":"):
                label_name = line[:-1].strip()
                self.labels[label_name] = len(temp_instructions)
                continue
            elif ":" in line:
                # 处理同行的标签，例如 "LOOP: li x1, 10"
                parts = line.split(":", 1)
                label_name = parts[0].strip()
                self.labels[label_name] = len(temp_instructions)
                line = parts[1].strip()
            
            # 解析指令和参数
            tokens = line.replace(",", " ").split()
            op = tokens[0].lower()
            args = tokens[1:]
            temp_instructions.append((op, args))
            
        self.instructions = temp_instructions
        self._program_digest = self._compute_program_digest(self.instructions, self.labels)

    def execute(self) -> Dict[str, int]:
        """
        执行已载入的指令直到程序结束，返回所有寄存器状态字典
        """
        return self._execute(capture_trace=False)

    def execute_with_trace(self) -> Dict[str, Any]:
        """Execute the loaded program and capture an instruction trace keyed by instruction index PCs."""
        return self._execute(capture_trace=True)

    def replay_trace(self, trace: Mapping[str, Any]) -> Dict[str, Any]:
        """Replay a trace against the currently loaded program and reject any integrity mismatch."""
        trace_program_digest = trace.get("program_digest")
        if trace_program_digest != self._program_digest:
            raise ValueError("trace program digest does not match the currently loaded program")

        replay = TinyRISCVEmulator()
        replay.instructions = copy.deepcopy(self.instructions)
        replay.labels = copy.deepcopy(self.labels)
        replay.max_steps = self.max_steps
        replay._program_digest = self._program_digest
        replay.pc = 0
        replay.registers = [0] * 32
        for reg, value in trace.get("initial_registers", {}).items():
            replay.set_register(reg, value)

        expected = replay.execute_with_trace()
        if expected != dict(trace):
            raise ValueError("trace integrity check failed")
        return expected

    def _execute(self, capture_trace: bool):
        steps = 0
        num_instr = len(self.instructions)
        initial_registers = self._sparse_registers()
        events: List[Dict[str, Any]] = []
        branches: List[Dict[str, Any]] = []

        while 0 <= self.pc < num_instr:
            steps += 1
            if steps > self.max_steps:
                raise RuntimeError("程序执行超出最大步数限制，疑似发生死循环")

            pc = self.pc
            op, args = self.instructions[pc]
            next_pc = pc + 1
            register_changes: Dict[str, int] = {}
            branch = None

            if op == "li":
                rd, imm = args[0], int(args[1])
                register_changes = self._write_register(rd, imm)
            elif op == "add":
                rd, rs1, rs2 = args[0], args[1], args[2]
                register_changes = self._write_register(rd, self.get_register(rs1) + self.get_register(rs2))
            elif op == "sub":
                rd, rs1, rs2 = args[0], args[1], args[2]
                register_changes = self._write_register(rd, self.get_register(rs1) - self.get_register(rs2))
            elif op == "addi":
                rd, rs1, imm = args[0], args[1], int(args[2])
                register_changes = self._write_register(rd, self.get_register(rs1) + imm)
            elif op in {"beq", "bne"}:
                rs1, rs2, label = args[0], args[1], args[2]
                target_pc = self._resolve_label(label)
                left = self.get_register(rs1)
                right = self.get_register(rs2)
                taken = left == right if op == "beq" else left != right
                if taken:
                    next_pc = target_pc
                branch = {
                    "kind": "conditional",
                    "registers": [
                        {"name": rs1, "value": left},
                        {"name": rs2, "value": right},
                    ],
                    "target_label": label,
                    "target_pc": target_pc,
                    "taken": taken,
                }
            elif op == "j":
                label = args[0]
                target_pc = self._resolve_label(label)
                next_pc = target_pc
                branch = {
                    "kind": "jump",
                    "target_label": label,
                    "target_pc": target_pc,
                    "taken": True,
                }
            else:
                raise ValueError(f"不支持的指令操作: {op}")

            self.pc = next_pc
            if capture_trace:
                event = {
                    "step": steps,
                    "pc": pc,
                    "operation": op,
                    "args": list(args),
                    "register_changes": register_changes,
                    "branch": branch,
                    "next_pc": next_pc,
                }
                events.append(event)
                if branch is not None:
                    branches.append(copy.deepcopy(event))

        final_registers = self._sparse_registers()
        if not capture_trace:
            return final_registers

        return {
            "schema_version": 1,
            "program_digest": self._program_digest,
            "initial_registers": initial_registers,
            "events": events,
            "branches": branches,
            "final_registers": final_registers,
            "steps": steps,
            "terminated": True,
        }

    def _write_register(self, reg: str, value: int) -> Dict[str, int]:
        idx = self._parse_reg_idx(reg)
        if idx == 0:
            return {}
        self.registers[idx] = value
        return {f"x{idx}": value}

    def _resolve_label(self, label: str) -> int:
        if label not in self.labels:
            raise ValueError(f"未定义的跳转标签: {label}")
        return self.labels[label]

    def _sparse_registers(self) -> Dict[str, int]:
        result = {}
        for idx, val in enumerate(self.registers):
            if val != 0:
                result[f"x{idx}"] = val
        return result

    def _compute_program_digest(self, instructions: List[Tuple[str, List[str]]], labels: Mapping[str, int]) -> str:
        payload = {
            "instructions": [[op, list(args)] for op, args in instructions],
            "labels": sorted(labels.items()),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def load_quantum_program(self, program):
        """Load and decode a 32-bit custom-opcode quantum program."""
        try:
            from .loomq.quantum_riscv import decode_program
        except ImportError:
            from loomq.quantum_riscv import decode_program

        decode_program(program)
        self.quantum_program = program

    def execute_quantum(self, shots: int) -> Dict[str, Any]:
        """Execute the decoded quantum program through LoomQ's exact runtime."""
        if self.quantum_program is None:
            raise RuntimeError("未载入量子 RISC-V 机器码程序")
        try:
            from .loomq.quantum_riscv import CUSTOM_0_OPCODE, decode_program
            from .loomq.runtime import execute
        except ImportError:
            from loomq.quantum_riscv import CUSTOM_0_OPCODE, decode_program
            from loomq.runtime import execute

        circuit = decode_program(self.quantum_program)
        result = execute(circuit, "spinq", shots)
        result["backend"] = "loomq_quantum_riscv"
        result["meta"].update(
            {
                "machine_words": len(self.quantum_program.words),
                "custom_opcode": f"0x{CUSTOM_0_OPCODE:02x}",
            }
        )
        return result

# 简易功能测试
if __name__ == "__main__":
    code = """
    li x1, 5
    li x2, 10
    beq x1, x2, EQUAL
    add x3, x1, x2       # x3 = 15
    j END
    EQUAL:
    sub x3, x2, x1
    END:
    addi x3, x3, 1       # x3 = 16
    """
    emu = TinyRISCVEmulator()
    emu.load_program(code)
    state = emu.execute()
    print("寄存器执行最终状态:", state)
    assert state.get("x3") == 16, "测试失败！"
    print("Tiny RISC-V 模拟器核心测试通过！")
