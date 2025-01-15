#version 330 core

uniform sampler2D Texture;
uniform float alpha;

in vec3 v_vertex;
in vec2 v_uv;

layout(location = 0) out vec4 out_color;

void main() {
    vec2 uvp = v_uv;
    // uncomment to flip vertically
    // uvp.y = 1 - uvp.y;
    out_color = vec4(texture(Texture, uvp).xyz, alpha);

}
