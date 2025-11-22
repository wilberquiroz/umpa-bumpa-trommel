import pygame.midi
import time

pygame.midi.init()
input_id = 1   # ID del Dato DUO
output_id = 2  # Por si luego quieres devolverlo al DUO

#49

midi_in = pygame.midi.Input(input_id)
midi_out = pygame.midi.Output(output_id)
events = []
start_time = time.time()
guia_start_time = time.time()

print("Grabando... Ctrl+C para parar")

try:
    while True:
        
        guia_current_time = time.time()
        if int(guia_current_time*100) - int(guia_start_time*100) > 125:
            midi_out.note_on(42, 110, 9)
            time.sleep(0.05)
            midi_out.note_off(42, 0, 0)
            guia_start_time = time.time()
            print("=========================================")
        if midi_in.poll():
            for data, ts in midi_in.read(10):
                status, d1, d2, _ = data
                rel_time = time.time() - start_time

                events.append((rel_time, [status, d1, d2]))
                if data[0]!=248:
                    #if data[2] == 127:
                    #    midi_out.note_on(35, 110, 9)
                    #    time.sleep(0.05)
                    #    midi_out.note_off(35, 0, 0)
                    print(f"[{rel_time:.3f}s] {data}")
        else:
            time.sleep(0.005)
except KeyboardInterrupt:
    print("\nGrabación detenida.")
finally:
    del midi_in
    pygame.midi.quit()

# Guarda los eventos
import pickle
with open("dato_duo_loop.pkl", "wb") as f:
    pickle.dump(events, f)

print(f"{len(events)} eventos guardados.")
