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

* `.asc` → LTspice schematic (GUI-generated, preferred)
* `.net` / `.cir` → LTspice/SPICE netlist

**Preference:** Always prefer `.asc` — it is the editable source of truth and supports back-annotation. Use `.net`/`.cir` only when `.asc` is unavailable.

---

## Environment Assumptions

* OS: Windows
* LTspice executable available via full path
* `ltspice_raw2csv.exe` available (built on first run if absent — see Converter Setup below)
* File system access permitted

---

## Converter Setup (First Run)

`ltspice_raw2csv.exe` is not distributed in the repository; it must be built locally once.

**Check:** Before any conversion step, verify `converter_path` exists:

```powershell
Test-Path "<converter_path>"
```

**Build if missing:** Run the following from the `converter/` directory. Full commands are in `CLAUDE.md`.

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

### Step 1 — Run LTspice

```
"<ltspice_path>" -run -b <input_file>
```

* `-run`: start simulation
* `-b`: batch mode (no GUI)
* Works for both `.asc` and `.net`

---

### Step 2 — Determine Output Files

LTspice writes outputs to the same directory as the input, using the same base name:

```
C:\sim\buck.asc  →  C:\sim\buck.raw
                     C:\sim\buck.op.raw  (if .op analysis present)
                     C:\sim\buck.log
```

---

### Step 3 — Wait for Simulation Completion

LTspice in batch mode (`-b`) runs **synchronously** — the process exits only when the simulation finishes (or fails). Simply wait for the process to return; no polling required.

---

### Step 4 — Validate Simulation Success

Check that `.raw` exists. Then read `.log` and scan for any of these failure indicators:

* `Error:`
* `Analysis failed`
* `.TRAN failed`
* `No operating point found`
* `Singular matrix`
* `Time step too small`

If `.raw` is missing or `.log` contains any of the above → simulation failed; report the relevant log lines to the user.

---

### Step 5 — Convert to CSV

Build the converter command:

```
<converter_path> <name>.raw -o <output_csv> [--op] [--step N] [--traces "time,V(out),I(L1)"] [--complex-mode ri|ma|python] [-q] [-f]
```

* `--op` — also exports `{name}.op.raw` to `{name}.op.csv` in the same call (use instead of a separate invocation)
* `--step N` — export only step N of a `.STEP` sweep (1-indexed); omit to export all steps with prefix columns
* Apply `-q` and `-f` unless explicitly disabled by the user

---

## Procedure — FRA Simulation (.FRA)

FRA (Frequency Response Analysis) uses a different output structure. The `.fra` directive is controlled by `@` device instances in the circuit. See `REFERENCE.md §2 .FRA` and `§3 @ / &` for syntax.

### Step 1 — Run LTspice (same command)

```
"<ltspice_path>" -run -b <input_file>
```

### Step 2 — Determine FRA Output Files

```
C:\sim\buck.asc  →  C:\sim\buck.fra_1.raw   (one per @ device instance)
                     C:\sim\buck.log
```

Note: FRA does NOT produce `buck.raw`. Check for `buck.fra_<n>.raw` instead.

### Step 3 — Wait for Completion

Same as standard simulation: wait for the LTspice process to exit. FRA simulations can take significantly longer than transient simulations — this is expected.

### Step 4 — Validate

Check `.log` for the same failure indicators as standard simulation.

### Step 5 — Convert FRA Output

```
<converter_path> <name>.fra_1.raw -o <output_csv> --complex-mode ma [-q] [-f]
```

FRA output is complex (magnitude/phase). Use `--complex-mode ma` for Bode-plot-ready columns.

---

## Circuit Modification Workflow

When asked to modify a circuit before simulating:

1. **Read `REFERENCE.md`** for the relevant syntax (directive, component, or `.asc` format).
2. **Prefer editing `.asc`** over `.net` — changes to `.asc` persist when the user reopens LTspice; changes to `.net` are overwritten when LTspice re-netlists from `.asc`.
3. **For netlist edits (`.net`/`.cir`):** Edit the directive or element line directly. LTspice netlist syntax is in `REFERENCE.md §1–§5`.
4. **For schematic edits (`.asc`):** Follow the `.asc` file format rules in `REFERENCE.md §6`. Key points:
   - Coordinates must be on the 16-unit grid
   - `SYMATTR Value` sets component values; `SYMATTR InstName` sets instance names
   - Simulation directives live in `TEXT` records: `TEXT <x> <y> Left 2 !<directive>`
5. **Re-run the simulation** after any modification using the standard or FRA procedure above.
6. **Verify** by checking the `.log` for errors and inspecting the output CSV.

---

## LTspice Command Notes

| Flag | Effect |
|------|--------|
| `-run` | Start simulation |
| `-b` | Batch mode (no GUI) |
| `-netlist` | Export `.asc` to `.net` only, no simulation |

Do NOT use `-ascii` (severe performance degradation) or GUI flags (`-big`, `-max`).

---

## File Behavior Rules

* All output files are written to the same directory as the input file
* Output base name matches input base name
* Example: `buck.asc` → `buck.raw`, `buck.op.raw`, `buck.log`

---

## Smart Behavior (Agent Guidelines)

* Prefer `.asc` over `.net` when both exist
* Auto-derive all output filenames from the input path
* If traces not specified: run `ltspice_raw2csv.exe <file>.raw -d` first and suggest available traces
* Use `-q` and `-f` by default unless the user explicitly asks otherwise
* Use `--op` flag (single converter call) instead of two separate calls when exporting operating point
* For FRA: use `--complex-mode ma` by default (Bode-plot-ready output)

---

## Error Handling

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| `.raw` not created | Simulation failure or bad netlist | Read `.log`, show relevant error lines to user |
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

* Execute only: LTspice executable and `ltspice_raw2csv.exe`
* Do not execute arbitrary shell commands
* Validate all file paths before execution
