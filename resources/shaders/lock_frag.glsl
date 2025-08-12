#version 460

const float PI = 3.1415926535897932384626433832795;

in vec4 o_color;
in float o_line_progress;

out vec4 fragColor;

uniform float u_time;

void main()
{

    // float final_alpha = fragColor.a * sin(2 * PI * o_line_progress + u_time);

    // // float wave_intensity = smoothstep(wave_width, 0.0, wave_distance);

    // fragColor = vec4(fragColor.rgb, clamp(final_alpha, 0.0, 1.0));
    o_color = fragColor;
}