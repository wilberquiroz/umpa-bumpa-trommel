"""
GameLogic — Maneja la lógica principal del juego:
sincronización MIDI, detección de aciertos, errores y control del flujo.
"""
import time
import pygame.midi


class GameLogic:
    def __init__(self, midi_device_hint="DATO", channel=9, hit_window=0.15):
        """
        :param midi_device_hint: texto parcial para detectar el dispositivo MIDI
        :param channel: canal MIDI usado
        :param hit_window: margen de tiempo (en segundos) para considerar un golpe como correcto
        """
        self.channel = channel
        self.hit_window = hit_window
        self.loop_length = 8.0
        self.reference_matrix = {}
        self.timeline = []
        self.active = False
        self.start_time = None

        # --- MIDI ---
        pygame.midi.init()
        self.midi_in = None
        self.midi_out = None
        self.device_hint = midi_device_hint

    # ---------------------------------------------------------
    # INICIALIZACIÓN
    # ---------------------------------------------------------
    def init_midi(self):
        print("=== Entradas MIDI disponibles ===")
        for i in range(pygame.midi.get_count()):
            interf, name, inp, outp, opened = pygame.midi.get_device_info(i)
            if inp:
                print(f"[{i}] {name.decode()}")

        input_id = int(input("\nSelecciona ID de entrada (DATO DUO): "))

        print("\n=== Salidas MIDI disponibles ===")
        for i in range(pygame.midi.get_count()):
            interf, name, inp, outp, opened = pygame.midi.get_device_info(i)
            if outp:
                print(f"[{i}] {name.decode()}")

        output_id = int(input("\nSelecciona ID de salida (Microsoft GS Wavetable Synth): "))

        self.midi_in = pygame.midi.Input(input_id)
        self.midi_out = pygame.midi.Output(output_id)
        print("[MIDI] Configuración completa ✅")

    # ---------------------------------------------------------
    # MATRIZ DE REFERENCIA
    # ---------------------------------------------------------
    def set_reference_matrix(self, matrix):
        """Define la matriz de tiempos esperados y construye la línea de tiempo consolidada."""
        self.reference_matrix = matrix
        self.timeline.clear()
        for inst, hits in matrix.items():
            for h in hits:
                self.timeline.append({"time": h, "inst": inst, "hit": False})
        self.timeline.sort(key=lambda x: x["time"])
        print("[GameLogic] Matriz de referencia cargada con", len(self.timeline), "golpes.")

    def start(self):
        self.active = True
        self.start_time = time.time()

    # ---------------------------------------------------------
    # PROCESAMIENTO DE ENTRADAS MIDI
    # ---------------------------------------------------------
    def process_midi_events(self, graphics_manager):
        """Lee los mensajes MIDI y compara con la línea de tiempo esperada."""
        if not self.midi_in or not self.active:
            return
        now = time.time() - self.start_time

        if self.midi_in.poll():
            events = self.midi_in.read(10)
           
            for data, ts in events:
                status, cc, value, _ = data

                # Mensaje de "golpe" CC81 → representa crush o golpe de pad
                if (status & 0xF0) == 0xB0 and cc == 81 and value >= 64:
                    print(f"[MIDI] Golpe detectado en t={now:.2f}")
                    self._evaluate_hit(now, graphics_manager)

    def _evaluate_hit(self, hit_time, graphics_manager):
        """Evalúa si el golpe coincide con algún tiempo de la matriz de referencia."""
        closest = None
        min_diff = 999

        for entry in self.timeline:
            if entry["hit"]:
                continue
            diff = abs(entry["time"] - hit_time)
            if diff < min_diff:
                min_diff = diff
                closest = entry

        if closest and min_diff <= self.hit_window:
            closest["hit"] = True
            print(f"✅ Acierto! (Δ={min_diff:.3f}s)")
            graphics_manager.flash_rayo(closest["inst"])  # genera el rayo correspondiente
            self.play_feedback(True)
        else:
            print(f"❌ Fallo (Δ={min_diff:.3f}s)")
            self.play_feedback(False)

    def play_feedback(self, success=True):
        """Reproduce un sonido breve de confirmación (diferente para acierto/error)."""
        note = 76 if success else 30
        self.midi_out.note_on(note, 127, self.channel)
        time.sleep(0.05)
        self.midi_out.note_off(note, 0, self.channel)

    def stop(self):
        self.active = False
        if self.midi_in:
            del self.midi_in
        if self.midi_out:
            self.midi_out.close()
        pygame.midi.quit()
        print("[GameLogic] MIDI detenido correctamente.")
