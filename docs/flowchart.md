# Flowchart Engine

This project now includes an initial flowchart engine architecture built on the
existing AST and parser stack.

## Status

- AST-based graph construction is available through `FlowchartBuilder`.
- Flowchart IR models and validation are implemented.
- A GTK placeholder view is mounted in the analysis panel.
- The implementation is intentionally minimal and compatible with the current
  project architecture.

## Pipeline

source -> parser -> AST -> FlowchartBuilder -> FlowchartGraph -> validation -> render
