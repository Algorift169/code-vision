from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

import gi

gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from ...export.analysis_collector import AnalysisCollector
from ...export.export_manager import ExportManager, ExportResult


class ExportDialog:
    """GTK export action dialog that keeps export work off the UI thread."""

    def __init__(
        self,
        parent: Gtk.Window,
        analysis_panel: Gtk.Widget,
        project_root: Path | None = None,
        initial_section: str | None = None,
    ) -> None:
        self.parent = parent
        self.analysis_panel = analysis_panel
        self.project_root = project_root
        self.initial_section = initial_section
        self._space_mode = initial_section == "Space"
        self.window = Gtk.Window(title="Export Analysis Report", transient_for=parent, modal=False)
        self.window.set_default_size(560, 620)
        self.window.set_resizable(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.set_margin_top(16)
        outer.set_margin_bottom(16)
        self.window.set_child(outer)

        heading = Gtk.Label(label="Export Analysis Report")
        heading.add_css_class("title-1")
        heading.set_halign(Gtk.Align.START)
        outer.append(heading)

        destination = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        destination.set_hexpand(True)
        self.directory_entry = Gtk.Entry()
        self.directory_entry.set_hexpand(True)
        self.directory_entry.set_text(str(project_root or Path.home()))
        browse = Gtk.Button(label="Browse")
        browse.connect("clicked", self._browse_directory)
        destination.append(self.directory_entry)
        destination.append(browse)
        outer.append(Gtk.Label(label="Output directory", xalign=0))
        outer.append(destination)

        filename_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.filename_entry = Gtk.Entry(text="codevision-report")
        self.filename_entry.set_hexpand(True)
        filename_row.append(Gtk.Label(label="Base name"))
        filename_row.append(self.filename_entry)
        outer.append(filename_row)

        outer.append(Gtk.Label(label="Formats", xalign=0))
        self.format_checks: dict[str, Gtk.CheckButton] = {}
        formats = Gtk.Grid(column_spacing=12, row_spacing=8)
        available = (
            (("png", "PNG"), ("pdf", "PDF"))
            if self._space_mode
            else (("html", "HTML"), ("json", "JSON"), ("pdf", "PDF"), ("docx", "DOCX"), ("markdown", "Markdown"), ("csv", "CSV"), ("xlsx", "XLSX"), ("txt", "TXT"), ("zip", "ZIP package"))
        )
        for index, (key, label) in enumerate(available):
            check = Gtk.CheckButton(label=label)
            check.set_active(key in ({"png", "pdf"} if self._space_mode else {"html", "json", "pdf"}))
            formats.attach(check, index % 3, index // 3, 1, 1)
            self.format_checks[key] = check
        outer.append(formats)

        self.section_label = Gtk.Label(
            label=(
                f"Exporting menu: {initial_section}"
                if initial_section and initial_section != "Overview"
                else "Exporting complete report"
            ),
            xalign=0,
        )
        outer.append(self.section_label)

        self.complete_radio = Gtk.CheckButton(label="Complete Report")
        self.complete_radio.set_active(initial_section is None)
        custom = Gtk.CheckButton(label="Custom Report", group=self.complete_radio)
        if initial_section:
            custom.set_active(True)
        outer.append(self.complete_radio)
        outer.append(custom)

        self.include_graphs = Gtk.CheckButton(label="Include available graph assets")
        self.include_graphs.set_active(True)
        outer.append(self.include_graphs)
        self.overwrite = Gtk.CheckButton(label="Overwrite existing files")
        outer.append(self.overwrite)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        outer.append(self.progress)
        self.status = Gtk.Label(label="Ready")
        self.status.set_wrap(True)
        self.status.set_xalign(0)
        outer.append(self.status)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_row.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _button: self.window.close())
        export = Gtk.Button(label="Export")
        export.add_css_class("suggested-action")
        export.connect("clicked", self._on_export)
        action_row.append(cancel)
        action_row.append(export)
        outer.append(action_row)

    def present(self) -> None:
        self.window.present()

    def _browse_directory(self, _button: Gtk.Button) -> None:
        picker = getattr(self.parent, "file_picker", None)
        if picker is None:
            self.status.set_text("Folder browser is unavailable.")
            return
        initial_directory = Path(self.directory_entry.get_text()).expanduser()
        if not initial_directory.is_dir():
            initial_directory = self.project_root or Path.home()

        def on_directory_selected(directory: Path) -> None:
            GLib.idle_add(self._set_output_directory, directory)

        picker.show_open_folder(
            initial_directory=initial_directory,
            on_folder_opened=on_directory_selected,
        )

    def _set_output_directory(self, directory: Path) -> bool:
        self.directory_entry.set_text(str(directory))
        self.status.set_text("Output directory selected.")
        return GLib.SOURCE_REMOVE

    def _on_export(self, _button: Gtk.Button) -> None:
        directory = Path(self.directory_entry.get_text()).expanduser()
        selected = [key for key, check in self.format_checks.items() if check.get_active()] 
        if not selected:
            self.status.set_text("Select at least one export format.")
            return
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.status.set_text(f"Invalid output directory: {error}")
            return

        self.progress.pulse()
        self.status.set_text("Collecting analysis data...")
        if self._space_mode:
            selected = [key for key in selected if key in {"png", "pdf"}]
            if not selected:
                self.status.set_text("Space export supports PNG or PDF.")
                return

        context = AnalysisCollector().collect(self.analysis_panel, self.project_root)
        context.selected_section = None if self.complete_radio.get_active() else self.initial_section

        def worker() -> None:
            if self._space_mode:
                from ...space import SpaceExporter
                from ...export.export_manager import ExportResult

                placeholders = getattr(self.analysis_panel, "_section_placeholders", {})
                space = placeholders.get("Space")
                generated = []
                failures = []
                if space is None:
                    failures.append({"format": "space", "error": "Space board is unavailable."})
                else:
                    exporter = SpaceExporter()
                    base_name = self.filename_entry.get_text().strip() or "codevision-space"
                    for format_name in selected:
                        output_path = directory / f"{base_name}.{format_name}"
                        if output_path.exists() and not self.overwrite.get_active():
                            failures.append({"format": format_name, "error": f"Output already exists: {output_path}"})
                            continue
                        try:
                            if format_name == "png":
                                exported = exporter.export_png(space, output_path)
                            else:
                                exported = exporter.export_pdf(space, output_path)
                            from ...export.formats.base_exporter import ExportMetadata
                            generated.append(ExportMetadata(format_name.upper(), exported, exported.stat().st_size))
                        except (OSError, RuntimeError, ValueError, TypeError) as error:
                            failures.append({"format": format_name, "error": str(error)})
                result = ExportResult(
                    success=not failures,
                    output_directory=directory,
                    generated=generated,
                    failures=failures,
                )
                GLib.idle_add(self._finish, result)
                return

            result = ExportManager().export(
                context,
                directory,
                selected,
                output_name=self.filename_entry.get_text().strip() or "codevision-report",
                overwrite=self.overwrite.get_active(),
                progress=lambda stage: GLib.idle_add(self._progress_stage, stage),
            )
            GLib.idle_add(self._finish, result)

        threading.Thread(target=worker, daemon=True, name="codevision-export").start()

    def _progress_stage(self, stage: str) -> bool:
        self.status.set_text(f"Generating {stage}...")
        self.progress.pulse()
        return GLib.SOURCE_REMOVE

    def _finish(self, result: ExportResult) -> bool:
        if result.success:
            self.status.set_text("Export complete: " + ", ".join(str(path) for path in result.paths))
            self.progress.set_fraction(1.0)
        else:
            failures = "; ".join(f"{item['format']}: {item['error']}" for item in result.failures)
            generated = ", ".join(str(path) for path in result.paths)
            self.status.set_text(f"Partial export. Generated: {generated or 'none'}. Failed: {failures}")
            self.progress.set_fraction(0.0)
        return GLib.SOURCE_REMOVE
