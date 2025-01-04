import numpy as np
import moderngl
import glfw
from glm import mat4, ortho, scale, translate, value_ptr

vert_shader = """
#version 460

layout(std430, binding = 0) buffer TVertex
{
   vec4 vertex[]; 
};

uniform mat4  u_mvp;
uniform vec2  u_resolution;
uniform float u_thickness;

void main()
{
    int line_i = gl_VertexID / 6;
    int tri_i  = gl_VertexID % 6;

    vec4 va[4];
    for (int i=0; i<4; ++i)
    {
        va[i] = u_mvp * vertex[line_i+i];
        va[i].xyz /= va[i].w;
        va[i].xy = (va[i].xy + 1.0) * 0.5 * u_resolution;
    }

    vec2 v_line  = normalize(va[2].xy - va[1].xy);
    vec2 nv_line = vec2(-v_line.y, v_line.x);
    
    vec4 pos;
    if (tri_i == 0 || tri_i == 1 || tri_i == 3)
    {
        vec2 v_pred  = normalize(va[1].xy - va[0].xy);
        vec2 v_miter = normalize(nv_line + vec2(-v_pred.y, v_pred.x));

        pos = va[1];
        pos.xy += v_miter * u_thickness * (tri_i == 1 ? -0.5 : 0.5) / dot(v_miter, nv_line);
    }
    else
    {
        vec2 v_succ  = normalize(va[3].xy - va[2].xy);
        vec2 v_miter = normalize(nv_line + vec2(-v_succ.y, v_succ.x));

        pos = va[2];
        pos.xy += v_miter * u_thickness * (tri_i == 5 ? 0.5 : -0.5) / dot(v_miter, nv_line);
    }

    pos.xy = pos.xy / u_resolution * 2.0 - 1.0;
    pos.xyz *= pos.w;
    gl_Position = pos;
}
"""

frag_shader = """
#version 460

out vec4 fragColor;

void main()
{
    fragColor = vec4(1.0);
}
"""

def main():
    if not glfw.init():
        raise RuntimeError("GLFW initialization failed")

    window = glfw.create_window(800, 600, "ModernGL SSBO Example", None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("Window creation failed")

    glfw.make_context_current(window)
    ctx = moderngl.create_context()

    program = ctx.program(vertex_shader=vert_shader, fragment_shader=frag_shader)

    program['u_resolution'] = (800, 600)
    program['u_thickness'] = 20.0


    # vertices = [
    #     [0.0, -1.0, 0.0, 1.0], [1.0, -1.0, 0.0, 1.0]
    # ]
    # for u in range(0, 91, 10):
    #     a = np.radians(u)
    #     vertices.append([np.cos(a), np.sin(a), 0.0, 1.0])
    # vertices.append([-1.0, 1.0, 0.0, 1.0])
    # for u in range(90, -1, -10):
    #     a = np.radians(u)
    #     vertices.append([np.cos(a) - 1.0, np.sin(a) - 1.0, 0.0, 1.0])
    # vertices.extend([[1.0, -1.0, 0.0, 1.0], [1.0, 0.0, 0.0, 1.0]])
    
    vertices = [
        [0.0, -1.0, 0.0, 1.0], [1.0, -1.0, 0.0, 1.0]
    ]
    for u in range(0, 91, 10):
        a = np.radians(u)
        vertices.append([np.cos(a), np.sin(a), 0.0, 1.0])
    vertices.append([-1.0, 1.0, 0.0, 1.0])
    for u in range(90, -1, -10):
        a = np.radians(u)
        vertices.append([np.cos(a) - 1.0, np.sin(a) - 1.0, 0.0, 1.0])
    vertices.extend([[1.0, -1.0, 0.0, 1.0], [1.0, 0.0, 0.0, 1.0]])

    data = np.array(vertices, dtype='f4')
    ssbo = ctx.buffer(data)
    ssbo.bind_to_storage_buffer(0)

    vao = ctx.vertex_array(program, [])

    while not glfw.window_should_close(window):
        width, height = glfw.get_framebuffer_size(window)
        ctx.viewport = (0, 0, width, height)

        projection = ortho(-1, 1, -1, 1, -1, 1)
        mvp = projection * scale(mat4(1.0), [0.5, 0.5, 1.0])

        program['u_mvp'].write(mvp.to_bytes())

        program['u_resolution'] = (width, height)

        ctx.clear(0.0, 0.0, 0.0)
        vao.render(moderngl.TRIANGLES, vertices=len(vertices) * 6)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
