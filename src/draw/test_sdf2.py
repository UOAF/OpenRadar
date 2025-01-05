import moderngl
import numpy as np
import glm
import json
import os
from PIL import Image
import glfw

# Initialize GLFW
if not glfw.init():
    raise Exception("GLFW cannot be initialized!")

# Create a window
window_width, window_height = 1300, 600
window = glfw.create_window(window_width, window_height, "SDF Text Rendering", None, None)
if not window:
    glfw.terminate()
    raise Exception("GLFW window cannot be created!")

glfw.make_context_current(window)

# Create ModernGL context
context = moderngl.create_context()


# Load SDF Atlas and JSON Metadata
def load_atlas(atlas_image_path, atlas_json_path):
    # Load the atlas texture
    atlas_image = Image.open(atlas_image_path).convert("RGBA")
    atlas_texture = context.texture(atlas_image.size, 4, atlas_image.tobytes())
    atlas_texture.use()

    # Debug: Display the image dimensions
    print(f"Atlas loaded: {atlas_image_path} ({atlas_image.size[0]}x{atlas_image.size[1]})")

    # Load JSON metadata
    with open(atlas_json_path, 'r') as f:
        atlas_metadata = json.load(f)

    return atlas_texture, atlas_metadata


# Define paths using os.path.join
base_path = "resources/fonts"
atlas_image_path = os.path.join(base_path, "atlas.png")
atlas_json_path = os.path.join(base_path, "atlas.json")

atlas_texture, atlas_metadata = load_atlas(atlas_image_path, atlas_json_path)
glyphs = atlas_metadata['glyphs']
atlas_width = atlas_metadata['atlas']['width']
atlas_height = atlas_metadata['atlas']['height']

# Compile shaders
vertex_shader = """
#version 330
in vec2 in_position;
in vec2 in_texcoord;
uniform mat4 projection;
out vec2 frag_texcoord;
void main() {
    gl_Position = projection * vec4(in_position, 0.0, 1.0);
    frag_texcoord = in_texcoord;
}
"""

fragment_shader = \
"""#version 330
in vec2 frag_texcoord;
out vec4 frag_color;
uniform sampler2D sdf_texture;
// uniform vec4 fgColor;

float median(float r, float g, float b) {
    return max(min(r, g), min(max(r, g), b));
}

void main() {
    vec3 msd = texture(sdf_texture, frag_texcoord).rgb;
    float sd = median(msd.r, msd.g, msd.b);
    float screenPxDistance = 5.0*(sd - 0.5);
    float opacity = clamp(screenPxDistance + 0.5, 0.0, 1.0);
    vec4 bgColor = vec4(0.0, 0.0, 0.0, 0.0);
    vec4 fgColor = vec4(1.0, 1.0, 1.0, 1.0);
    frag_color = mix(bgColor, fgColor, opacity);
}
"""

program = context.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

# Quad and index buffers
quad = np.array([
    [-0.5, -0.5, 0.0, 0.0],
    [0.5, -0.5, 1.0, 0.0],
    [0.5, 0.5, 1.0, 1.0],
    [-0.5, 0.5, 0.0, 1.0],
],
                dtype='f4')

indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')

vbo = context.buffer(quad.tobytes())
ibo = context.buffer(indices.tobytes())
vao = context.simple_vertex_array(program, vbo, 'in_position', 'in_texcoord', index_buffer=ibo)

# Orthographic projection using glm
projection = glm.ortho(0, window_width, window_height, 0, -1, 1)


# Text rendering function
def render_text(text, x, y, scale=32):
    cursor_x = x
    for char in text:
        if char == ' ':
            cursor_x += 0.5 * scale
            continue
        # Skip characters without glyph data
        index = ord(char) - 32
        if index < 0 or index >= len(glyphs):
            # print(f"Skipping unknown character: {char}")
            continue

        glyph = glyphs[index]
        if 'planeBounds' not in glyph or 'atlasBounds' not in glyph:
            print(f"Skipping incomplete glyph: {index}")
            continue  # Skip glyphs without valid bounds

        # Glyph metrics
        plane = glyph['planeBounds']
        atlas = glyph['atlasBounds']
        advance = glyph['advance']

        # Scale glyph size
        quad_x = plane['left'] * scale
        quad_y = plane['bottom'] * scale
        quad_w = plane['right'] * scale
        quad_h = plane['top'] * scale
        advance *= scale

        glyph_bottom = atlas_height - atlas['bottom']
        glyph_top = atlas_height - atlas['top']

        # Calculate texture coordinates
        tex_x = atlas['left'] / atlas_width
        tex_y = (glyph_top) / atlas_height
        tex_w = (atlas['right'] - atlas['left']) / atlas_width
        tex_h = (glyph_top - glyph_bottom) / atlas_height

        # Debug: Print glyph metrics
        # print(f"Rendering '{char}': tex=({tex_x}, {tex_y}, {tex_w}, {tex_h})")

        # Set up vertex data
        quad = np.array([
            [cursor_x + quad_x, y - quad_y, tex_x, tex_y - tex_h],
            [cursor_x + quad_w, y - quad_y, tex_x + tex_w, tex_y - tex_h],
            [cursor_x + quad_w, y - quad_h, tex_x + tex_w, tex_y],
            [cursor_x + quad_x, y - quad_h, tex_x, tex_y],
        ],
                        dtype='f4')

        vbo.write(quad.tobytes())

        # Render glyph
        vao.render(moderngl.TRIANGLES)

        # Advance cursor
        cursor_x += advance


# Main rendering loop
while not glfw.window_should_close(window):
    glfw.poll_events()

    # Clear screen
    context.clear(0.1, 0.1, 0.1, 1.0)

    # Set uniform values
    program['projection'].write(np.array(projection.to_list(), dtype='f4'))
    # Render text
    render_text("The quick brown fox jumps over the lazy dog!", x=100, y=200)

    # Swap buffers
    glfw.swap_buffers(window)

# Cleanup
glfw.terminate()
