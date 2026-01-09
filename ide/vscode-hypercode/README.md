# HyperCode VS Code Extension

Official language support for **HyperCode** - The Neurodivergent-First Quantum Language.

## Features

*   **Syntax Highlighting**: Beautiful coloring for `@function`, `@circuit`, `QReg`, and quantum gates.
*   **Snippets**: (Coming Soon) Fast scaffolding for circuits.
*   **LSP Integration**: (Coming Soon) Real-time error checking powered by `syntax_validator.py`.

## Quick Start (Development)

1.  Open this folder (`ide/vscode-hypercode`) in VS Code.
2.  Press `F5` to launch a new Extension Development Host window.
3.  Open any `.hc` file (check `../../examples/` for samples).
4.  Enjoy the syntax highlighting!

## Installation (Manual)

1.  Install `vsce`: `npm install -g vsce`
2.  Package the extension: `vsce package`
3.  Install the `.vsix` file in VS Code.
