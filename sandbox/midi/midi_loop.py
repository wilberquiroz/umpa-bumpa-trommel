import pygame.midi, time, pickle

pygame.midi.init()
output_id = 2  # Puerto de salida (puede ser “Microsoft GS Wavetable” o el Dato DUO)
midi_out = pygame.midi.Output(output_id)

# Cargar el loop
with open("dato_duo_loop.pkl", "rb") as f:
    events = pickle.load(f)

loop_length = events[-1][0]  # duración total en segundos

print(f"Reproduciendo loop de {loop_length:.2f}s... Ctrl+C para parar.")

try:
    while True:  # loop infinito
        start = time.time()
        for t, data in events:
            while (time.time() - start) < t:
                time.sleep(0.001)
            midi_out.write_short(*data)
        print("Loop!")
except KeyboardInterrupt:
    print("\nLoop detenido.")
finally:
    midi_out.close()
    pygame.midi.quit()
