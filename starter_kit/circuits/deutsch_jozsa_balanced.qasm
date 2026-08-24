OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[2];

// Two input qubits and one |-> ancilla.
x q[2];
h q[0];
h q[1];
h q[2];

// Balanced oracle f(x0,x1) = x0 XOR x1.
cx q[0],q[2];
cx q[1],q[2];

h q[0];
h q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
