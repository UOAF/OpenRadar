from imgui_bundle import imgui

def get_imgui_font_atlas():
    """
    Get the ImGui font atlas texture ID.
    """
    io = imgui.get_io()
    return io.fonts.texture_id