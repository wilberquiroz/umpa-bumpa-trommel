# rhythm_manager.py
# Encapsula la lógica de ritmo, predicciones y evaluación de "treffer".
# - Cada fila de rhythm_matrix es una nube (cloud)
# - Cada columna es un paso dentro del loop (step)
# - Los valores de rhythm_matrix son 0/1 (no hay evento / hay evento)
# - Se guardan predicciones del usuario por loop y por nube
# - Al completar todos los treffers de un loop para la nube activa, se marca como "mastered"

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class CloudProgress:
    # Por loop index -> conjunto de pasos predichos por el usuario (enteros)
    predictions_by_loop: Dict[int, Set[int]] = field(default_factory=dict)
    # Por loop index -> pasos acertados (match con tolerancia)
    hits_by_loop: Dict[int, Set[int]] = field(default_factory=dict)
    mastered: bool = False


class RhythmManager:
    def __init__(
        self,
        rhythm_matrix: List[List[int]],  # clouds x steps (0/1)
        steps_per_loop: int,
        tolerance_steps: int = 0,  # tolerancia en pasos para el treffer (0 = exacto)
    ) -> None:
        assert steps_per_loop > 0, "steps_per_loop debe ser > 0"
        self.rhythm_matrix = rhythm_matrix
        self.steps_per_loop = steps_per_loop
        self.tolerance_steps = tolerance_steps
        self.num_clouds = len(rhythm_matrix)
        self._validate_matrix()

        # Progreso por nube (índice)
        self.progress: List[CloudProgress] = [CloudProgress() for _ in range(self.num_clouds)]
        # Nube actualmente seleccionada
        self.current_cloud: int = 0

    # -------------------------------
    # Utilidades internas
    # -------------------------------
    def _validate_matrix(self) -> None:
        if self.num_clouds == 0:
            raise ValueError("rhythm_matrix no puede estar vacío")
        cols = len(self.rhythm_matrix[0])
        if cols != self.steps_per_loop:
            raise ValueError(
                f"rhythm_matrix tiene {cols} columnas, pero steps_per_loop={self.steps_per_loop}"
            )
        for row in self.rhythm_matrix:
            if len(row) != cols:
                raise ValueError("Todas las filas de rhythm_matrix deben tener el mismo número de columnas")

    def _wrap_distance(self, a: int, b: int) -> int:
        """Distancia mínima en el anillo [0..steps_per_loop-1] entre dos pasos."""
        n = self.steps_per_loop
        d = abs(a - b) % n
        return min(d, n - d)

    # -------------------------------
    # API pública
    # -------------------------------
    def set_current_cloud(self, idx: int) -> None:
        if idx < 0 or idx >= self.num_clouds:
            raise IndexError("Índice de nube fuera de rango")
        self.current_cloud = idx

    def next_unresolved_cloud(self) -> Optional[int]:
        for i, prog in enumerate(self.progress):
            if not prog.mastered:
                return i
        return None

    def is_every_cloud_mastered(self) -> bool:
        return all(p.mastered for p in self.progress)

    def expected_steps_for_cloud(self, cloud_idx: int) -> List[int]:
        row = self.rhythm_matrix[cloud_idx]
        return [i for i, v in enumerate(row) if v == 1]

    def register_prediction(self, loop_idx: int, cloud_idx: Optional[int], step_idx: int) -> None:
        """Registra una predicción del usuario en el loop y nube dados."""
        if cloud_idx is None:
            cloud_idx = self.current_cloud
        if cloud_idx < 0 or cloud_idx >= self.num_clouds:
            raise IndexError("cloud_idx fuera de rango")
        step_idx = step_idx % self.steps_per_loop

        prog = self.progress[cloud_idx]
        prog.predictions_by_loop.setdefault(loop_idx, set()).add(step_idx)

    def evaluate_loop_for_cloud(self, loop_idx: int, cloud_idx: Optional[int] = None) -> Dict[str, int]:
        """Compara predicciones vs patrón con tolerancia. Marca mastered si se cumplen todas.
        Devuelve métricas: total_expected, total_hits, missed."""
        if cloud_idx is None:
            cloud_idx = self.current_cloud

        expected = self.expected_steps_for_cloud(cloud_idx)
        prog = self.progress[cloud_idx]
        predicted = list(prog.predictions_by_loop.get(loop_idx, set()))
        tol = self.tolerance_steps

        hits: Set[int] = set()  # pasos del patrón que se considerarán acertados
        used_preds: Set[int] = set()

        for s in expected:
            # buscar alguna predicción p cercana
            found = False
            for p in predicted:
                if p in used_preds:
                    continue
                if self._wrap_distance(p, s) <= tol:
                    hits.add(s)
                    used_preds.add(p)
                    found = True
                    break
            # si no se encontró, sigue al siguiente esperado

        prog.hits_by_loop[loop_idx] = hits

        total_expected = len(expected)
        total_hits = len(hits)
        missed = total_expected - total_hits

        if missed == 0 and total_expected > 0:
            prog.mastered = True

        return {
            "total_expected": total_expected,
            "total_hits": total_hits,
            "missed": missed,
        }

    def reset_predictions_for_cloud(self, cloud_idx: int) -> None:
        self.progress[cloud_idx] = CloudProgress(mastered=self.progress[cloud_idx].mastered)

    def cloud_status(self, cloud_idx: int) -> Dict[str, object]:
        prog = self.progress[cloud_idx]
        return {
            "mastered": prog.mastered,
            "loops_recorded": list(prog.predictions_by_loop.keys()),
            "hits_by_loop": {k: sorted(list(v)) for k, v in prog.hits_by_loop.items()},
        }
