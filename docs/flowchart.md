# Flowchart Analysis

CodeVision builds flowcharts from the existing Tree-sitter AST. The graph
models, builder, layout, validation, and exporters are independent of GTK; the
GTK view presents the active source file's function graphs in the Analysis
panel.

## Pipeline

`source -> SourceParser -> ASTResult -> FlowchartBuilder -> FlowchartGraph -> GraphLayout -> validation -> GTK/Cairo renderer`

`FlowchartBuilder.build()` selects `main` when present, otherwise the first
recognized function. `build_all()` returns an individual graph for every
recognized function. The Analysis panel exposes those graphs in its function
selector.

## Implemented

- Sequential declarations and expression statements.
- `if` / `else` and chained `elif` / `else if` branches with labeled edges and
  merge nodes.
- `for` and `while` loops, loop-back edges, and nearest-loop `break` and
  `continue` destinations.
- Returns and throws terminate their reachable path; statements after an
  unconditional return are omitted.
- Common input/output calls are classified as input/output nodes; other calls
  are represented as function nodes.
- C, C++, Python, Java, JavaScript, and TypeScript parser node families are
  recognized where they match the implemented statement forms. Automated
  language-specific coverage currently exercises C and Python.
- The view supports selecting functions, refreshing, selecting nodes to
  navigate to source, zooming, fitting, drag-panning, and exporting SVG, PNG,
  and PDF.
- Validation rejects malformed node/edge references and duplicate identifiers;
  unreachable nodes are reported as warnings.

## Limitations

- `try` / `catch` / `finally`, switch-style branching, do-while loops, and
  language-specific constructs without an explicit adapter are not modeled as
  executable control flow. Unknown AST statements are labeled unsupported.
- Function calls link to their source location but do not open a callee graph
  automatically.
- Parsing and graph generation currently run synchronously in the flowchart
  view; source updates are debounced by the main window, but very large files
  can still delay the GTK thread.
- The deterministic layout is intentionally simple and can overlap or route
  awkwardly for deeply nested or highly connected graphs.
- Node colors are currently fixed in the Cairo renderer; the stylesheet is
  loaded for the canvas surface, but complete theme-driven graph colors remain
  future work.

Run the focused tests with `.venv/bin/python -m pytest -q tests/test_flowchart_builder.py tests/test_flowchart_view.py tests/test_graph_export.py`.
