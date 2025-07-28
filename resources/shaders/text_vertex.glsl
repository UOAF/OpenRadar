#version 330

in vec2 in_pos_text;
in vec2 in_pos_world;
in vec2 in_texcoord;

uniform mat4 camera;
uniform float font_to_world;
uniform float u_scale;

out vec2 frag_texcoord;

void main() {
    frag_texcoord = in_texcoord;
    vec2 world = in_pos_text * u_scale * font_to_world + in_pos_world;
    gl_Position = camera * vec4(world, 0.0, 1.0);
    frag_texcoord = in_texcoord;
}
