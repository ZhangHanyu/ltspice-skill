# AGENTS.md

This file provides development guidance for agents working on this repository.

## What This Is

An agent skill for automating LTspice circuit simulations. It runs LTspice through `scripts/run_ltspice.ps1`, validates the log, then converts the binary `.raw` output to CSV. There are three main artifacts: `scripts/run_ltspice.ps1` (the LTspice runner), `converter/ltspice_raw2csv.py` (the converter source), and `converter/ltspice_raw2csv.exe` (a locally-built Windows executable compiled with PyInstaller - not distributed in the repo; build it once with the commands below).

The canonical skill definition lives in `SKILL.md` - this is what agents read to know the full procedure, all supported parameters, defaults, and behavior guidelines. Read it first when modifying the skill's behavior.

`REFERENCE.md` is the circuit syntax reference - netlist conventions, all simulation directives, all element types, waveform syntax, `.MODEL`/`.SUBCKT`, and the `.asc` file format. Load it when reading or writing circuit files.

## LTspice Schematic Encoding

`.asc` schematic files are Windows-1252 files. Read and write them as Windows-1252 only; never use UTF-8 for `.asc`, even when the rendered text looks correct. LTspice symbols such as `µ` must remain single-byte Windows-1252 (`0xB5`). A UTF-8 rewrite produces bytes such as `C2 B5`, which LTspice reads as `Âµ` and can silently corrupt component values during netlisting.

`.net` and `.cir` files are separate from this rule. LTspice-generated `.net` files may be UTF-8, and LTspice accepts both UTF-8 and Windows-1252 for `.net` files.

Use this pattern for `.asc` edits in PowerShell/.NET:

```powershell
$encoding = [System.Text.Encoding]::GetEncoding(1252)
$text = $encoding.GetString([System.IO.File]::ReadAllBytes($ascPath))
# edit $text here
[System.IO.File]::WriteAllBytes($ascPath, $encoding.GetBytes($text))
```

`scripts/run_ltspice.ps1` checks `.asc` bytes before netlisting and fails fast on UTF-8 BOM or common UTF-8-encoded LTspice symbols. It does not auto-convert schematics.

## Commands

**Run the converter (Python):**
```powershell
cd converter
pip install -r requirements.txt
python ltspice_raw2csv.py <file.raw> -o [output.csv] [-t "V(out),I(R1)"] [-c ri|ma|python] [-p N] [-q] [-f]
```

**Preview traces in a `.raw` file:**
```powershell
python ltspice_raw2csv.py <file.raw> -d      # metadata + variable list
python ltspice_raw2csv.py <file.raw> -s      # metadata only
```

**Run LTspice simulation (preferred runner):**
```powershell
.\scripts\run_ltspice.ps1 -LtspicePath "<path_to_LTspice.exe>" -InputFile "<file.asc|file.net|file.cir>" -ExpectedOutput standard -TimeoutSeconds 3600
```

The runner handles `.asc` netlisting, waits for the log completion marker (`Total elapsed time`) and file-lock release on the RAW output, and returns nonzero on LTspice failures. Use `-ExpectedOutput fra` for `.FRA` simulations and `-ExpectedOutput none` only for workflows that intentionally do not produce RAW output.

**Rebuild the executable** (run once to create the venv, then use it for all subsequent builds):
```powershell
cd converter

# First time only
python -m venv .venv
.\.venv\Scripts\pip install pyinstaller pyltspice numpy

# Build (excludes matplotlib/scipy/PIL which are PyLTSpice optional deps, not needed here)
.\.venv\Scripts\pyinstaller --onefile `
  --exclude-module matplotlib `
  --exclude-module scipy `
  --exclude-module PIL `
  --exclude-module tkinter `
  --exclude-module _tkinter `
  --exclude-module contourpy `
  --exclude-module cycler `
  --exclude-module fonttools `
  --exclude-module kiwisolver `
  --exclude-module pillow `
  --distpath dist --workpath build `
  ltspice_raw2csv.py

Copy-Item dist\ltspice_raw2csv.exe ltspice_raw2csv.exe -Force
```

**Test with the included example:**
```powershell
.\converter\ltspice_raw2csv.exe .\examples\TRAN_analysis\output\RC_filter.raw -d
.\converter\ltspice_raw2csv.exe .\examples\TRAN_analysis\output\RC_filter.raw -o .\examples\TRAN_analysis\output\RC_filter_test.csv -f -q
```

## Architecture

The skill has three layers:

**Skill definition (`SKILL.md`)** - agent-facing spec. Defines inputs/outputs, the simulation procedures (standard and FRA), smart-behavior rules (read `.net` to understand circuits, edit `.asc` as Windows-1252 to modify them, auto-detect traces, check `.log` for fatal errors before converting), and security constraints (only the runner, LTspice, and the converter may be executed).

**Runner (`scripts/run_ltspice.ps1`)** - PowerShell script that wraps LTspice execution. Handles two-phase `.asc` → `.net` → `.raw` flow, rejects UTF-8-corrupted `.asc` files before netlisting, waits for the log completion marker (`Total elapsed time`) and confirms RAW write completion via file-lock release, scans for fatal log patterns, and returns nonzero on any failure. Use `-ExpectedOutput fra` for FRA simulations.

**Converter (`converter/ltspice_raw2csv.py`)** - reads LTspice binary `.raw` files via PyLTSpice, applies optional trace filtering, handles complex data in three modes (`ri` = real/imag columns, `ma` = magnitude/angle columns, `python` = Python complex literals), and writes CSV. Key functions: `raw_to_csv()` (main logic), `_process_trace()` (complex handling), `preview_short/detailed()` (inspection modes).

The `.exe` is a frozen copy of the Python script; keep it in sync with the source when making changes.

## Parameter Defaults (Skill Layer)

| Parameter | Default |
|-----------|---------|
| `output_csv` | `{input_name}.csv` (same directory as `.raw`) |
| `quiet` | `true` (pass `-q`) |
| `overwrite` | `true` (pass `-f`) |
| `export_op` | `false` |
| `complex_mode` | `ri` |
| `step` | all steps (omit `--step`; prefix columns added for stepped files) |
| `precision` | `6` sig figs for waveform values (pass `-p 0` for full precision); `time`/`frequency` always full precision |

When `traces` is omitted, all traces are exported.

## Key Constraints

- `.op.raw` (operating point) is a separate file from `.raw` (transient/AC/DC sweep). Use `--op` to export both in a single converter call; they always produce separate CSVs.
- Trace names are case-sensitive and must match exactly what LTspice writes (e.g., `V(vout)` not `v(vout)`). The `-d` flag reveals exact names.
- The converter raises an error if no valid traces remain after filtering; it warns (not errors) for individual missing trace names.

## Testing

No automated test suite. Validate changes against the examples in `examples/` — each subdirectory has a runnable circuit and documented expected results (see `examples/README.md`). For changes to `scripts/run_ltspice.ps1`, also test with a temporary long-running circuit under `tmp/` to exercise the file-write detection window.

`tmp/` is gitignored and serves as a scratch area for temporary test circuits, change notes, and other ephemeral files that should not be committed.

## Licensing

The converter (`converter/`) is GPL-3.0 because it depends on PyLTSpice (GPL-3.0). Everything else (`SKILL.md`, `REFERENCE.md`, `AGENTS.md`, `scripts/`, `examples/`) is MIT. Do not move converter code into the MIT-licensed portion.
