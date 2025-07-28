#version 330

in vec2 in_pos_text;
in vec2 in_pos_world;
in vec2 in_texcoord;
in vec2 in_pos_str_offset;

uniform mat4 camera;
uniform float font_to_world;
uniform float u_scale;

out vec2 frag_texcoord;

void main() {
    frag_texcoord = in_texcoord;
    vec2 model = in_pos_str_offset + in_pos_text;
    vec2 world = model * u_scale * font_to_world + in_pos_world;
    gl_Position = camera * vec4(world, 0.0, 1.0);
    frag_texcoord = in_texcoord;
}
