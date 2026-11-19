# Export System

CodeVision exports the complete currently available analysis state through a GTK-independent pipeline:

```text
Analysis modules / cached views
  -> AnalysisCollector
  -> ExportContext
  -> ReportBuilder
  -> ReportModel
  -> ExportManager
  -> format exporters
  -> ZIP package and manifest
```

## Formats

- HTML: complete standalone report with table of contents, collapsible sections, tables, and source blocks.
- JSON: complete structured report, schema version, metadata, and no arbitrary record limit.
- PDF: ReportLab multi-page layout with repeating table headers and automatic page flow.
- DOCX: editable Word document with heading hierarchy, tables, repeated table headers, margins, and footer/header text.
- Markdown: GitHub-compatible complete report.
- CSV: tabular analysis records in normalized section/table/record/column/value rows.
- XLSX: workbook with overview and one worksheet per report section.
- TXT: complete plain-text report.
- ZIP: selected report files, graph assets, and `metadata.json` manifest.

## Completeness

The report builder distinguishes `performed`, `no-findings`, `not-performed`, `unavailable`, and `failed` section states. JSON serialization uses an explicit dataclass/enum/Path adapter and records unsupported structured value types rather than silently replacing them.

The export manager never reports success when a selected format fails. `ExportResult.generated`, `ExportResult.failures`, and `ExportResult.manifest` expose partial state explicitly.

## Optional Dependencies

PDF uses ReportLab. DOCX uses `python-docx`. XLSX uses `openpyxl`. Missing dependencies produce format-specific failures in the export result instead of aborting the other formats.
