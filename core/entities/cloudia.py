# cloudia.py
# Movimiento errático lateral de CloudIA (izquierda ↔ derecha) con cambios de objetivo y jitter.
from __future__ import annotations
import random
import math
from dataclasses import dataclass

@dataclass
class Bounds:
    xmin: float
    xmax: float

class CloudIA:
    def __init__(
        self,
        bounds: Bounds,
        y: float,
        speed_base: float = 220.0,          # px/seg - velocidad base
        jitter_amp: float = 45.0,           # amplitud del jitter lateral (px)
        retarget_interval_range=(0.7, 1.6), # cada cuánto cambia de objetivo (seg)
        jitter_freq_range=(3.0, 6.5),       # frecuencia del jitter (Hz)
    ) -> None:
        self.bounds = bounds
        self.y = y
        self.x = (bounds.xmin + bounds.xmax) * 0.5
        self.speed_base = speed_base
        self.jitter_amp = jitter_amp
        self.retarget_interval_range = retarget_interval_range
        self.jitter_freq_range = jitter_freq_range

        self.target_x = self._pick_target()
        self._time_to_retarget = self._pick_retarget_time()
        self._t = 0.0  # tiempo acumulado para jitter
        self._jitter_phase = random.uniform(0, math.tau)
        self._jitter_freq = random.uniform(*self.jitter_freq_range)

    # ---------- API pública ----------
    def update(self, dt: float) -> None:
        """Avanza el movimiento en dt (segundos). Errático lateral con límites."""
        self._t += dt
        self._time_to_retarget -= dt

        # Re-seleccionar objetivo cada cierto tiempo aleatorio
        if self._time_to_retarget <= 0.0 or self._near_target():
            self.target_x = self._pick_target()
            self._time_to_retarget = self._pick_retarget_time()
            # cambias ligeramente la frecuencia/phase para evitar patrones repetitivos
            self._jitter_phase = random.uniform(0, math.tau)
            self._jitter_freq = random.uniform(*self.jitter_freq_range)

        # Dirección hacia el objetivo con pequeña variación de velocidad
        dir_sign = 1.0 if self.target_x > self.x else -1.0
        speed_variation = 0.75 + 0.5 * random.random()  # 0.75..1.25
        vx = dir_sign * self.speed_base * speed_variation

        # Movimiento base hacia el objetivo
        self.x += vx * dt

        # Jitter suavizado (mezcla seno + ruido ligero)
        jitter = self.jitter_amp * math.sin(self._jitter_phase + self._t * self._jitter_freq)
        jitter += (self.jitter_amp * 0.15) * (random.random() - 0.5)

        # Aplicar límites y rebote suave
        if self.x < self.bounds.xmin:
            self.x = self.bounds.xmin + 2.0
            self.target_x = self._pick_target(prefer_right=True)
        elif self.x > self.bounds.xmax:
            self.x = self.bounds.xmax - 2.0
            self.target_x = self._pick_target(prefer_left=True)

        # Posición final con jitter, recortada a límites
        xj = max(self.bounds.xmin, min(self.bounds.xmax, self.x + jitter * 0.25))
        self.x = xj

    def get_pos(self) -> tuple[float, float]:
        return (self.x, self.y)

    def set_bounds(self, xmin: float, xmax: float) -> None:
        self.bounds = Bounds(xmin, xmax)
        self.x = max(xmin, min(xmax, self.x))
        self.target_x = self._pick_target()

    def set_y(self, y: float) -> None:
        self.y = y

    # ---------- Utilidades internas ----------
    def _pick_retarget_time(self) -> float:
        a, b = self.retarget_interval_range
        return random.uniform(a, b)

    def _pick_target(self, prefer_left: bool = False, prefer_right: bool = False) -> float:
        # Elegir nuevo objetivo aleatorio dentro de los límites
        # con leve sesgo si venimos de un borde
        bias = 0.15  # 15% del ancho como sesgo
        width = self.bounds.xmax - self.bounds.xmin
        xmin = self.bounds.xmin + (bias * width if prefer_right else 0.0)
        xmax = self.bounds.xmax - (bias * width if prefer_left else 0.0)
        return random.uniform(xmin, xmax)

    def _near_target(self) -> bool:
        return abs(self.target_x - self.x) < 18.0  # px


# ------------------ DEMO opcional (pygame) ------------------
if __name__ == "__main__":
    # Demo minimalista para ver el movimiento (requiere pygame).
    import pygame
    pygame.init()
    W, H = 900, 300
    scr = pygame.display.set_mode((W, H))
    clk = pygame.time.Clock()

    cloudia = CloudIA(bounds=Bounds(60, W-60), y=H//2, speed_base=230, jitter_amp=55)

    running = True
    while running:
        dt = clk.tick(60) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

        cloudia.update(dt)

        scr.fill((12, 17, 26))
        x, y = cloudia.get_pos()
        # dibuja un círculo representando a CloudIA
        pygame.draw.circle(scr, (220, 240, 255), (int(x), int(y)), 22)
        pygame.display.flip()

    pygame.quit()
