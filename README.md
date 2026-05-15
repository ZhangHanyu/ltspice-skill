# ltspice-skill

An agent skill/toolkit for LTspice circuit automation. Agents that can read a `SKILL.md` workflow can use this repository to read and edit schematics (`.asc`) and netlists (`.net`/`.cir`), run LTspice simulations in batch mode, and convert binary waveform output to CSV from a natural-language prompt.

The first documented agent targets are Claude Code and Codex, but the core workflow is intentionally agent-neutral.

## What it does

- **Understand and modify circuits** - reads and edits component values, simulation directives, and topology in `.asc` schematics and `.net`/`.cir` netlists
- **Run simulations** - launches LTspice in batch mode for TRAN, AC, DC, `.OP`, `.STEP` sweeps, and FRA analyses
- **Convert output to CSV** - exports `.raw`, `.op.raw`, and `.fra_*.raw` waveform files using the included converter; supports `.STEP` multi-step export and three complex-number formats

## Requirements

- [LTspice](https://www.analog.com/en/resources/design-tools-and-calculators/ltspice-simulator.html) installed on Windows
- An agent environment that can read `SKILL.md` instructions, such as [Claude Code](https://claude.ai/code) or Codex
- Python 3.10+ (to build the converter executable once)

## Setup

**1. Clone the repo**

```powershell
git clone <repo-url> ltspice-skill
```

**2. Build the converter executable** (one-time, ~30-60 s)

```powershell
cd ltspice-skill\converter
python -m venv .venv
.\.venv\Scripts\pip install pyinstaller pyltspice numpy
.\.venv\Scripts\pyinstaller --onefile `
  --exclude-module matplotlib --exclude-module scipy --exclude-module PIL `
  --exclude-module tkinter --exclude-module _tkinter `
  --exclude-module contourpy --exclude-module cycler `
  --exclude-module fonttools --exclude-module kiwisolver --exclude-module pillow `
  --distpath dist --workpath build ltspice_raw2csv.py
Copy-Item dist\ltspice_raw2csv.exe ltspice_raw2csv.exe -Force
```

This produces `converter/ltspice_raw2csv.exe` (~20 MB, self-contained).

## Use with agents

The canonical workflow is `SKILL.md`. `REFERENCE.md` provides the LTspice syntax reference, and `converter/` provides the RAW-to-CSV tool used by the workflow.

### Claude Code

Open the repo in Claude Code:

```powershell
cd ltspice-skill
claude
```

Claude Code automatically loads `CLAUDE.md`, which points to the agent-neutral development guide in `AGENTS.md` and the canonical skill workflow in `SKILL.md`.

### Codex

Install the repo as a Codex skill by copying or symlinking this folder into Codex's skills directory:

```powershell
Copy-Item -Recurse . "$env:USERPROFILE\.codex\skills\ltspice-skill"
```

Alternatively, create a directory junction so updates to this working copy are seen by Codex:

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\ltspice-skill" `
  -Target (Get-Location)
```

The root `SKILL.md` already follows the Codex skill shape, so no Codex-specific package is needed.

## Usage

Give the agent a natural-language instruction. Examples:

```
Simulate examples/TRAN_analysis/RC_filter.asc and export V(vout) to CSV.

Change R1 in my_circuit.asc to 4.7k and re-run the transient simulation.

Run a .STEP sweep over L1 from 1uH to 10uH in 3k steps and export all steps.

Convert the FRA output to a Bode-plot CSV.
```

The agent uses `SKILL.md` as its procedure guide and `REFERENCE.md` for circuit syntax.

## Repository structure

| Path | Description |
|------|-------------|
| `SKILL.md` | Canonical skill definition: procedure, inputs, defaults, and agent guidelines |
| `REFERENCE.md` | LTspice circuit syntax reference (netlists, directives, `.asc` format) |
| `AGENTS.md` | Agent-neutral development guide for maintainers and coding agents |
| `CLAUDE.md` | Claude Code compatibility pointer to `AGENTS.md` and `SKILL.md` |
| `converter/` | `ltspice_raw2csv.py` source + `README.md` + build instructions |
| `examples/` | Five worked examples: TRAN, AC, DC, `.STEP`, FRA |

## Examples

See [`examples/README.md`](examples/README.md) for runnable commands for each simulation type.

## License

This repository uses a dual license:

- **Skill definition, reference docs, development guide, and examples** (`SKILL.md`, `REFERENCE.md`, `AGENTS.md`, `CLAUDE.md`, `examples/`) - [MIT](LICENSE)
- **Converter** (`converter/`) - [GPL-3.0](converter/LICENSE)

The converter is GPL-3.0 because it depends on [PyLTSpice](https://github.com/nunobrum/PyLTSpice) (GPL-3.0). The executable is not distributed; each user builds it locally from source.
