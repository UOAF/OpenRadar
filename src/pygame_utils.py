import pygame

def draw_dashed_line(surface, color, start_pos, end_pos, width=1, dash_length=4):
    origin = pygame.Vector2(start_pos)
    target = pygame.Vector2(end_pos)
    displacement = target - origin
    if displacement.length() < 1: # if the line is too short, just
        return
    length = displacement.length()
    displacement.normalize_ip() #TODO some bug here, fix it later
    for index in range(0, int(length/dash_length), 2):
        start = origin + displacement * dash_length * index
        end = origin + displacement * dash_length * (index + 1)
        pygame.draw.line(surface, color, start, end, width)