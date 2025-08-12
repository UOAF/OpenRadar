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

out vec4 o_color;

void main()
{
    int instance_id = gl_InstanceID;
    int line_i = gl_VertexID / 6;
    int tri_i  = gl_VertexID % 6;

    // Get instance data
    IconInstance inst = instances[instance_id];
    
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
