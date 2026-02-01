# 🛠️ HYPERCODE ROADMAP 2025

## Vision

**By end of 2025, HyperCode should be:**
- ✅ Publicly usable (command-line tool)
- ✅ Multi-backend capable (classical, quantum, molecular)
- ✅ AI-integrated (LLM co-development)
- ✅ Community-driven (open-source, neurodivergent-led)

---

## PHASE 1: DESIGN SPECIFICATION (✅ COMPLETE)

**Status:** Done (Dec 2025)

- [x] Research report (2025 landscape analysis)
- [x] Textual syntax specification
- [x] Visual syntax specification
- [x] Intermediate representation design
- [x] Phase 1 summary

**Deliverable:** 2,942 lines of comprehensive specification

---

## PHASE 2: IMPLEMENTATION (Jan-May 2025)

### 2.1: Parser & AST (Jan 2025)

**Goal:** Parse HyperCode text → Abstract Syntax Tree

**Milestones:**
- [ ] Define ANTLR grammar (`.g4`)
- [ ] Generate lexer + parser
- [x] Build AST data structures (Python)
- [x] Write snapshot tests
- [x] Support minimal quantum subset (init, hadamard, cnot, measure, return)
- **Note:** A functional hand-written parser and lexer are implemented in `hypercode/parser/parser.py`. The formal ANTLR grammar needs to be synced with this implementation.

**Timeline:** 2-3 weeks  
**Owner:** Lyndz  
**Status:** 🟢 In Progress

---

### 2.2: IR Builder (Feb 2025)

**Goal:** AST → HyperCode Intermediate Representation (SSA form)

**Milestones:**
- [x] Implement IR data structures (Python, for quantum)
- [x] Build AST → IR visitor/converter (for quantum)
- [ ] Add type checking pass
- [ ] Add scope analysis pass
- [ ] Unit tests (AST sample → IR sample)
- **Note:** Quantum IR lowering exists in `hypercode/ir/lower_quantum.py`.

**Timeline:** 2-3 weeks  
**Owner:** Lyndz 
**Status:** 🟢 In Progress

---

### 2.3: Quantum Backend (Feb-Mar 2025)

**Goal:** IR → Qiskit Python code (executable)

**Milestones:**
- [x] Implement IR → Qiskit code generator
- [x] Support basic gates (Hadamard, CNOT, Measure)
- [x] Integration tests (run on Qiskit Aer simulator)
- [ ] Optional: Run on IBM quantum hardware (with API key)
- **Note:** A functional Qiskit backend is implemented in `hypercode/backends/qiskit_backend.py`.

**Timeline:** 2-3 weeks  
**Owner:** Lyndz 
**Status:** 🟢 In Progress

---

### 2.4: CLI Tool (Feb 2025)

**Goal:** User-facing command-line interface

**Commands:**
- [x] `hypercode parse`
- [x] `hypercode qir`
- [x] `hypercode run`
- [x] `hypercode --version`
- [x] `hypercode --help`
- **Note:** The core CLI is functional in `hypercode/cli.py`.

**Timeline:** 1 week  
**Owner:** Lyndz  
**Status:** 🟢 In Progress

---

### 2.5: Visual Editor (Mar-Apr 2025)

**Goal:** Web-based node editor using React + React Flow.

**Milestones:**
- [x] Basic React Flow setup
- [x] Custom Nodes (Quantum, Classical)
- [x] Compiler Integration
- [ ] Drag-and-drop Palette
- [ ] Save/Load flows

---

## PHASE 3: BIO-LOGIC & MOLECULAR COMPUTING (May-Aug 2025)

**Goal:** Introduce DNA assembly, PCR, and CRISPR simulation capabilities.

**Milestones:**
- [ ] **Golden Gate Assembly Simulator:**
    - [x] Backend BsaI overhang logic (`simulator.py`)
    - [x] Frontend Node (`GoldenGateNode.tsx`)
    - [ ] Linear Map View for failed assemblies
- [ ] **PCR Simulation:**
    - [ ] Primer annealing logic
    - [ ] Amplification cycle simulation
- [ ] **CRISPR/Cas9:**
    - [ ] gRNA target search
    - [ ] Off-target scoring
- [ ] **Visualization:**
    - [ ] Circular Plasmid Maps (D3/SVG)
    - [ ] Linear Sequence Views

**Goal:** Web-based node-graph editor

**Tech Stack:**
- React (frontend)
- React Flow or Rete.js (node library)
- D3.js (data visualization)
- Python FastAPI (backend, optional)

**Milestones:**
- [x] Foundational project homepage created.
- [ ] Node palette (15+ nodes)
- [ ] Drag-drop canvas
- [ ] Parameter editing (sliders, dropdowns)
- [ ] Export to HyperCode text
- [ ] Import HyperCode text → visual
- [ ] Play button (execute, show results)
- [ ] Semantic color coding

**Timeline:** 3-4 weeks  
**Owner:** [TBD] (web dev)  
**Status:** 🟢 In Progress

---

### 2.6: Classical Backend (Mar 2025)

**Goal:** IR → LLVM IR → CPU code

**Implementation:**
- [ ] Use LLVM bindings (llvmlite for Python)
- [ ] Implement classical IR lowering
- [ ] Code generation
- [ ] Execute and return results

**Timeline:** 2-3 weeks  
**Owner:** [TBD] (compiler expert)  
**Status:** 🟡 Not started

---

### 2.7: Molecular Backend (Apr 2025)

**Goal:** IR → DSD (DNA Strand Displacement) simulator code

**Implementation:**
- [ ] Implement molecular IR lowering
- [ ] Generate DSD Visual code (or custom simulator)
- [ ] Reaction simulation
- [ ] Visualization of results

**Timeline:** 2-3 weeks  
**Owner:** [TBD] (computational biology)  
**Status:** 🟡 Not started

---

## PHASE 3: OPTIMIZATION & RELIABILITY (Apr-Jun 2025)

### 3.1: Optimization Passes

**Milestones:**
- [ ] Dead code elimination
- [ ] Constant folding
- [ ] Quantum gate fusion
- [ ] Resource estimation (qubit count, gate depth, error)
- [ ] Memory optimization

**Timeline:** 2-3 weeks  
