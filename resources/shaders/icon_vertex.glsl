#version 460

layout(std430, binding = 0) buffer TVertex
{
   vec4 vertex[]; 
};

// Instance data as a struct - matches IconRenderData structure
struct IconInstance {
    vec2 position;    // x, y world coords
    float scale;      // Scale factor per icon
    float _buffer;    // Padding for alignment
    vec4 color;       // RGBA normalized 0.0-1.0
    
};

layout(std430, binding = 1) buffer IconInstanceData
{
    IconInstance instances[];
};

uniform mat4  u_mvp;
uniform vec2  u_resolution;
uniform float u_width;
uniform float u_point_size;  // Size of center point quad in pixels

out vec4 o_color;

void main()
{
    int instance_id = gl_InstanceID;
    int vertex_id = gl_VertexID;

    // Get instance data
    IconInstance inst = instances[instance_id];
    
    // Calculate number of line segments in the shape
    int num_line_segments = (vertex.length() - 1);
    int line_vertices = num_line_segments * 6;  // 6 vertices per line segment
    
    // Check if this vertex is part of the center point quad (last 6 vertices)
    if (vertex_id >= line_vertices) {
        // Render center point quad
        int quad_vertex = vertex_id - line_vertices;
        
        // Transform center position to screen space
        vec4 center_pos = u_mvp * vec4(inst.position, 0.0, 1.0);
        center_pos.xyz /= center_pos.w;
        center_pos.xy = (center_pos.xy + 1.0) * 0.5 * u_resolution;
        
        // Calculate quad vertices (2 triangles = 6 vertices)
        vec4 pos;
        float half_size = u_point_size * 0.5;
        
        if (quad_vertex == 0) {
            // Bottom-left
            pos = vec4(center_pos.xy + vec2(-half_size, -half_size), center_pos.zw);
        } else if (quad_vertex == 1) {
            // Top-left
            pos = vec4(center_pos.xy + vec2(-half_size, half_size), center_pos.zw);
        } else if (quad_vertex == 2) {
            // Bottom-right
            pos = vec4(center_pos.xy + vec2(half_size, -half_size), center_pos.zw);
        } else if (quad_vertex == 3) {
            // Top-right
            pos = vec4(center_pos.xy + vec2(half_size, half_size), center_pos.zw);
        } else if (quad_vertex == 4) {
            // Bottom-right (second triangle)
            pos = vec4(center_pos.xy + vec2(half_size, -half_size), center_pos.zw);
        } else { // quad_vertex == 5
            // Top-left (second triangle)
            pos = vec4(center_pos.xy + vec2(-half_size, half_size), center_pos.zw);
        }
        
        // Convert back to normalized device coordinates
        pos.xy = pos.xy / u_resolution * 2.0 - 1.0;
        pos.xyz *= pos.w;
        gl_Position = pos;
        o_color = inst.color;
        return;
    }
    
    // Render icon shape lines (existing logic)
    int line_i = vertex_id / 6;
    int tri_i  = vertex_id % 6;
    
    vec4 va[4];
    for (int i=0; i<4; ++i)
    {
        vec4 offset = vec4(inst.position, 0, 0);
        va[i] = u_mvp * (vertex[line_i+i] + offset);
        va[i].xyz /= va[i].w;
        va[i].xy = (va[i].xy + 1.0) * 0.5 * u_resolution + (inst.scale, inst.scale) * vertex[line_i+i].xy;
    }
    // va is vertex[line_i], vertex[line_i+1], vertex[line_i+2], vertex[line_i+3] in screen space
    // offset and scaled

    vec2 v_line  = normalize(va[2].xy - va[1].xy);  // unit vector parallel to vertex 1 and 2
    vec2 nv_line = vec2(-v_line.y, v_line.x);       // unit vector Normal to v_line
    
    vec4 pos;
    if (tri_i == 0 || tri_i == 1 || tri_i == 3) // 0, 1, 3 are the first triangle bordering the left edge
    {
        vec2 v_pred  = normalize(va[1].xy - va[0].xy); // unit vector parallel to vertex 0 and 1
        vec2 v_miter = normalize(nv_line + vec2(-v_pred.y, v_pred.x)); // normal from 1 to 2 plus normal from 0 to 1

        pos = va[1];
        pos.xy += v_miter * u_width * (tri_i == 1 ? -0.5 : 0.5) / dot(v_miter, nv_line);
    }
    else // 2, 4, 5 are the second triangle bordering the right edge
    {
        vec2 v_succ  = normalize(va[3].xy - va[2].xy);
        vec2 v_miter = normalize(nv_line + vec2(-v_succ.y, v_succ.x));

        pos = va[2];
        pos.xy += v_miter * u_width * (tri_i == 5 ? 0.5 : -0.5) / dot(v_miter, nv_line);
    }

    pos.xy = pos.xy / u_resolution * 2.0 - 1.0;
    pos.xyz *= pos.w;
    gl_Position = pos;

    o_color = inst.color;
}
