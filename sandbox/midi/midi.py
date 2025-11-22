import pygame.midi
import time

# --- Configura tu ID aquí si ya lo sabes ---
INPUT_ID = None  # pon un int (p.ej. 1) o deja None para elegir

# --- Utilidades ---
REALTIME = {0xF8, 0xFA, 0xFB, 0xFC, 0xFE, 0xFF}  # clock, start/stop, active sensing, reset

def is_realtime(status):
    return status in REALTIME

def status_type(status):
    """Devuelve ('note_on'|'note_off'|'cc'|'pitchbend'|None, canal) para status de canal."""
    if 0x80 <= status <= 0xEF:
        kind = (status & 0xF0)
        ch = (status & 0x0F) + 1  # canal 1..16
        if kind == 0x80: return 'note_off', ch
        if kind == 0x90: return 'note_on', ch
        if kind == 0xB0: return 'cc', ch
        if kind == 0xE0: return 'pitchbend', ch
        # (podrías añadir aftertouch/program change si los necesitas)
    return None, None

def main():
    pygame.midi.init()

    # Elegir puerto si no está fijado
    in_id = 1
    

    print(f"\nAbriendo dispositivo MIDI ID {in_id}...\n")
    midi_in = pygame.midi.Input(in_id)

    print("Escuchando (Ctrl+C para salir). Mostrando solo Note On/Off (y CC si activas la bandera).")
    show_cc = True  # pon True si quieres ver CC

    try:
        while True:
            if midi_in.poll():
                events = midi_in.read(20)  # hasta 20 de golpe para no saturar
                for data, ts in events:
                    status, d1, d2, _ = data
                    # Filtra mensajes "real-time" (clock, etc.)
                    if is_realtime(status):
                        continue
                    
                    kind, ch = status_type(status)
                    if kind == 'note_on':
                        # Convención: Note On con velocity 0 equivale a Note Off
                        if d2 == 0:
                            print(f"[{ts:>8} ms] Note Off  ch={ch:2d} note={d1:3d}")
                        else:
                            print(f"[{ts:>8} ms] Note On   ch={ch:2d} note={d1:3d} vel={d2:3d}")
                    elif kind == 'note_off':
                        print(f"[{ts:>8} ms] Note Off  ch={ch:2d} note={d1:3d} vel={d2:3d}")
                    elif kind == 'cc' and show_cc:
                        print(f"[{ts:>8} ms] CC       ch={ch:2d} ctrl={d1:3d} val={d2:3d}")
                    # opcional: elif kind == 'pitchbend': ...
            else:
                time.sleep(0.005)  # descansa un poco la CPU
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    finally:
        del midi_in
        pygame.midi.quit()

if __name__ == "__main__":
    main()
