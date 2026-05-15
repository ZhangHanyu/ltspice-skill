# ltspice_raw2csv

Convert LTspice `.raw` binary simulation files to CSV. Supports all simulation types (TRAN, AC, DC operating point, FRA), `.STEP` parameter sweeps, and three complex-number export formats.

## License

GPL-3.0 — see [LICENSE](LICENSE). This tool depends on [PyLTSpice](https://github.com/nunobrum/PyLTSpice) (GPL-3.0).

## Requirements

- Python 3.10+
- PyLTSpice, NumPy (see `requirements.txt`)

## Setup

```powershell
pip install -r requirements.txt
```

To use the pre-built executable instead, see the **Building the exe** section below.

---

## Usage

```
python ltspice_raw2csv.py <rawfile> [options]
```

### Preview

```powershell
# Short: file metadata only
python ltspice_raw2csv.py simulation.raw -s

# Detailed: metadata + step info (if .STEP) + variable list
python ltspice_raw2csv.py simulation.raw -d
```

Example `-d` output for a stepped file:
```
File: RC_step.raw
Size: 95.5KB (97840 bytes)
...
Plotname: Transient Analysis
Flags: real forward stepped
No. Variables: 6
No. Points: 3463

Steps: 3
Step parameters: r
  Step 1: r=1000
  Step 2: r=2000
  Step 3: r=3000

Variables:
  - time
  - V(vin)
  - V(vout)
  ...
```

### Convert to CSV

```powershell
# All traces, auto-named output
python ltspice_raw2csv.py simulation.raw -o

# Explicit output path
python ltspice_raw2csv.py simulation.raw -o output.csv

# Specific traces only (comma-separated, case-sensitive, no spaces)
python ltspice_raw2csv.py simulation.raw -o output.csv --traces "time,V(out),I(L1)"

# Also export operating point (.op.raw → .op.csv) in one call
python ltspice_raw2csv.py simulation.raw -o output.csv --op

# Force overwrite, suppress summary
python ltspice_raw2csv.py simulation.raw -o output.csv -f -q
```

### .STEP parameter sweeps

For files with `.STEP`, all steps are exported by default with `step` and parameter columns prepended. A `.log` file must be present alongside the `.raw` file.

```powershell
# All steps — output has columns: step, <param>, time, V(out), ...
python ltspice_raw2csv.py sweep.raw -o sweep_all.csv -f -q

# Single step (1-indexed) — no step prefix columns
python ltspice_raw2csv.py sweep.raw -o sweep_s2.csv --step 2 -f -q
```

Example all-steps CSV (first rows):
```
step,r,time,V(vout)
1,1000,0.0,0.0
1,1000,1e-09,4.3e-07
...
2,2000,0.0,0.0
...
```

### Complex number formats

For AC and FRA files, which contain complex-valued traces:

```powershell
# ri (default): separate _re and _im columns
python ltspice_raw2csv.py ac.raw -o ac_ri.csv

# ma: magnitude and phase angle in degrees (_mag, _ang columns)
python ltspice_raw2csv.py ac.raw -o ac_ma.csv --complex-mode ma

# python: single column with Python complex notation, e.g. "1+2j"
python ltspice_raw2csv.py ac.raw -o ac_py.csv --complex-mode python
```

The `frequency` trace is always exported as real values regardless of mode.

---

## Command-line reference

```
positional arguments:
  rawfile                    Path to LTspice .raw file

options:
  -o [PATH], --output [PATH] Convert to CSV. Omit PATH to auto-name from input.
  -s, --short                Short preview: metadata only
  -d, --detailed             Detailed preview: metadata + step info + variable list
  --traces TRACES            Comma-separated trace names to export (default: all)
  --step N                   Export only step N (1-indexed). Default: all steps,
                             with step/param prefix columns for stepped files.
  --complex-mode {ri,ma,python}
                             Format for complex traces (default: ri)
                               ri     → {trace}_re, {trace}_im
                               ma     → {trace}_mag, {trace}_ang (degrees)
                               python → single column, Python complex string
  --op                       Also export {name}.op.raw → {name}.op.csv
  -q, --quiet                Suppress conversion summary
  -f, --force                Overwrite output without confirmation
  -h, --help                 Show help message
```

---

## Supported simulation types

| Simulation | Output file | Notes |
|------------|-------------|-------|
| `.TRAN` transient | `name.raw` | Real-valued traces |
| `.AC` analysis | `name.raw` | Complex-valued traces |
| `.DC` sweep | `name.raw` | Real-valued traces |
| `.OP` operating point | `name.op.raw` | Use `--op` or convert directly |
| `.FRA` frequency response | `name.fra_<n>.raw` | Complex; use `--complex-mode ma` for Bode |
| `.STEP` parameter sweep | any of the above | Multi-step; all steps exported by default |

---

## Building the exe

The `.exe` is not included in the repository (GPL-3.0 distribution requirement). Build it locally once:

```powershell
cd converter

# First time only — create venv
python -m venv .venv
.\.venv\Scripts\pip install pyinstaller pyltspice numpy

# Build (~30–60 s, produces ~20 MB exe)
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
