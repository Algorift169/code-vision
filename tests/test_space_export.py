from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.space.space_export import SpaceExporter
from codevision.space.space_view import SpaceView


def test_space_export_png_and_pdf_preserve_live_board(tmp_path):
    space = SpaceView()
    text_box = space.add_text_box(text="Board text", position=(30, 40))
    space.pen.add_strokes([[(10, 10), (50, 30), (90, 20)]])

    exporter = SpaceExporter()
    png_path = exporter.export_png(space, tmp_path / "board.png")
    pdf_path = exporter.export_pdf(space, tmp_path / "board.pdf")

    assert text_box in space.text_boxes
    assert space.pen.strokes
    assert png_path.is_file() and png_path.stat().st_size > 0
    assert pdf_path.is_file() and pdf_path.stat().st_size > 0


def test_export_dialog_space_mode_only_exposes_png_and_pdf(tmp_path):
    parent = Gtk.Window(title="Test")
    panel = Gtk.Box()
    panel._section_placeholders = {"Space": object()}

    from codevision.ui.export.export_dialog import ExportDialog

    dialog = ExportDialog(parent, panel, tmp_path, initial_section="Space")

    assert set(dialog.format_checks) == {"png", "pdf"}
    assert dialog.format_checks["png"].get_active()
    assert dialog.format_checks["pdf"].get_active()
