from __future__ import annotations

import json
import zipfile
from pathlib import Path

from ..report_builder import ReportModel
from ..report_manifest import ReportManifest
from .base_exporter import BaseExporter, ExportMetadata


class ZIPExporter(BaseExporter):
    format_name = "zip"
    extension = ".zip"

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None, files: dict[str, Path] | None = None, manifest: ReportManifest | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for arcname, file_path in (files or {}).items():
                source = Path(file_path)
                if source.is_file():
                    archive.write(source, arcname)
            if assets_dir is not None:
                assets_root = Path(assets_dir)
                if assets_root.is_dir():
                    for asset in sorted(assets_root.rglob("*")):
                        if asset.is_file():
                            archive.write(asset, f"graphs/{asset.relative_to(assets_root).as_posix()}")
            archive.writestr("metadata.json", json.dumps((manifest.to_dict() if manifest else {}), ensure_ascii=False, indent=2))
        return ExportMetadata("ZIP", path, path.stat().st_size, [section.section_id for section in report.sections], warnings=[])
