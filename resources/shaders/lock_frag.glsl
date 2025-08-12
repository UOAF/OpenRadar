#version 460

const float PI = 3.1415926535897932384626433832795;

in vec4 o_color;
in float o_line_progress;

out vec4 fragColor;

uniform float u_time;
// uniform mat4 u_mvp; // We'll extract zoom from this

void main()
{
    // Extract zoom/scale from MVP matrix
    // float zoom = length(vec2(u_mvp[0][0], u_mvp[1][0]));

    float wave_frequency = 0.005; // Scale frequency by zoom level
    float phase = wave_frequency * o_line_progress - u_time / 2;
    float wave_input = fract(phase); // Get fractional part to create repeating pattern [0,1]
    

    float wave;
    if (wave_input < 0.5) {
        wave = 0.8 * smoothstep(0.0, 0.3, wave_input);
    } else {
        wave = 0.8 * smoothstep(1.0, 0.7, wave_input);
    }
    
    float final_alpha = o_color.a * wave;

    fragColor = vec4(o_color.rgb, clamp(final_alpha, 0.2, 0.8));
    // fragColor = o_color;
}