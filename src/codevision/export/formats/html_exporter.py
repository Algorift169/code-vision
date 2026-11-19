from __future__ import annotations

import html
from pathlib import Path

from ..report_builder import ReportModel
from ..report_section import ReportSection
from .base_exporter import BaseExporter, ExportMetadata


class HTMLExporter(BaseExporter):
    format_name = "html"
    extension = ".html"

    @staticmethod
    def _table(table: dict) -> str:
        columns = table.get("columns", [])
        rows = table.get("rows", [])
        title = html.escape(str(table.get("title", "Table")))
        head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
        body = "".join("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
        return f'<section class="table-wrap"><h3>{title}</h3><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></section>'

    def _section(self, section: ReportSection) -> str:
        body = []
        if section.description:
            body.append(f'<p class="description">{html.escape(section.description)}</p>')
        body.extend(self._table(table) for table in section.tables)
        for block in section.code_blocks:
            code = block.get("code") or ""
            body.append(f'<details open><summary>{html.escape(str(block.get("title", "Source")))}</summary><pre><code>{html.escape(str(code))}</code></pre></details>')
        if section.graph_references:
            body.append("<h3>Graph References</h3><ul>" + "".join(
                f'<li><strong>{html.escape(str(graph.get("title", "Graph")))}</strong>: {html.escape(str(graph.get("asset") or "Not exported as an asset"))}</li>'
                for graph in section.graph_references
            ) + "</ul>")
        if not section.tables and not section.code_blocks and not section.graph_references:
            body.append('<pre class="structured">' + html.escape(str(section.content)) + "</pre>")
        return f'<section id="{html.escape(section.section_id)}" class="report-section"><details open><summary><h2>{html.escape(section.title)}</h2><span class="status {html.escape(section.status)}">{html.escape(section.status)}</span></summary>{"".join(body)}</details></section>'

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        meta = report.metadata
        toc = "".join(f'<li><a href="#cover"></a></li>')
        toc += "".join(f'<li><a href="#{html.escape(section.section_id)}">{html.escape(section.title)}</a></li>' for section in report.sections)
        sections = "".join(self._section(section) for section in report.sections)
        document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(meta.title)}</title><style>
:root{{color-scheme:light dark;--bg:#0d1117;--panel:#161b22;--text:#e6edf3;--muted:#8b949e;--border:#30363d}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 system-ui,sans-serif}} .layout{{display:grid;grid-template-columns:260px minmax(0,1fr);min-height:100vh}} nav{{position:sticky;top:0;height:100vh;overflow:auto;border-right:1px solid var(--border);padding:24px;background:var(--panel)}} main{{min-width:0;padding:32px 48px 80px}} nav a{{color:inherit;text-decoration:none}} nav li{{margin:7px 0}} #cover{{border-bottom:1px solid var(--border);padding-bottom:32px;margin-bottom:32px}} .report-section{{margin:20px 0;border:1px solid var(--border);border-radius:8px;background:var(--panel)}} summary{{cursor:pointer;padding:14px 18px}} summary h2{{display:inline-block;margin:0}} .status{{float:right;color:var(--muted);text-transform:uppercase;font-size:11px}} table{{width:100%;border-collapse:collapse}} th,td{{border:1px solid var(--border);padding:8px;text-align:left;vertical-align:top}} th{{position:sticky;top:0;background:var(--bg)}} pre{{overflow:auto;padding:16px;border:1px solid var(--border);background:var(--bg);white-space:pre-wrap;overflow-wrap:anywhere}} .description{{color:var(--muted)}} @media(max-width:800px){{.layout{{grid-template-columns:1fr}}nav{{position:relative;height:auto}}main{{padding:24px 16px}}}} @media print{{nav{{display:none}}.layout{{display:block}}body{{background:white;color:black}}.report-section{{break-inside:auto;background:white}}pre{{white-space:pre-wrap}}}}
</style></head><body><div class="layout"><nav><strong>CodeVision Report</strong><ol>{toc}</ol></nav><main>
<section id="cover"><h1>{html.escape(meta.title)}</h1><p><strong>Project:</strong> {html.escape(meta.project_name)}</p><p><strong>Root:</strong> {html.escape(meta.project_root or "Not specified")}</p><p><strong>Language:</strong> {html.escape(meta.primary_language or "Unknown")}</p><p><strong>Generated:</strong> {html.escape(meta.generated_at)}</p><p><strong>Analysis status:</strong> {html.escape(meta.analysis_status)}</p></section>{sections}
</main></div></body></html>'''
        path.write_text(document, encoding="utf-8")
        return ExportMetadata("HTML", path, path.stat().st_size, [section.section_id for section in report.sections])
