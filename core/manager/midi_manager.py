import time
#from graphics_manager import GraphicsManager

class MIDIManager:
    def __init__(self, patterns_completed, matrix, midi_out, vel=100, channel=0):
        """
        patterns_completed : lista de bools
        matrix             : diccionario {note: [t1, t2, ...]}
        midi_out           : objeto con note_on
        vel                : velocidad MIDI
        channel            : canal MIDI
        """
        self.patterns_completed = patterns_completed
        self.matrix = matrix
        self.midi_out = midi_out
        self.vel = vel
        self.channel = channel

        # Lista interna de eventos ya desplegados para no repetirlos
        self._scheduled = []
        self.start_time = None
        self.graphics = None

    def set_graphics(self, graphics_manager):
        self.graphics = graphics_manager

    def reset(self):
        """
        Reinicia tiempos y vuelve a evaluar qué patrones deben emitir MIDI.
        """
        self.start_time = time.perf_counter()
        self._scheduled = []  # limpiar eventos viejos

        # Por cada patrón completado, programar sus notas
        i = 0
        for note, times_list in self.matrix.items():
            if i < len(self.patterns_completed) and self.patterns_completed[i]:
                for t in times_list:
                    self._scheduled.append((t, note))
            i += 1

        # Ordenar eventos por tiempo
        self._scheduled.sort(key=lambda x: x[0])

    def update(self):
        """
        Chequea si hay notas MIDI que deban dispararse en este frame.
        """
        if self.start_time is None:
            return

        now = time.perf_counter() - self.start_time

        # Los eventos que ya deben dispararse (<= now)
        to_fire = [ev for ev in self._scheduled if ev[0] <= now]

        for event in to_fire:
            t, note = event
            # Disparar note_on
            self.graphics.on_crush_midi()
            self.midi_out.note_on(note, self.vel, self.channel)
            # Removerlo para no repetirlo
            self._scheduled.remove(event)
