#version 460

// Instance data as a struct - matches LockLineRenderData structure
struct LineInstance {
    vec2 start_position;  // x, y world coords
    vec2 end_position;    // x, y world coords  
    vec4 color;          // RGBA normalized 0.0-1.0
};

layout(std430, binding = 0) buffer LineInstanceData
{
    LineInstance instances[];
};

uniform mat4  u_mvp;
uniform vec2  u_resolution;
uniform float u_width;
uniform float u_time;

out vec4 o_color;
out float o_line_progress;

void main()
{
    int instance_id = gl_InstanceID;
    int vertex_id = gl_VertexID;
    
    // Get instance data
    LineInstance inst = instances[instance_id];
    
    // Transform start and end positions to screen space
    vec4 start_screen = u_mvp * vec4(inst.start_position, 0.0, 1.0);
    vec4 end_screen = u_mvp * vec4(inst.end_position, 0.0, 1.0);
    
    // Perspective divide
    start_screen.xyz /= start_screen.w;
    end_screen.xyz /= end_screen.w;
    
    // Convert to pixel coordinates
    start_screen.xy = (start_screen.xy + 1.0) * 0.5 * u_resolution;
    end_screen.xy = (end_screen.xy + 1.0) * 0.5 * u_resolution;

    float pixel_len = length(end_screen.xy - start_screen.xy);

    // Calculate line direction and normal
    vec2 line_dir = normalize(end_screen.xy - start_screen.xy);
    vec2 line_normal = vec2(-line_dir.y, line_dir.x);
    
    // Generate quad vertices (2 triangles = 6 vertices per line)
    vec4 pos;
    float half_width = u_width * 0.5;
    float line_progress = 0.0;
    
    if (vertex_id == 0) {
        // Bottom-left
        pos = vec4(start_screen.xy - line_normal * half_width, start_screen.zw);
        line_progress = 0.0;
    } else if (vertex_id == 1) {
        // Top-left
        pos = vec4(start_screen.xy + line_normal * half_width, start_screen.zw);
        line_progress = 0.0;
    } else if (vertex_id == 2) {
        // Bottom-right
        pos = vec4(end_screen.xy - line_normal * half_width, end_screen.zw);
        line_progress = 1.0;
    } else if (vertex_id == 3) {
        // Top-right
        pos = vec4(end_screen.xy + line_normal * half_width, end_screen.zw);
        line_progress = 1.0;
    } else if (vertex_id == 4) {
        // Bottom-right (second triangle)
        pos = vec4(end_screen.xy - line_normal * half_width, end_screen.zw);
        line_progress = 1.0;
    } else { // vertex_id == 5
        // Top-left (second triangle)
        pos = vec4(start_screen.xy + line_normal * half_width, start_screen.zw);
        line_progress = 0.0;
    }
    
    // Convert back to normalized device coordinates
    pos.xy = pos.xy / u_resolution * 2.0 - 1.0;
    pos.xyz *= pos.w;
    
    gl_Position = pos;
    o_color = inst.color;
    o_line_progress = line_progress * pixel_len;
}
