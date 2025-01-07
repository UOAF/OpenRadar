import pygame
import config

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
        
def get_surface_from_image(image_path, surface_size = None):
    
    path = config.bundle_dir / image_path
    extension = path.suffix
    
    if extension == ".svg" and surface_size is not None:
        return pygame.image.load_sized_svg(str(path.absolute()), surface_size)

    image = pygame.image.load(str((config.bundle_dir / image_path).absolute()))
    if surface_size is not None:
        image = pygame.transform.scale(image, surface_size)
    return image
 
def load_icon_from_svg(image_path, raster_size = (64, 64)):
    pygame.image.load_sized_svg(image_path, raster_size)