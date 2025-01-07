import moderngl
import numpy as np
import json
from PIL import Image
import glm
import glfw

# Initialize GLFW
if not glfw.init():
    raise Exception("GLFW can't be initialized")

# Create a GLFW window
window = glfw.create_window(800, 600, "MSDF Dynamic Text Rendering", None, None)
glfw.make_context_current(window)

# Create ModernGL context
ctx = moderngl.create_context()

# Load the MSDF atlas and metadata
atlas_image = Image.open('resources/fonts/atlas.png').convert('RGBA')
atlas_texture = ctx.texture(atlas_image.size, 4, atlas_image.tobytes())
atlas_texture.use(0)  # Explicitly bind texture to unit 0

with open('resources/fonts/atlas.json') as f:
    atlas_data = json.load(f)

# Extract atlas details
atlas_width = atlas_data['atlas']['width']
atlas_height = atlas_data['atlas']['height']
distance_range = atlas_data['atlas']['distanceRange']
font_size = atlas_data['atlas']['size']
glyphs = atlas_data['glyphs']

# Shader Program
vertex_shader = '''
#version 330

in vec2 in_vert;
in vec2 in_texcoord;

out vec2 uv;

uniform mat4 model;
uniform mat4 proj;

void main() {
    uv = in_texcoord; // No flipping
    gl_Position = proj * model * vec4(in_vert, 0.0, 1.0);
}
'''

fragment_shader = '''
#version 330

in vec2 uv;
out vec4 fragColor;

uniform sampler2D atlas;
uniform float smoothing;

void main() {
    vec3 msdf = texture(atlas, uv).rgb;
    float dist = max(min(msdf.r, msdf.g), msdf.b); // MSDF interpolation
    float alpha = smoothstep(0.5 - smoothing, 0.5 + smoothing, dist);
    fragColor = vec4(1.0, 1.0, 1.0, alpha); // White text with transparency
}
'''

prog = ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
prog['atlas'].value = 0 # type: ignore
prog['smoothing'].value = distance_range / font_size # type: ignore

# Projection Matrix
proj = glm.ortho(0, 800, 0, 600, -1, 1)  # Y-axis flipped for bottom-left origin
prog['proj'].write(np.array(proj.to_list(), dtype='f4', order='C')) # type: ignore

# Model Matrix
model = glm.mat4(1.0)  # Identity matrix
prog['model'].write(np.array(model.to_list(), dtype='f4', order='C')) # type: ignore

# Create dynamic VBO and VAO
vbo = ctx.buffer(reserve=1024 * 16)  # Reserve space for vertices
ibo = ctx.buffer(reserve=1024 * 4)   # Reserve space for indices
vao = ctx.vertex_array(prog, [(vbo, '2f 2f', 'in_vert', 'in_texcoord')], ibo)

# Build vertices and indices for text

def build_text(text, x, y, scale=1.0):
    vertices = []
    indices = []
    cursor_x = x
    cursor_y = y
    index_offset = 0

    for i, char in enumerate(text):
        glyph = next((g for g in glyphs if g['index'] == ord(char)), None)
        if not glyph:
            continue

        # Get UV coordinates
        u0 = glyph['atlasBounds']['left'] / atlas_width
        v0 = glyph['atlasBounds']['bottom'] / atlas_height
        u1 = glyph['atlasBounds']['right'] / atlas_width
        v1 = glyph['atlasBounds']['top'] / atlas_height

        # Scale plane bounds
        px_scale = (distance_range / font_size) * scale
        plane_left = glyph['planeBounds']['left'] * px_scale
        plane_bottom = glyph['planeBounds']['bottom'] * px_scale
        plane_right = glyph['planeBounds']['right'] * px_scale
        plane_top = glyph['planeBounds']['top'] * px_scale

        # Debug output
        print(f"Glyph {char}: Plane ({plane_left}, {plane_bottom}) to ({plane_right}, {plane_top})")
        print(f"Glyph {char}: UV ({u0}, {v0}) to ({u1}, {v1})")

        # Build vertices for this glyph
        quad = [
            cursor_x + plane_left, cursor_y + plane_bottom, u0, v0,  # Bottom-left
            cursor_x + plane_right, cursor_y + plane_bottom, u1, v0,  # Bottom-right
            cursor_x + plane_right, cursor_y + plane_top, u1, v1,  # Top-right
            cursor_x + plane_left, cursor_y + plane_top, u0, v1   # Top-left
        ]
        print(f"Quad: {quad}")
        vertices.extend(quad)
        
        

        # Build indices for this glyph
        indices.extend([
            index_offset, index_offset + 1, index_offset + 2,
            index_offset, index_offset + 2, index_offset + 3
        ])

        index_offset += 4
        cursor_x += glyph['advance'] * px_scale  # Scale advance

    print(f"Vertices: {len(vertices) // 4}, Indices: {len(indices) // 6}")
    return np.array(vertices, dtype='f4'), np.array(indices, dtype='i4')

# Main loop
target_text = "Hello MSDF!"
vertices, indices = build_text(target_text, 100, 300, scale=1.0)
vbo.write(vertices)
ibo.write(indices)

while not glfw.window_should_close(window):
    glfw.poll_events()
    ctx.clear(0.1, 0.1, 0.1, 1.0)

    vao.render(moderngl.TRIANGLES)
    glfw.swap_buffers(window)

# Cleanup
glfw.terminate()
