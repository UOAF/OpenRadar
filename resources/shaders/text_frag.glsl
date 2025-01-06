#version 330
in vec2 frag_texcoord;
out vec4 frag_color;
uniform sampler2D sdf_texture;

float median(float r, float g, float b) {
    return max(min(r, g), min(max(r, g), b));
}

void main() {
    vec3 msd = texture(sdf_texture, frag_texcoord).rgb;
    float sd = median(msd.r, msd.g, msd.b);
    float screenPxDistance = 5.0*(sd-0.5);
    float opacity = clamp(screenPxDistance+0.5, 0.0, 1.0);
    vec4 bgColor = vec4(0.0, 0.0, 0.0, 0.0);
    vec4 fgColor = vec4(1.0, 1.0, 1.0, 1.0);
    frag_color = mix(bgColor, fgColor, opacity);
}
