import pygame.midi
import time

# --- utilidades ---
def map_value(value, in_min, in_max, out_min, out_max):
    """Mapea un valor entre dos rangos"""
    return int(out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min))

# --- setup ---
pygame.midi.init()

print("=== Entradas MIDI disponibles ===")
for i in range(pygame.midi.get_count()):
    interf, name, inp, outp, opened = pygame.midi.get_device_info(i)
    if inp:
        print(f"[{i}] {name.decode()}")

input_id = int(input("\nSelecciona ID de entrada (Dato DUO): "))

print("\n=== Salidas MIDI disponibles ===")
for i in range(pygame.midi.get_count()):
    interf, name, inp, outp, opened = pygame.midi.get_device_info(i)
    if outp:
        print(f"[{i}] {name.decode()}")

output_id = int(input("\nSelecciona ID de salida (Microsoft GS Wavetable Synth): "))

midi_in = pygame.midi.Input(input_id)
midi_out = pygame.midi.Output(output_id)
CHANNEL_DRUMS = 9  # canal 10 (índice base 0)

# --- estado ---
current_instrument = 35
matrix = {}         # {instrumento: [tiempos_relativos_de_golpes]}
recording = True
loop_length = 8.0
start_time = None
active_instrument = None  # instrumento activo actual

print("\n🎛️ Grabación activa (hasta que pulses CC65).")
print("CC71 → cambia instrumento (reinicia contador y sobrescribe si ya existía).")
print("CC81 → golpe (se graba 0–8 s).")
print("CC65 → detiene grabación y reproduce loop.\n")

try:
    while True:
        if midi_in.poll():
            events = midi_in.read(20)
            for data, ts in events:
                status, cc, value, _ = data
                if (status & 0xF0) == 0xB0:  # mensaje CC
                    # --- CC71 → define instrumento ---
                    if cc == 71:
                        new_inst = map_value(value, 0, 127, 35, 81)
                        if new_inst != current_instrument:
                            current_instrument = new_inst
                            start_time = None
                            if current_instrument in matrix:
                                del matrix[current_instrument]
                            print(f"\nInstrumento cambiado → {current_instrument} (contador reiniciado)")
                    # --- CC81 → golpe ---
                    elif cc == 81 and value >= 64 and recording:
                        now = time.time()
                        if start_time is None:
                            start_time = now
                            active_instrument = current_instrument
                            print(f"\n🎬 Comienza grabación para instrumento {active_instrument}")
                        if active_instrument == current_instrument:
                            t_rel = now - start_time
                            if t_rel <= loop_length:
                                matrix.setdefault(current_instrument, []).append(t_rel)
                                print(f"Golpe {current_instrument} en {t_rel:.3f}s")
                                midi_out.note_on(current_instrument, 120, CHANNEL_DRUMS)
                                time.sleep(0.1)
                                midi_out.note_off(current_instrument, 0, CHANNEL_DRUMS)
                            else:
                                print(f"⏱️  Fin automático (8 s) para {current_instrument}")
                    # --- CC65 → comando de fin ---
                    elif cc == 65 and value >= 64:
                        recording = False
                        print("\n🛑 Grabación detenida por CC65")
        else:
            time.sleep(0.005)

        # --- cuando se detiene la grabación ---
        if not recording and matrix:
            print("\n🎶 Matriz final:")
            for inst, hits in matrix.items():
                print(f"  Nota {inst}: {['%.2f' % h for h in hits]}")
            
            # === Construir línea de tiempo consolidada ===
            timeline = []
            for inst, hits in matrix.items():
                for h in hits:
                    timeline.append((h, inst))
            timeline.sort(key=lambda x: x[0])

            print("\n📜 Línea de tiempo consolidada:")
            for t, inst in timeline:
                print(f"  {t:.3f}s -> nota {inst}")

            print("\n🔁 Iniciando loop de reproducción (Ctrl+C para salir)\n")

            # --- loop infinito de reproducción ---
            while True:
                loop_start = time.time()
                idx = 0
                while True:
                    now = time.time() - loop_start
                    if idx < len(timeline) and now >= timeline[idx][0]:
                        _, inst = timeline[idx]
                        midi_out.note_on(inst, 120, CHANNEL_DRUMS)
                        time.sleep(0.05)
                        midi_out.note_off(inst, 0, CHANNEL_DRUMS)
                        idx += 1
                    elif now >= loop_length:
                        break
                    else:
                        time.sleep(0.001)
                print("Loop!")
except KeyboardInterrupt:
    print("\n🛑 Programa detenido por el usuario.")
finally:
    del midi_in
    midi_out.close()
    pygame.midi.quit()
