from codevision.ui.analysis_panel import AnalysisPanel


def test_space_toolbar_zoom_scales_board_and_zoom_out_reverses_it() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    space._set_canvas_extent("width", 200)
    space._set_canvas_extent("height", 120)

    space.tool_buttons["Zoom In"].emit("clicked")
    assert space.zoom.scale == 1.25
    assert space.canvas.get_content_width() == 250
    assert space.canvas.get_content_height() == 150

    space.tool_buttons["Zoom Out"].emit("clicked")
    assert space.zoom.scale == 1.0
    assert space.canvas.get_content_width() == 200
    assert space.canvas.get_content_height() == 120


def test_analysis_panel_zoom_controls_also_zoom_space() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    panel.section_buttons["Space"].set_active(True)

    assert panel.zoom_in_button.get_sensitive()
    assert panel.zoom_out_button.get_sensitive()
    panel.zoom_in_button.emit("clicked")
    assert space.zoom.scale == 1.25
    panel.zoom_out_button.emit("clicked")
    assert space.zoom.scale == 1.0


def test_space_zoom_clamps_and_transforms_pointer_coordinates() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]

    for _ in range(20):
        space.zoom_in()
    assert space.zoom.scale == space.zoom.MAX_SCALE

    for _ in range(40):
        space.zoom_out()
    assert space.zoom.scale == space.zoom.MIN_SCALE
    assert space.zoom.to_board(40, 20) == (100, 50)
