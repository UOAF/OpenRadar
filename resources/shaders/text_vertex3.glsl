#version 330

layout(location = 0) in vec2 in_pos_text;    // Text vertex position (screen coordinates)
layout(location = 1) in vec2 in_texcoord;    // Texture coordinates

uniform mat4 u_proj;          // Projection matrix
uniform vec2 u_offset;        // Offset in pixels

out vec2 frag_texcoord;      // Pass texture coordinates to the fragment shader

void main() {
    // Final screen-space position
    gl_Position = u_proj * (vec4(in_pos_text, 0.0, 1.0) + vec4(u_offset, 0.0, 0.0));

    // Pass through texture coordinates
    frag_texcoord = in_texcoord;
}
