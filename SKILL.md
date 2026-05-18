---
name: ltspice-skill
description: Understand, modify, and simulate LTspice circuits. Reads and edits schematics (`.asc`) and netlists (`.net`/`.cir`) — components, values, simulation directives, and topology — then runs LTspice in batch mode and converts waveform output (`.raw`, `.op.raw`, `.fra_*.raw`) to CSV using `ltspice_raw2csv.exe`. Supports TRAN, AC, DC, .OP, .STEP sweeps, and FRA simulations.
---

# LTspice Simulation, Circuit Modification, and Data Export

---

## Circuit Syntax Reference

When reading, writing, or modifying `.asc` schematics or `.net`/`.cir` netlists, consult `REFERENCE.md` in this directory. It covers netlist conventions, all simulation directives (including `.FRA`), all circuit element types, waveform syntax, `.MODEL`/`.SUBCKT`, and the `.asc` file format.

---

## LTspice Installation

### LTspice Executable

If the user does not specify the path to `LTspice.exe`, check the default install location:
`C:\Users\{user_name}\AppData\Local\Programs\ADI\LTspice\LTspice.exe`

### LTspice Official Help Documents

Located at `{install_dir}\LTspiceHelp\`. Each `.htm` file covers one topic. Consult these for details not covered in `REFERENCE.md`.

---

## Supported Input Types

* `.asc` → LTspice schematic (GUI-generated)
* `.net` / `.cir` → LTspice/SPICE netlist

**Reading/understanding a circuit:** Prefer `.net` — pure SPICE syntax (element, nodes, value per line) with no coordinate or layout noise, and it is exactly what LTspice simulates. If only `.asc` exists, generate `.net` first:

```powershell
"<ltspice_path>" -netlist "<file.asc>"
```

**Editing/modifying a circuit:** Always edit `.asc` — it is the source of truth. LTspice overwrites `.net` when re-netlisting from `.asc`, so edits to `.net` are lost on the next schematic open or simulation run.

---

## Schematic Encoding Rule

LTspice `.asc` schematic files must be read and written as Windows-1252 only. Do not use UTF-8 for `.asc`, even if the text appears correct in an editor. LTspice symbols such as `µ` must remain single-byte Windows-1252 (`0xB5`); UTF-8 bytes such as `C2 B5` are interpreted as `Âµ` and can silently corrupt values during netlisting.

`.net` and `.cir` files are separate from this rule. LTspice-created `.net` files may be UTF-8, and LTspice accepts both UTF-8 and Windows-1252 for `.net` files.

When editing `.asc` with PowerShell/.NET, use Windows-1252 for both read and write:

```powershell
$encoding = [System.Text.Encoding]::GetEncoding(1252)
$text = $encoding.GetString([System.IO.File]::ReadAllBytes($ascPath))
# edit $text here
[System.IO.File]::WriteAllBytes($ascPath, $encoding.GetBytes($text))
```

The runner checks `.asc` bytes before netlisting and fails fast if it detects UTF-8 BOM or common UTF-8-encoded LTspice symbols. It does not auto-convert schematics; fix the source file intentionally.

---

## Environment Assumptions

* OS: Windows
* LTspice executable available via full path
* `ltspice_raw2csv.exe` available (built on first run if absent — see Converter Setup below)
* File system access permitted

---

## LTspice Launch Smoke Test

When using a new LTspice executable, a new agent sandbox, or a launch mode that has not worked in the current session, run this quick `.cir` deck before long simulations:

```spice
* LTspice launch smoke test
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.tran 1m
.end
```

Run it with:

```powershell
"<ltspice_path>" -b ltspice_smoke_test.cir
```

Proceed only if LTspice creates `.log` and `.raw` files. Do not use `-sync` for this; current LTspice help documents `-sync` as component-library update.

---

## Converter Setup (First Run)

`ltspice_raw2csv.exe` is not distributed in the repository; it must be built locally once.

**Check:** Before any conversion step, verify `converter_path` exists:

```powershell
Test-Path "<converter_path>"
```

**Build if missing:** Run the following from the `converter/` directory. Full commands are in `AGENTS.md`.

```powershell
cd <skill_root>\converter
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

This takes ~30–60 seconds and produces a ~20 MB self-contained executable.

---

## Inputs

* **input_file** (required)
  Path to `.asc` or `.net`/`.cir` file to simulate

* **ltspice_path** (required)
  Full path to `LTspice.exe` (e.g., `C:\Users\...\ADI\LTspice\LTspice.exe`)

* **converter_path** (required)
  Full path to `ltspice_raw2csv.exe`

* **output_csv** (optional, default: `{input_name}.csv`)
  Output CSV path for main waveform data

* **traces** (optional, default: all)
  Comma-separated list of trace names to export (e.g., `"time,V(out),I(L1)"`)

* **complex_mode** (optional, default: `ri`)
  Format for complex data: `ri` (real/imag columns) | `ma` (magnitude/angle) | `python`

* **overwrite** (optional, default: true)
  Pass `-f` to skip overwrite confirmation

