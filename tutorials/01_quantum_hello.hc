Welcome to your first Quantum Circuit!
In this tutorial, we will create a Bell Pair - the "Hello World" of Quantum Computing.

---STEP---
First, we need to define our domain.
HyperCode needs to know we are working with Quantum mechanics.

```python
#:domain quantum
#:backend qiskit
```

---STEP---
Now, let's create a circuit.
We'll name it `hello_bell` and initialize our registers.
We need 2 Qubits (`QReg`) and 2 Classical Bits (`CReg`).

```python
@circuit: hello_bell
  @init: q = QReg(2)
  @init: c = CReg(2)
```

---STEP---
Time for the magic. 🪄
We put the first qubit into a "Superposition" using the Hadamard gate.
This means it is both 0 and 1 at the same time.

```python
  @hadamard: q[0]
```

---STEP---
Now, we "Entangle" them.
We use a CNOT (Controlled-NOT) gate.
If q[0] is 1, flip q[1]. Since q[0] is in superposition, q[1] becomes entangled!

```python
  @cnot: q[0], q[1]
```

---STEP---
Finally, we measure the result.
This collapses the quantum state into classical bits we can read.

```python
  @measure: q -> c
```

---STEP---
That's it! You just wrote a quantum program.
HyperCode makes it easy, right?
