#version 430

layout(location = 0) in vec2 in_pos_text;    // Text vertex position (local coordinates)
layout(location = 1) in vec2 in_texcoord;    // Texture coordinates

uniform mat4 u_vp;           // Shared view-projection matrix

layout(std430, binding = 0) buffer ModelMatrices {
    mat4 u_model[];  // Dynamically sized array of model matrices
};

uniform float u_text_scale;  // Scale for text in screen space

out vec2 frag_texcoord;      // Pass texture coordinates to the fragment shader

void main() {
    // Scale text in screen space
    vec4 model_space_pos = vec4(in_pos_text * u_text_scale, 0.0, 1.0);

    // Compute world-space position using model and VP matrices
    vec4 world_space_pos = u_vp * u_model[gl_InstanceID] * vec4(0.0, 0.0, 0.0, 1.0);

    // Final screen-space position
    gl_Position = world_space_pos + model_space_pos;

    // Pass through texture coordinates
    frag_texcoord = in_texcoord;
}
