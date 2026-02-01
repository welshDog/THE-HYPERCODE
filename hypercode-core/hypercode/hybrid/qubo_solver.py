"""
QUBO Solver for Hybrid Optimization
Provides a unified interface for solving QUBO problems using either:
1. Classical Simulated Annealing (CPU-based fallback)
2. D-Wave Quantum Annealing (QPU-based, requires dwave-ocean-sdk)

Designed to be API-compatible with D-Wave's Ocean SDK (dimod).
"""

import math
import random
import logging
from typing import Dict, Tuple, List
import importlib

# Setup logger
logger = logging.getLogger("hypercode.hybrid.solver")

DWAVE_AVAILABLE = False
try:
    dwave_system = importlib.import_module("dwave.system")
    DWaveSampler = getattr(dwave_system, "DWaveSampler")
    EmbeddingComposite = getattr(dwave_system, "EmbeddingComposite")
    DWAVE_AVAILABLE = True
except (ImportError, AttributeError):
    DWAVE_AVAILABLE = False

class SimulatedAnnealer:
    """
    A classical simulated annealing solver for QUBO problems.
    Acts as a placeholder for a real Quantum Annealer (D-Wave).
    """
    
    def __init__(self, steps: int = 5000, initial_temp: float = 10.0, alpha: float = 0.99, restarts: int = 10):
        self.steps = steps
        self.initial_temp = initial_temp
        self.alpha = alpha
        self.restarts = restarts
        
    def sample_qubo(self, Q: Dict[Tuple[int, int], float]) -> Dict[int, int]:
        """
        Minimizes the objective function: E = x^T Q x
        
        Args:
            Q: A dictionary {(i, j): weight} representing the QUBO matrix.
               Diagonal elements (i, i) are linear biases.
               Off-diagonal elements (i, j) are quadratic couplings.
               
        Returns:
            A dictionary of selected variables {var_index: 0 or 1}
        """
        # 1. Identify all variables
        variables_set: set[int] = set()
        for (i, j) in Q.keys():
            variables_set.add(i)
            variables_set.add(j)
        variables: List[int] = sorted(list(variables_set))
        
        if not variables:
            return {}
            
        best_state: Dict[int, int] = {}
        best_energy: float = float("inf")
        for _ in range(self.restarts):
            state: Dict[int, int] = {v: random.choice([0, 1]) for v in variables}
            current_energy = self._calculate_energy(state, Q)
            temp = self.initial_temp
            for _ in range(self.steps):
                v: int = random.choice(variables)
                old_val = state[v]
                new_val = 1 - old_val
                state[v] = new_val
                new_energy = self._calculate_energy(state, Q)
                delta_E = new_energy - current_energy
                if delta_E < 0 or random.random() < math.exp(-delta_E / temp):
                    current_energy = new_energy
                    if current_energy < best_energy:
                        best_energy = current_energy
                        best_state = state.copy()
                else:
                    state[v] = old_val
                temp *= self.alpha
        return best_state
        
    def _calculate_energy(self, state: Dict[int, int], Q: Dict[Tuple[int, int], float]) -> float:
        energy = 0.0
        for (i, j), weight in Q.items():
            if i in state and j in state:
                energy += weight * state[i] * state[j]
        return energy

class QuboSolver:
    """
    Unified solver that attempts to use D-Wave hardware if available/configured,
    falling back to simulated annealing otherwise.
    """
    def __init__(self, use_quantum: bool = True, num_reads: int = 100):
        self.use_quantum = use_quantum
        self.num_reads = num_reads
        self.sim_annealer = SimulatedAnnealer()
        
    def solve(self, Q: Dict[Tuple[int, int], float]) -> Dict[int, int]:
        """
        Solve the QUBO problem Q.
        
        Args:
            Q: Dictionary {(i, j): weight}
            
        Returns:
            Dictionary {var_index: 0 or 1} for the best solution found.
        """
        # Check if we should (and can) use Quantum Backend
        if self.use_quantum and DWAVE_AVAILABLE:
            try:
                return self._solve_quantum(Q)
            except RuntimeError as e:
                logger.warning("D-Wave solve failed: %s. Falling back to simulation.", e)
                return self._solve_classical(Q)
        else:
            if self.use_quantum and not DWAVE_AVAILABLE:
                logger.info("D-Wave SDK not installed. Using classical simulation.")
            return self._solve_classical(Q)
            
    def _solve_classical(self, Q: Dict[Tuple[int, int], float]) -> Dict[int, int]:
        return self.sim_annealer.sample_qubo(Q)
        
    def _solve_quantum(self, Q: Dict[Tuple[int, int], float]) -> Dict[int, int]:
        if not DWAVE_AVAILABLE:
            raise RuntimeError("D-Wave Ocean SDK not installed")
            
        # Convert Q dictionary to linear/quadratic components for dimod if needed
        # D-Wave's EmbeddingComposite handles the graph embedding automatically
        sampler = EmbeddingComposite(DWaveSampler())
        
        # Q is {(i, j): weight}. 
        # dimod expects a dictionary like this directly for sample_qubo
        response = sampler.sample_qubo(Q, num_reads=self.num_reads)
        
        # Get the best sample (lowest energy)
        best_sample = response.first.sample
        return dict(best_sample)
