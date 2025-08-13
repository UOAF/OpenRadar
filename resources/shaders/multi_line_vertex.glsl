#version 460

struct LinePoint {
    vec2 position;  // x, y world coordinates
};

struct LineMetadata {
    uint start_index;   // Start index in points array
    uint end_index;     // End index in points array (exclusive)
    float width;        // Line width
    vec4 color;         // RGBA normalized 0.0-1.0
};

layout(std430, binding = 0) buffer TLinePoints
{
    LinePoint points[];
};

layout(std430, binding = 1) buffer TLineMetadata
{
    LineMetadata lines[];
};

uniform mat4  u_mvp;
uniform vec2  u_resolution;
uniform float u_width;

out vec4 o_color;

void main()
{
    // Each line segment is rendered as 2 triangles (6 vertices)
    int segment_i = gl_VertexID / 6;  // Which line segment within the line
    int tri_i = gl_VertexID % 6;      // Which vertex within the segment (0-5)
    
    LineMetadata line = lines[gl_InstanceID];
    
    // Calculate actual point indices for this segment
    uint line_start = line.start_index;
    uint line_end = line.end_index;
    uint line_length = line_end - line_start;
    
    // If we don't have enough points for this segment, discard
    if (line_length < 2 || uint(segment_i) >= (line_length - 1)) {
        gl_Position = vec4(0, 0, 0, 0);
        o_color = vec4(0, 0, 0, 0);
        return;
    }
    
    // Get the current segment points
    uint p0_idx = line_start + uint(segment_i);     // Current point
    uint p1_idx = line_start + uint(segment_i) + 1; // Next point
    
    // Get world coordinates for the segment
    vec2 p0_world = points[p0_idx].position;
    vec2 p1_world = points[p1_idx].position;
    
    // Transform to screen space
    vec4 p0_screen = u_mvp * vec4(p0_world, 0, 1);
    vec4 p1_screen = u_mvp * vec4(p1_world, 0, 1);
    
    p0_screen.xyz /= p0_screen.w;
    p1_screen.xyz /= p1_screen.w;
    
    p0_screen.xy = (p0_screen.xy + 1.0) * 0.5 * u_resolution;
    p1_screen.xy = (p1_screen.xy + 1.0) * 0.5 * u_resolution;
    
    // Calculate line direction and normal
    vec2 line_dir = normalize(p1_screen.xy - p0_screen.xy);
    vec2 line_normal = vec2(-line_dir.y, line_dir.x);
    
    // Use line width (override with uniform if specified)
    float width = line.width;
    if (u_width > 0.0) {
        width = u_width;
    }
    
    // Calculate miter adjustments for start and end caps
    vec2 start_miter = line_normal;
    vec2 end_miter = line_normal;
    
    // Calculate start cap miter (if this is the first segment)
    if (segment_i == 0) {
        // This is the start of the line - use perpendicular to line
        start_miter = line_normal;
    } else {
        // Calculate miter with previous segment
        uint prev_idx = p0_idx - 1;
        if (prev_idx >= line_start) {
            vec2 prev_world = points[prev_idx].position;
            vec4 prev_screen = u_mvp * vec4(prev_world, 0, 1);
            prev_screen.xyz /= prev_screen.w;
            prev_screen.xy = (prev_screen.xy + 1.0) * 0.5 * u_resolution;
            
            vec2 prev_dir = normalize(p0_screen.xy - prev_screen.xy);
            vec2 prev_normal = vec2(-prev_dir.y, prev_dir.x);
            
            start_miter = normalize(line_normal + prev_normal);
            // Avoid excessive miter length
            float miter_dot = dot(start_miter, line_normal);
            if (miter_dot > 0.1) {
                start_miter = start_miter / miter_dot;
            } else {
                start_miter = line_normal;
            }
        }
    }
    
    // Calculate end cap miter (if this is the last segment)
    if (uint(segment_i) == (line_length - 2)) {
        // This is the end of the line - use perpendicular to line
        end_miter = line_normal;
    } else {
        // Calculate miter with next segment
        uint next_idx = p1_idx + 1;
        if (next_idx < line_end) {
            vec2 next_world = points[next_idx].position;
            vec4 next_screen = u_mvp * vec4(next_world, 0, 1);
            next_screen.xyz /= next_screen.w;
            next_screen.xy = (next_screen.xy + 1.0) * 0.5 * u_resolution;
            
            vec2 next_dir = normalize(next_screen.xy - p1_screen.xy);
            vec2 next_normal = vec2(-next_dir.y, next_dir.x);
            
            end_miter = normalize(line_normal + next_normal);
            // Avoid excessive miter length
            float miter_dot = dot(end_miter, line_normal);
            if (miter_dot > 0.1) {
                end_miter = end_miter / miter_dot;
            } else {
                end_miter = line_normal;
            }
        }
    }
    
    // Generate vertex position based on triangle vertex index
    vec4 pos;
    if (tri_i == 0 || tri_i == 1 || tri_i == 3) {
        // Vertices on the start of the segment
        pos = p0_screen;
        pos.xy += start_miter * width * (tri_i == 1 ? -0.5 : 0.5);
    } else {
        // Vertices on the end of the segment (tri_i == 2, 4, 5)
        pos = p1_screen;
        pos.xy += end_miter * width * (tri_i == 5 ? 0.5 : -0.5);
    }
    
    // Convert back to normalized device coordinates
    pos.xy = pos.xy / u_resolution * 2.0 - 1.0;
    pos.xyz *= pos.w;
    
    gl_Position = pos;
    o_color = line.color;
}
