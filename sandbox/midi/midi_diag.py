import pygame.midi

pygame.midi.init()

for i in range(pygame.midi.get_count()):
    info = pygame.midi.get_device_info(i)
    interf, name, input_dev, output_dev, opened = info
    print(f"ID {i} -> {name.decode()} | Input: {bool(input_dev)} | Output: {bool(output_dev)}")