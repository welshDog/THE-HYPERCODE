# 🛠️ HyperCode Agent Tools Guide

We have upgraded the team with new capabilities! Here is how to use the new tooling.

## 🔬 Research Agent: Auto-Docs Generator
**Goal:** Automatically generate Markdown documentation from source code.
**Usage:**
```bash
python tools/research/doc_gen.py <input_directory> <output_file>
```
**Example:**
```bash
python tools/research/doc_gen.py examples/ docs/API_REFERENCE.md
```

## 💻 Code Agent: V3 Syntax Validator
**Goal:** Check `.hc` files for HyperCode V3 compliance (Neurodivergent-First Standard).
**Usage:**
```bash
python tools/code/syntax_validator.py <file.hc>
```
**Example:**
```bash
python tools/code/syntax_validator.py examples/grover.hc
```
*   **Green:** Valid V3 Syntax.
*   **Red:** Errors (Legacy syntax, missing domain headers).
*   **Yellow:** Warnings (Verbose naming).

## 🗣️ Narrator Agent: Interactive Tutorial Runner
**Goal:** Run interactive, step-by-step tutorials in the terminal.
**Usage:**
```bash
python tools/narrator/tutorial_runner.py <tutorial_file.hc>
```
**Example:**
```bash
python tools/narrator/tutorial_runner.py tutorials/01_quantum_hello.hc
```

---
*Note: Ensure you have Python 3 installed to run these tools.*
