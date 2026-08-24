OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];

// Uniform search state.
h q[0];
h q[1];
h q[2];

// Iteration 1: phase-mark |111>, then reflect about the mean.
h q[2];
ccx q[0],q[1],q[2];
h q[2];
h q[0];
h q[1];
h q[2];
x q[0];
x q[1];
x q[2];
h q[2];
ccx q[0],q[1],q[2];
h q[2];
x q[0];
x q[1];
x q[2];
h q[0];
h q[1];
h q[2];

// Iteration 2.
h q[2];
ccx q[0],q[1],q[2];
h q[2];
h q[0];
h q[1];
h q[2];
x q[0];
x q[1];
x q[2];
h q[2];
ccx q[0],q[1],q[2];
h q[2];
x q[0];
x q[1];
x q[2];
h q[0];
h q[1];
h q[2];

measure q -> c;