* **quiet** (optional, default: true)
  Pass `-q` to suppress conversion summary output

* **step** (optional, default: all steps)
  Pass `--step N` (1-indexed) to export only step N of a `.STEP` sweep. Omit to export all steps with `step` and parameter prefix columns. No effect on non-stepped files.

* **export_op** (optional, default: false)
  Pass `--op` to also convert `.op.raw` to CSV in the same converter invocation. The op CSV is always written to `{csv_stem}.op.csv` (not configurable separately).

* **precision** (optional, default: `6`)
  Pass `-p N` to set the number of significant figures for waveform values. Use `-p 0` for full float precision. `time` and `frequency` axes are always written at full precision regardless of this setting.

---

## Outputs

After simulation:

* `{name}.raw` — transient / AC / DC sweep waveform data
* `{name}.op.raw` — operating point data (if `.op` analysis present)
* `{name}.log` — simulation log
* `{name}.fra_<instance>.raw` — FRA frequency response data (if `.fra` analysis present)

After conversion:

* `{name}.csv`
* `{name}.op.csv` (if `export_op` requested)
* `{name}.fra_<n>.csv` (FRA — one per `@` device instance converted)

---

## Procedure — Standard Simulation (TRAN / AC / DC)

### Step 1 — Run LTspice with the Runner

Use the bundled runner script as the preferred execution interface:

```powershell
.\scripts\run_ltspice.ps1 `
  -LtspicePath "<ltspice_path>" `
  -InputFile "<input_file>" `
  -ExpectedOutput standard `
  -TimeoutSeconds 3600
```

The runner handles `.asc` netlist generation, waits for generated `.net` files to be fully written, invokes LTspice with the documented `-b` deck form, waits for `Total elapsed time` in the log, confirms RAW write completion via file-lock release, checks fatal log patterns, and returns nonzero on failure.

Use raw LTspice commands only when `scripts/run_ltspice.ps1` is unavailable or when debugging the runner itself. Direct schematic simulation with `-Run <schematic.asc>` is acceptable only when netlist generation is not suitable or the user explicitly requests it.

---

### Step 2 — Determine Output Files

LTspice writes outputs to the same directory as the simulated deck, using the same base name. If an `.asc` file was netlisted first, use the generated `.net` base name:

```
C:\sim\buck.net  →  C:\sim\buck.raw
                     C:\sim\buck.op.raw  (if .op analysis present)
                     C:\sim\buck.log
```

---

### Step 3 — Wait for Simulation Completion

The runner does this for normal use. Do not treat shell/process return alone as completion: LTspice batch mode can return control while background work is still writing `.raw`, `.log`, or generated `.net` files. Completion is valid only after the log contains `Total elapsed time` and expected output files are stable.

---

### Step 4 — Validate Simulation Success

Check that `.raw` exists and the `.log` contains `Total elapsed time`. Then read `.log` and scan for any of these failure indicators:

* `Error:`
* `Analysis failed`
* `.TRAN failed`
* `No operating point found`
* `Singular matrix`
* `Time step too small`

If the runner exits nonzero, report its error and relevant log lines to the user. If running LTspice manually, treat missing `.raw`, missing `Total elapsed time`, or any fatal log pattern as failed or incomplete simulation.

---

### Step 5 — Convert to CSV

Build the converter command:

```
<converter_path> <name>.raw -o <output_csv> [--op] [--step N] [-t "time,V(out),I(L1)"] [-c ri|ma|python] [-p N] [-q] [-f]
```

* `--op` — also exports `{name}.op.raw` to `{name}.op.csv` in the same call (use instead of a separate invocation)
* `--step N` — export only step N of a `.STEP` sweep (1-indexed); omit to export all steps with prefix columns
* Apply `-q` and `-f` unless explicitly disabled by the user

---

## Procedure — FRA Simulation (.FRA)

FRA (Frequency Response Analysis) uses a different output structure. The `.fra` directive is controlled by `@` device instances in the circuit. See `REFERENCE.md §2 .FRA` and `§3 @ / &` for syntax.

### Step 1 — Run LTspice with the Runner

Use the same runner script with FRA output mode:

```powershell
.\scripts\run_ltspice.ps1 `
  -LtspicePath "<ltspice_path>" `
  -InputFile "<input_file>" `
  -ExpectedOutput fra `
  -TimeoutSeconds 7200
```

### Step 2 — Determine FRA Output Files

```
C:\sim\buck.asc  →  C:\sim\buck.fra_1.raw   (one per @ device instance)
                     C:\sim\buck.log
```

Note: FRA does NOT produce `buck.raw`. Check for `buck.fra_<n>.raw` instead.

### Step 3 — Wait for Completion

Same as standard simulation: let the runner wait for the `.log` completion marker (`Total elapsed time`) and stable FRA `.raw` output before converting. FRA simulations can take significantly longer than transient simulations — this is expected.

### Step 4 — Validate

Check `.log` for the same failure indicators as standard simulation.

### Step 5 — Convert FRA Output

