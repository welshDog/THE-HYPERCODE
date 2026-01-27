# 🎓 Tutorial 1: Hello, Quantum World!

**Welcome to HyperCode!** 🧠✨
This guide will take you from "Zero" to "Quantum Entanglement" in about 5 minutes. No math degree required.

---

## 🧐 What are we building?
We are going to create a **Bell Pair**.
In quantum physics, this is when two particles become "entangled" — change one, and the other changes instantly, no matter how far apart they are. Spooky, right? 👻

In HyperCode, it's just 3 nodes.

---

## 🛠️ Step 1: The Setup
1. Open the **HyperFlow Editor**.
2. Press `Shift + Z` to enter **Zen Mode** (optional, but helps focus).
3. Look at the **Palette** on the left.

> **🧠 Brain Tip**: If the screen feels too bright, check the settings for "Dark Mode" or "Dyslexia Mode"!

---

## 🎨 Step 2: Draw the Circuit

### 1. Initialize Two Qubits
- Drag two **Init Nodes** (`@init`) onto the canvas.
- Name them `q0` and `q1`.
- Set their value to `|0>` (Quantum Zero).

### 2. The Superposition (Hadamard)
- Drag a **Gate Node** (`@gate`) next to `q0`.
- Select **H** (Hadamard) from the dropdown.
- Connect `q0` → `H Gate`.
- *What this does*: It puts `q0` into a state where it is **both 0 and 1 at the same time**.

### 3. The Entanglement (CNOT)
- Drag another **Gate Node** (`@gate`).
- Select **CX** (CNOT) from the dropdown.
- Connect `H Gate (output)` → `CX (Control input)`.
- Connect `q1` → `CX (Target input)`.
- *What this does*: "If `q0` is 1, flip `q1`." Since `q0` is both 0 and 1... `q1` becomes entangled with it!

### 4. Measure
- Drag two **Measure Nodes** (`@measure`).
- Connect the outputs of your circuit to them.

---

## 💻 Step 3: The Code
Click the **"Compile"** button. You should see this HyperCode generated automatically:

```hypercode
#:domain quantum

@circuit: bell_pair
    @init: q0 = QReg(1)
    @init: q1 = QReg(1)
    
    # Put q0 in superposition
    @gate: h(q0)
    
    # Entangle q0 and q1
    @gate: cx(q0, q1)
    
    # Check the results
    @measure: q0 -> c0
    @measure: q1 -> c1
```

---

## 🚀 Step 4: Run It!
Click **"Run Simulation"**.

**Expected Result:**
You will see roughly **50% `00`** and **50% `11`**.
You will **NEVER** see `01` or `10`.

Why? Because they are entangled! They always agree. 🤝

---

## 🎉 You did it!
You just programmed a quantum computer.
**Next Up**: [Tutorial 2: Gene Editing with CRISPR](02_hello_dna.md)
