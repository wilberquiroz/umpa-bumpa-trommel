import pygame.midi
import time

# Configuración MIDI
pygame.midi.init()

print("=== Dispositivos de salida disponibles ===")
for i in range(pygame.midi.get_count()):
    interf, name, inp, outp, opened = pygame.midi.get_device_info(i)
    if outp:
        print(f"[{i}] {name.decode()}")

output_id = int(input("\nSelecciona el ID del Microsoft GS Wavetable Synth: "))
midi_out = pygame.midi.Output(output_id)

CHANNEL = 9  # Canal 10 (índice base 0)
VEL = 110
LOOP_DURATION = 3.75  # segundos

# Instrumentos GM
BOMBO = 47
PLATILLO = 52
TOM = 56
CONGA_MUTE = 62
CONGA_OPEN = 63
COWBELL = 56

# Patrón (tiempo relativo en segundos)
pattern = [
    
    (0, BOMBO), (0.937, BOMBO), (1.875, BOMBO), (2.812, BOMBO),  
    (0.468, PLATILLO), (0.703, PLATILLO), (1.406, PLATILLO), (1.640, PLATILLO), (2.343, PLATILLO), (2.578, PLATILLO), (3.281, PLATILLO), (3.515, PLATILLO),
    (0, TOM), (0.937, TOM), (1.875, TOM), (2.812, TOM)
    # Caja
    #(0.75, SNARE), (2.25, SNARE),
    # Maracas (continuas cada 0.25s)
    #*[(i * 0.25, MARACAS) for i in range(int(LOOP_DURATION / 0.25))],
    # Congas
    #(0.75, CONGA_MUTE), (2.25, CONGA_OPEN),
    # Cowbell
    #(0.0, COWBELL), (1.5, COWBELL)
]

# Normaliza dentro de 3s
pattern = [(t % LOOP_DURATION, n) for t, n in pattern]
pattern.sort(key=lambda x: x[0])

print("\n🎶 Iniciando loop de cumbia (Ctrl+C para salir)\n")

try:
    while True:
        loop_start = time.time()
        idx = 0
        while True:
            now = time.time() - loop_start
            if idx < len(pattern) and now >= pattern[idx][0]:
                _, note = pattern[idx]
                midi_out.note_on(note, VEL, CHANNEL)
                time.sleep(0.05)
                midi_out.note_off(note, 0, CHANNEL)
                idx += 1
            elif now >= LOOP_DURATION:
                break
            else:
                time.sleep(0.001)
        print("Loop!")
except KeyboardInterrupt:
    print("\n🛑 Loop detenido por el usuario.")
finally:
    midi_out.close()
    pygame.midi.quit()
