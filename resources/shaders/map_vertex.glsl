#version 330 core

uniform mat4 camera;
uniform vec3 position;
uniform float scale;

layout(location = 0) in vec2 in_vertex;
layout(location = 1) in vec2 in_uv;

out vec3 v_vertex;
out vec2 v_uv;

void main() {
    vec3 vert = vec3(in_vertex, 0.0);
    v_vertex = position+vert*scale;
    v_uv = in_uv;

    gl_Position = camera*vec4(v_vertex, 1.0);
}
