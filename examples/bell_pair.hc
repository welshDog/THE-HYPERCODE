#:domain quantum
#:backend qiskit

@quantum_function: bell_pair () -> Bits
  @doc: "Create a Bell pair (maximally entangled state)"
  
  @circuit: c
    @init: qubits = QuantumRegister(2)
    @hadamard: qubits[0]
    @cnot: control=qubits[0], target=qubits[1]
    @measure: qubits -> result
  
  @return: result

@function: main ()
  @let: result = bell_pair()
  @print: result
