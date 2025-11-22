# game_loop.py
# Controla el timing del loop, la generación de "malos" o "notas" según progreso,
# la evaluación por loop y la salida MIDI (Windows) con pygame.midi si está disponible.
#
# NOTAS DE INTEGRACIÓN:
# - Reemplaza util.graphics_manager por manager.graphics_manager (ya aplicado en imports ficticios)
# - Cuando un evento es "treffer", puedes disparar una nota visual y/o prolongarla 0.5s
# - Si una nube está "mastered", deja de mandar "malos" para esa nube y manda "notas"
# - Al completar una nube, se selecciona automáticamente la siguiente no resuelta
#
# Este archivo se enfoca en la lógica; los detalles de render/input deben conectarse en tu engine.

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional
import time

try:
    import pygame.midi as midi
    _MIDI_AVAILABLE = True
except Exception:
    _MIDI_AVAILABLE = False
    midi = None  # type: ignore

# Tu propio módulo gráfico según tu proyecto:
# from manager.graphics_manager import spawn_enemy, spawn_note, show_hit_note
# Aquí definimos stubs para que el archivo sea ejecutable aislado:
def spawn_enemy(cloud_idx: int, step_idx: int):
    # TODO: integrar con manager.graphics_manager
    print(f"[SPAWN ENEMY] nube={cloud_idx} step={step_idx}")

def spawn_note(cloud_idx: int, step_idx: int, sustain_seconds: float = 0.5):
    # TODO: integrar con manager.graphics_manager
    print(f"[SPAWN NOTE] nube={cloud_idx} step={step_idx} sustain={sustain_seconds}s")

def show_top_center_lightning(alpha: float = 0.4):
    # TODO: integrar rayo superior centrado con alpha 40%
    pass

# Salida MIDI básica (Windows default) via pygame.midi
class MidiOut:
    def __init__(self, instrument: int = 0, velocity: int = 100):
        self.instrument = instrument
        self.velocity = velocity
        self.out = None
        if _MIDI_AVAILABLE:
            midi.init()
            try:
                device_id = midi.get_default_output_id()
                self.out = midi.Output(device_id)
                # Program Change para seleccionar instrumento
                self.out.set_instrument(self.instrument)
            except Exception:
                self.out = None

    def note_on(self, note: int):
        if self.out:
            self.out.note_on(note, self.velocity)

    def note_off(self, note: int):
        if self.out:
            self.out.note_off(note, self.velocity)

    def close(self):
        if self.out:
            self.out.close()
        if _MIDI_AVAILABLE:
            midi.quit()

# Mapeo simple de (nube, step) -> pitch MIDI (puedes sustituir por tu lógica musical)
def default_pitch_mapper(cloud_idx: int, step_idx: int) -> int:
    # Escala pentatónica básica sobre C4 (60)
    base = 60 + (cloud_idx * 2)  # eleva por nube
    return base + (step_idx % 5) * 2

@dataclass
class LoopConfig:
    bpm: float
    steps_per_beat: int = 1  # si quieres subdivisión
    steps_per_loop: int = 16

    @property
    def step_duration(self) -> float:
        # segundos por step
        spb = 60.0 / self.bpm
        return spb / max(1, self.steps_per_beat)

class GameLoop:
    def __init__(
        self,
        rhythm_manager,
        loop_cfg: LoopConfig,
        pitch_mapper: Callable[[int, int], int] = default_pitch_mapper,
        midi_instrument: int = 0,
        midi_velocity: int = 100,
        lightning_alpha: float = 0.4,
    ) -> None:
        self.rm = rhythm_manager
        self.cfg = loop_cfg
        self.pitch_mapper = pitch_mapper
        self.loop_idx = 0
        self.step_idx = 0
        self.midi = MidiOut(instrument=midi_instrument, velocity=midi_velocity)
        self.lightning_alpha = lightning_alpha

    # Debe ser llamado por tu sistema de input cuando el jugador presiona el botón
    def on_player_press(self, cloud_idx: Optional[int] = None):
        self.rm.register_prediction(loop_idx=self.loop_idx, cloud_idx=cloud_idx, step_idx=self.step_idx)

    def _send_midi_click(self, cloud_idx: int, step_idx: int):
        pitch = self.pitch_mapper(cloud_idx, step_idx)
        self.midi.note_on(pitch)
        # click corto
        time.sleep(0.05)
        self.midi.note_off(pitch)

    def _send_midi_note(self, cloud_idx: int, step_idx: int, sustain: float = 0.35):
        pitch = self.pitch_mapper(cloud_idx, step_idx)
        self.midi.note_on(pitch)
        time.sleep(sustain)
        self.midi.note_off(pitch)

    def _loop_end(self):
        # Evaluar loop para la nube activa
        cloud = self.rm.current_cloud
        metrics = self.rm.evaluate_loop_for_cloud(loop_idx=self.loop_idx, cloud_idx=cloud)
        all_hit = (metrics["missed"] == 0 and metrics["total_expected"] > 0)

        if all_hit:
            # Nube completada -> pasar a la siguiente no resuelta
            next_cloud = self.rm.next_unresolved_cloud()
            if next_cloud is None:
                print("[GAME] ¡Todas las nubes dominadas!")
            else:
                self.rm.set_current_cloud(next_cloud)
        else:
            # Si no se completó, seguimos intentando en el siguiente loop (no se limpia progreso)
            pass

        # Preparar siguiente loop
        self.loop_idx += 1
        self.step_idx = 0

    def tick(self):
        # Este método se debe llamar con cadencia de self.cfg.step_duration (tu scheduler)
        show_top_center_lightning(self.lightning_alpha)

        cloud = self.rm.current_cloud
        is_mastered = self.rm.progress[cloud].mastered

        expected_steps = set(self.rm.expected_steps_for_cloud(cloud))

        if self.step_idx in expected_steps:
            if is_mastered:
                # En modo notas: no se generan enemigos; se dispara nota visual/sonora
                spawn_note(cloud, self.step_idx, sustain_seconds=0.5)
                self._send_midi_note(cloud, self.step_idx, sustain=0.35)
            else:
                # Aún no dominado: se generan "malos" y guía por MIDI (click)
                spawn_enemy(cloud, self.step_idx)
                self._send_midi_click(cloud, self.step_idx)

        # Avance de step y control de fin de loop
        self.step_idx += 1
        if self.step_idx >= self.cfg.steps_per_loop:
            self._loop_end()

    def shutdown(self):
        self.midi.close()


# Ejemplo mínimo de ejecución (si corres este archivo directamente)
if __name__ == "__main__":
    from rhythm_manager import RhythmManager

    rhythm = [
        # nube 0
        [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        # nube 1
        [0,1,0,0, 0,1,0,0, 0,1,0,0, 0,1,0,0],
    ]
    rm = RhythmManager(rhythm_matrix=rhythm, steps_per_loop=16, tolerance_steps=0)
    cfg = LoopConfig(bpm=120, steps_per_loop=16)

    loop = GameLoop(rhythm_manager=rm, loop_cfg=cfg, midi_instrument=0)

    # Simular ticking por ~2 loops
    total_steps = 16 * 2
    start = time.time()
    for _ in range(total_steps):
        loop.tick()
        time.sleep(cfg.step_duration)

    loop.shutdown()
