import glfw
import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import glm  # Use glm for matrix operations

# Initialize GLFW
if not glfw.init():
    raise Exception("GLFW can't be initialized")

# Create a windowed mode window and its OpenGL context
window = glfw.create_window(800, 600, "ModernGL Text Rendering", None, None)
if not window:
    glfw.terminate()
    raise Exception("GLFW window can't be created")

# Make the window's context current
glfw.make_context_current(window)

# ModernGL context
ctx = moderngl.create_context()

# Generate text using Pillow
font = ImageFont.truetype("arial.ttf", 64)  # Replace with the font path
text = "Hello ModernGL!"
image = Image.new('RGBA', (512, 128), (0, 0, 0, 0))  # Transparent background
draw = ImageDraw.Draw(image)
draw.text((10, 10), text, font=font, fill=(255, 255, 255, 255))  # White text
# Flip the image vertically
image = image.transpose(Image.FLIP_TOP_BOTTOM)
# Create texture
texture = ctx.texture(image.size, 4, image.tobytes())
texture.use()

# Shaders
vertex_shader = '''
#version 330

in vec2 in_vert;
in vec2 in_texcoord;

out vec2 uv;

uniform mat4 model;
uniform mat4 proj;

void main() {
    uv = in_texcoord;
    gl_Position = proj * model * vec4(in_vert, 0.0, 1.0);
}
'''

fragment_shader = '''
#version 330

in vec2 uv;
out vec4 fragColor;

uniform sampler2D text_texture;

void main() {
    vec4 texColor = texture(text_texture, uv);
    fragColor = texColor;
}
'''

# Compile shaders
prog = ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

# Quad vertices
vertices = np.array([
    -1.0, -1.0, 0.0, 0.0,
     1.0, -1.0, 1.0, 0.0,
     1.0,  1.0, 1.0, 1.0,
    -1.0,  1.0, 0.0, 1.0,
], dtype='f4')

indices = np.array([0, 1, 2, 0, 2, 3], dtype='i4')

# Create buffers
vbo = ctx.buffer(vertices)
ibo = ctx.buffer(indices)

# Create VAO
vao = ctx.vertex_array(prog, [(vbo, '2f 2f', 'in_vert', 'in_texcoord')], ibo)

# Projection and Model matrices
proj = glm.ortho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
model = glm.mat4(1.0)

prog['proj'].write(np.array(proj, dtype='f4', order='C'))
prog['model'].write(np.array(model, dtype='f4', order='C'))

# Render loop
while not glfw.window_should_close(window):
    # Clear the screen
    ctx.clear(0.1, 0.1, 0.1, 1.0)
    vao.render(moderngl.TRIANGLES)

    # Swap front and back buffers
    glfw.swap_buffers(window)

    # Poll for and process events
    glfw.poll_events()

# Clean up and close
glfw.terminate()
