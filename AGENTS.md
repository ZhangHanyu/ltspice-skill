# AGENTS.md

This file provides development guidance for agents working on this repository.

## What This Is

An agent skill for automating LTspice circuit simulations. It runs LTspice through `scripts/run_ltspice.ps1`, validates the log, then converts the binary `.raw` output to CSV. There are three main artifacts: `scripts/run_ltspice.ps1` (the LTspice runner), `converter/ltspice_raw2csv.py` (the converter source), and `converter/ltspice_raw2csv.exe` (a locally-built Windows executable compiled with PyInstaller - not distributed in the repo; build it once with the commands below).

The canonical skill definition lives in `SKILL.md` - this is what agents read to know the full procedure, all supported parameters, defaults, and behavior guidelines. Read it first when modifying the skill's behavior.

`REFERENCE.md` is the circuit syntax reference - netlist conventions, all simulation directives, all element types, waveform syntax, `.MODEL`/`.SUBCKT`, and the `.asc` file format. Load it when reading or writing circuit files.

## Commands

**Run the converter (Python):**
```powershell
cd converter
pip install -r requirements.txt
python ltspice_raw2csv.py <file.raw> -o [output.csv] [--traces "V(out),I(R1)"] [--complex-mode ri|ma|python] [-q] [-f]
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

The runner handles `.asc` netlisting, waits for generated decks and RAW files to stabilize, checks for `Total elapsed time`, and returns nonzero on LTspice failures. Use `-ExpectedOutput fra` for `.FRA` simulations and `-ExpectedOutput none` only for workflows that intentionally do not produce RAW output.

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

The skill has two layers:

**Skill definition (`SKILL.md`)** - agent-facing spec. Defines inputs/outputs, the simulation procedures (standard and FRA), smart-behavior rules (prefer `.asc` over `.net`, auto-detect traces, check `.log` for fatal errors before converting), and security constraints (only LTspice and the converter may be executed).

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

When `traces` is omitted, all traces are exported.

## Key Constraints

- `.op.raw` (operating point) is a separate file from `.raw` (transient/AC/DC sweep). Use `--op` to export both in a single converter call; they always produce separate CSVs.
- Trace names are case-sensitive and must match exactly what LTspice writes (e.g., `V(vout)` not `v(vout)`). The `-d` flag reveals exact names.
- The converter raises an error if no valid traces remain after filtering; it warns (not errors) for individual missing trace names.
