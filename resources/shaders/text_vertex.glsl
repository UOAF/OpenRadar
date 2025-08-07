#version 330

// Per-vertex attributes (shared quad)
in vec2 in_quad_pos;         // Quad vertex position (0,0), (1,0), (1,1), (0,1)

// Per-instance attributes (per glyph)
in vec4 in_glyph_bounds;     // Glyph bounds: left, bottom, right, top (in font units)
in vec2 in_cursor_pos;       // Cursor position for this character
in vec2 in_world_pos;        // World position for the text string
in vec4 in_atlas_bounds;     // Atlas bounds: left, bottom, right, top (in atlas pixels)
in vec2 in_string_offset;    // Offset for string alignment (centering, etc.)
in vec2 in_screen_offset;    // Screen space offset in screen pixels

uniform mat4 camera;
uniform float font_to_world; // Scale factor to convert font units to world units
uniform float u_scale;       // User scale factor
uniform vec2 atlas_size;     // Atlas texture size in pixels (width, height)
uniform vec2 u_resolution;   // Viewport size in pixels (width, height)

out vec2 frag_texcoord;

void main() {
    // Calculate glyph position from quad position and glyph bounds
    vec2 glyph_size = in_glyph_bounds.zw-in_glyph_bounds.xy;
    vec2 glyph_pos = in_glyph_bounds.xy+in_quad_pos*glyph_size;

    // Calculate the final position:
    // 1. Start with glyph position relative to its origin
    // 2. Add cursor position to place the glyph in the string
    // 3. Add string offset for alignment (centering, etc.)
    // 4. Scale to world coordinates
    // 5. Add world position
    vec2 local_pos = glyph_pos+in_cursor_pos+in_string_offset;
    vec2 world_pos = local_pos*u_scale*font_to_world+in_world_pos;

    gl_Position = camera*vec4(world_pos, 0.0, 1.0);

    // Convert to screen coordinates, apply screen offset, then back to NDC
    // Similar to screen_polygon_vertex.glsl approach
    gl_Position.xyz /= gl_Position.w;
    vec2 screen_pos = (gl_Position.xy+1.0)*0.5*u_resolution;
    screen_pos += in_screen_offset;
    gl_Position.xy = screen_pos/u_resolution*2.0-1.0;
    gl_Position.xyz *= gl_Position.w;

    // Calculate texture coordinates from atlas bounds and quad position  
    // Use atlas coordinates directly and flip Y at the end
    vec2 atlas_min = vec2(in_atlas_bounds.x, in_atlas_bounds.y);  // left, bottom
    vec2 atlas_max = vec2(in_atlas_bounds.z, in_atlas_bounds.w);  // right, top

    // Interpolate within the glyph rectangle
    vec2 atlas_pos = atlas_min+in_quad_pos*(atlas_max-atlas_min);
    // Normalize and flip Y coordinate
    frag_texcoord = vec2(atlas_pos.x/atlas_size.x, 1.0-atlas_pos.y/atlas_size.y);
}