```
<converter_path> <name>.fra_1.raw -o <output_csv> -c ma [-q] [-f]
```

FRA output is complex (magnitude/phase). Use `--complex-mode ma` for Bode-plot-ready columns.

---

## Circuit Modification Workflow

When asked to modify a circuit before simulating:

1. **Read `REFERENCE.md`** for the relevant syntax (directive, component, or `.asc` format).
2. **Understand the circuit** by reading the `.net` file — pure SPICE syntax is easier to parse than `.asc`. If only `.asc` exists, generate `.net` first (`"<ltspice_path>" -netlist "<file.asc>"`).
3. **Edit `.asc`**, never `.net` — LTspice overwrites `.net` when re-netlisting from `.asc`. Follow the `.asc` file format rules in `REFERENCE.md §6`. Key points:
   - Coordinates must be on the 16-unit grid
   - `SYMATTR Value` sets component values; `SYMATTR InstName` sets instance names
   - Simulation directives live in `TEXT` records: `TEXT <x> <y> Left 2 !<directive>`
   - Read and write the `.asc` as Windows-1252 only; never save it as UTF-8
4. **Re-run the simulation** after any modification using the standard or FRA procedure above.
5. **Verify** by checking the `.log` for errors and inspecting the output CSV.

---

## LTspice Command Notes

| Flag | Effect |
|------|--------|
| `-b` | Run a `.net` / `.cir` deck in batch mode |
| `-Run` | Start simulating a schematic opened on the command line |
| `-netlist` | Export `.asc` to `.net` only, no simulation |
| `-sync` | Update component libraries; do not use as a wait/synchronization flag |

Do NOT use `-ascii` (severe performance degradation), `-sync` as a wait flag, or GUI flags (`-big`, `-max`).

When invoking LTspice from PowerShell, prefer literal absolute path strings. If using `Resolve-Path`, pass its `.Path` string rather than the raw PathInfo object:

```powershell
$deck = (Resolve-Path -LiteralPath ".\circuit.net").Path
& "<ltspice_path>" -b $deck
```

---

## File Behavior Rules

* All output files are written to the same directory as the simulated deck
* Output base name matches the deck base name
* Example: `buck.net` → `buck.raw`, `buck.op.raw`, `buck.log`

---

## Smart Behavior (Agent Guidelines)

* Use `scripts/run_ltspice.ps1` for LTspice execution by default
* To **read** a circuit: prefer `.net` (generate with `-netlist` if only `.asc` exists)
* To **edit** a circuit: always use `.asc`, preserving Windows-1252 encoding
* Let the runner generate `.net` files from `.asc` and simulate decks with `-b`
* Auto-derive all output filenames from the simulated deck path
* If LTspice launch behavior is unproven in the current environment, run a trivial smoke-test deck through the runner before long simulations
* Before converting, require successful runner completion; it checks `Total elapsed time` and output stability
* If traces not specified: run `ltspice_raw2csv.exe <file>.raw -d` first and suggest available traces
* Use `-q` and `-f` by default unless the user explicitly asks otherwise
* Use `--op` flag (single converter call) instead of two separate calls when exporting operating point
* For FRA: use `--complex-mode ma` by default (Bode-plot-ready output)

---

## Error Handling

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| `.raw` not created | Simulation failure or bad netlist | Read `.log`, show relevant error lines to user |
| Runner exits nonzero | Simulation, launch, timeout, or log failure | Report runner error and relevant log lines |
| `.raw` exists but `.log` lacks `Total elapsed time` | Simulation still running or incomplete | Do not convert; use runner or wait for completion marker |
| No `.log` or `.raw` after timeout | LTspice launch/sandbox failure | Report launch failure; retry direct visible/elevated launch or runner smoke test before blaming the circuit |
| `.op.raw` not created | No `.op` analysis in netlist | Not an error; skip silently |
| `.fra_*.raw` not created | FRA simulation failed or no `@` device | Check `.log`; confirm `@` device exists in schematic |
| Converter: "No valid traces" | Trace name mismatch (case-sensitive) | Run `-d` to list exact names, retry |
| Converter: corrupt file error | Simulation was interrupted mid-write | Re-run simulation |

---

## Known Limitations

### `.STEP` parameter sweeps

LTspice packs all sweep runs into a single `.raw` file. The converter handles stepped files in two ways:

* **Default (all steps):** When no `--step` flag is given, all steps are exported with `step` and parameter columns prepended (e.g. `step, R, time, V(out)`). Requires the `.log` file alongside the `.raw` file so step boundaries and parameter values can be read.
* **Single step:** `--step N` (1-indexed) exports only run N without the step prefix columns.

If the `.log` file is missing, the converter falls back to exporting step 0 only and emits a warning.

### FRA and standard `.raw`

A `.fra` simulation does not produce `{name}.raw`. Do not check for it; check for `{name}.fra_<instance>.raw` instead.

---

## Security Constraints

* Execute only: `scripts/run_ltspice.ps1`, LTspice executable, and `ltspice_raw2csv.exe`
* Do not execute arbitrary shell commands
* Validate all file paths before execution
