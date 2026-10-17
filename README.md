# GenOffice for Arch Linux

Native Arch Linux and Omarchy packages for [GenOffice](https://github.com/genspark-ai/genoffice),
the unified AI-native office suite for Word (`.docx`), Excel (`.xlsx`),
PowerPoint (`.pptx`), PDF, Markdown, and HTML.

```sh
curl -fsSL https://github.com/zamkara/genoffice/releases/latest/download/install.sh | bash
```

The installer verifies the SHA-256 checksum of the release package and installs
or upgrades `genoffice` through `pacman`. Upstream `genspark-ai/genoffice` is
checked daily at 00:00 Asia/Jakarta (17:00 UTC); new upstream revisions are
built from source in a clean Arch Linux container and published automatically,
while unchanged revisions are skipped.

This is a community packaging repository, not an official GenOffice project.
Source code, issues, and development belong to [genspark-ai/genoffice](https://github.com/genspark-ai/genoffice).

---

## GenOffice upstream overview

GenOffice is a free, open-source alternative to Microsoft Office for macOS,
Windows, and Linux. It opens and saves native `.docx`, `.xlsx`, and `.pptx`
files, edits PDF, Markdown, and HTML, and puts an AI agent next to every
document — an editor that reads the file, makes the change, and shows you
exactly what it touched.

- **Real formats, byte-preserving.** Only what you edit is rewritten. Everything
  else in the file survives byte-for-byte, so documents keep working in Word,
  Excel, and PowerPoint.
- **AI you can review.** Edits land as tracked changes and diffs with one-click
  rollback. Spreadsheets get live formulas, not pasted numbers. Decks and pages
  are generated onto the canvas and stay fully editable.
- **Local by design.** Files open, edit, save, and convert on your machine.
  PDF → Word / Excel / PowerPoint, Markdown → Word, and HTML → Word all run
  on-device. Only the AI calls leave the machine, to the provider you choose.
- **Find files by what they say.** The home screen searches the names,
  folders, and full text of your `.docx`, `.xlsx`, `.pptx`, PDF, Markdown, and
  HTML files from a local SQLite index, CJK included.
- **Ask your files, with sources.** Star a set of documents and **Ask AI** on
  the home screen answers questions across them, citing the file behind every
  claim so you can open it and check.
- **Your keys or none.** Sign in with Genspark and skip keys, or bring your own
  key for Claude, OpenAI, Gemini, DeepSeek, Kimi, GLM, Qwen, Doubao, MiniMax,
  Grok, Mistral, OpenRouter, Requesty, Opper, Cheaper Inference, Atlas Cloud, or
  any OpenAI-compatible endpoint, local servers included.
- **Scriptable and agent-ready.** The package ships the `genoffice` command line
  (`/usr/bin/genoffice`) and agent skill for Claude Code, Codex, Cursor,
  Gemini CLI, GitHub Copilot, OpenCode, and Windsurf, so a coding agent can
  create, convert, read, and edit real Office files on your machine without
  opening a window.

## Included Modules

| Module       | Capabilities                                                                                  |
| ------------ | --------------------------------------------------------------------------------------------- |
| **Docs**     | Full-fidelity Word (`.docx`) editing with tracked changes, comments, styles, equations, export |
| **Sheets**   | Excel (`.xlsx`) workbooks with live formulas, charts, pivot tables, and a Rust `.xlsx` engine  |
| **Slides**   | PowerPoint (`.pptx`) decks with masters, layouts, smart guides, and presenter tools           |
| **PDF**      | PDF reading, markup, text editing, and local conversion to Word / Excel / PowerPoint          |
| **Markdown** | Markdown editor with live preview and document conversion                                     |
| **HTML**     | HTML editor with visual editing and Word conversion                                           |
| **CLI**      | Headless `genoffice` CLI and MCP bridge for document automation                               |

## Downloads

- **Arch Linux / Omarchy:** grab the latest build from the [Releases page of this repository](https://github.com/zamkara/genoffice/releases) or run the one-line installer above.
- **Other platforms (macOS, Windows, Debian/Ubuntu, Fedora/RHEL, AppImage):** grab official builds from [genspark-ai/genoffice releases](https://github.com/genspark-ai/genoffice/releases).

## Documentation

- [Upstream repository](https://github.com/genspark-ai/genoffice)
- [Contributing & architecture guide](https://github.com/genspark-ai/genoffice/blob/main/CONTRIBUTING.md)
- [Privacy policy](https://github.com/genspark-ai/genoffice/blob/main/PRIVACY.md)
- [Upstream license](https://github.com/genspark-ai/genoffice/blob/main/LICENSE)

## License

GenOffice itself remains under its [upstream Apache-2.0 license](https://github.com/genspark-ai/genoffice/blob/main/LICENSE).
The build setup in this repository is released under the [Almatera Incubator License](LICENSE).
