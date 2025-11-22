import time
import pygame
import pygame.midi
from manager.graphics_manager import GraphicsManager
from manager.loop_manager import LoopManager
from manager.midi_manager import MIDIManager

CHANNEL = 9
VEL = 110
INSTRUMENTS = [47, 56, 44, 0]
PERIOD = 3.75

pygame.init()
pygame.midi.init()
clock = pygame.time.Clock()

WIDTH, HEIGHT = 1207, 975
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("☁️ Umpa Bumpa Trommel ☁️")

graphics = GraphicsManager()
graphics.load_assets(screen)

matrix = {
    47: [0, 0.937, 1.875, 2.812],
    56: [0, 0.937, 1.875, 2.812],
    44: [0.468, 0.703, 1.406, 1.640, 2.343, 2.578, 3.281, 3.515],
    0:  [0.   , 0.166, 0.332, 0.498, 0.664, 0.83 , 0.996, 1.162, 1.328,
       1.494, 1.66 , 1.826, 1.992, 2.158, 2.324, 2.49 , 2.656, 2.822,
       2.988, 3.154, 3.32 , 3.486]
}

# 
loop_manager = LoopManager(matrix[INSTRUMENTS[0]], PERIOD)


graphics.set_timeline_from_matrix(matrix)

print("\n=== Dispositivos MIDI ===")
for i in range(pygame.midi.get_count()):
    interf, name, inp, outp, opened = pygame.midi.get_device_info(i)
    print(f"[{i}] {name.decode()} {'(IN)' if inp else '(OUT)' if outp else ''}")

input_id = int(input("\nSelecciona ID de entrada (DATO DUO): "))
output_id = int(input("Selecciona ID de salida (Microsoft GS Wavetable Synth): "))

midi_in = pygame.midi.Input(input_id)
midi_out = pygame.midi.Output(output_id)

midi_manager = MIDIManager(graphics.patterns_completed, matrix, midi_out, vel=VEL, channel=CHANNEL)
midi_manager.set_graphics(graphics)

running = True
last_time = time.time()
fret = 0
result = None

while running:
    now = time.time()
    dt = now - last_time
    last_time = now
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if midi_in and midi_in.poll():
        events = midi_in.read(20)
        for data, ts in events:
            status, cc, value, _ = data
            if (status & 0xF0) == 0xB0:
                if cc == 81 and value >= 64:  # Crush
                    graphics.on_crush()
                    idx = graphics.selected_cloud_index
                    note = INSTRUMENTS[idx % len(INSTRUMENTS)]
                    loop_manager.register_input()
                    midi_out.note_on(note, VEL, CHANNEL)
                    time.sleep(0.05)
                    midi_out.note_off(note, 0, CHANNEL)
            if status == 251 and all(graphics.patterns_completed):
                loop_manager.set_melodie_mode()
                loop_manager.set_expected(matrix[INSTRUMENTS[graphics.selected_cloud_index]])
            if cc == 63:
                if all(graphics.patterns_completed): 
                    fret = fret + 1
                    if fret % 4 == 0:
                        loop_manager.reset()
                        midi_manager.reset()
                else: 
                    graphics.set_msg('Ohne Beat darfst du keine Melodie spielen!', error=True)
            if cc in [49,51,63] and value == 100 and all(graphics.patterns_completed):
                #print(data)
                loop_manager.register_input(cc)
                #elif cc == 71:  # Resonancia → selección nube
                #    graphics.on_resonance(value)
    result = loop_manager.update()
    if result is not None:
        print(result)
    if result == 'progress':
        graphics.anim_img = graphics.nota_img
    elif result == 'trampa':
        graphics.set_msg('Kein Rythmus, keine Wolken!') 
    elif result == 'next':
        if not all(graphics.patterns_completed):
            graphics.patterns_completed[graphics.selected_cloud_index] = True
            graphics.set_nube_buena(graphics.selected_cloud_index)
            graphics.update_bg()
            midi_manager.patterns_completed = graphics.patterns_completed
            #graphics.selected_cloud_index = graphics.selected_cloud_index + 1
            #if not all(graphics.patterns_completed):
            graphics.next_nube()
            graphics.nerv_cloudia()
            graphics._place_clouds(graphics.cloud_imgs, graphics.cloud_imgs_sel, graphics.width)
            graphics._apply_selection(graphics.selected_cloud_index)
            loop_manager.set_expected(matrix[INSTRUMENTS[graphics.selected_cloud_index]])
            graphics.set_msg('Du hast den Beat!')
            loop_manager.user_inputs = []
        else: 
            graphics.set_msg('Du beherschst den Tanz der Wolken!')
    elif result == 'reset':
        midi_manager.reset()
        graphics.tick()
        if not all(graphics.patterns_completed):
            graphics.anim_img = graphics.rayo_img
        else:
            graphics.on_crush()
    elif result == 'lento':
        graphics.set_msg('Fühl den Beat, sei schneller.')
    elif result == 'rapido':
        graphics.set_msg('Fühl den Beat, sei langsamer.')
    elif result == 'end':
        graphics.cloudia = None
        graphics.set_msg('Du hast den Bann gebrochen.')
        graphics.set_end_status()
    
    midi_manager.update()
    graphics.update(dt)
    graphics.draw()
    pygame.display.flip()

del midi_in
midi_out.close()
pygame.midi.quit()
pygame.quit()
