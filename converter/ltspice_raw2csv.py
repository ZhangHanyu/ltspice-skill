# SPDX-License-Identifier: GPL-3.0-only
import sys
import os
import csv
import argparse
from typing import Optional
import numpy as np
from numpy.typing import NDArray
from PyLTSpice import RawRead


def _hr_size(num: float, suffix: str = 'B') -> str:
	"""Convert bytes to human-readable format."""
	for unit in ['', 'K', 'M', 'G', 'T', 'P']:
		if abs(num) < 1024.0:
			return f"{num:3.1f}{unit}{suffix}"
		num /= 1024.0
	return f"{num:.1f}E{suffix}"


def _print_file_metadata(raw_path: str, props: dict[str, str]) -> None:
	"""Print file-level metadata (file size, title, date, plotname, flags, counts)."""
	try:
		size_bytes = os.path.getsize(raw_path)
		print(f"File: {raw_path}")
		print(f"Size: {_hr_size(size_bytes)} ({size_bytes} bytes)")
	except Exception:
		print(f"File: {raw_path}")
		print("Size: (unknown)")

	if props:
		print(f"Title: {props.get('Title', 'N/A')}")
		print(f"Date: {props.get('Date', 'N/A')}")
		print(f"Plotname: {props.get('Plotname', 'N/A')}")
		print(f"Flags: {props.get('Flags', 'N/A')}")
		print(f"No. Variables: {props.get('No. Variables', 'N/A')}")
		print(f"No. Points: {props.get('No. Points', 'N/A')}")
		print()  # Blank line for readability


def _open_raw(raw_path: str) -> RawRead:
	if not os.path.exists(raw_path):
		raise OSError(f"File not found: {raw_path}")
	try:
		return RawRead(raw_path)
	except Exception as e:
		raise OSError(f"Failed to read {raw_path}: {e}") from e


def preview_short(raw_path: str) -> None:
	"""Print short summary: file metadata only."""
	raw = _open_raw(raw_path)
	props = raw.get_raw_properties()
	_print_file_metadata(raw_path, props)


def preview_detailed(raw_path: str) -> None:
	"""Print detailed summary: file metadata, step info, and variable list."""
	raw = _open_raw(raw_path)
	props = raw.get_raw_properties()
	_print_file_metadata(raw_path, props)

	all_step_indices = raw.get_steps()
	step_params = raw.steps
	n_steps = len(all_step_indices)

	if n_steps > 1:
		print(f"Steps: {n_steps}")
		if step_params:
			param_names = list(step_params[0].keys())
			print(f"Step parameters: {', '.join(param_names)}")
			for i, sp in enumerate(step_params):
				vals = ', '.join(f"{k}={v}" for k, v in sp.items())
				print(f"  Step {i + 1}: {vals}")
		else:
			print("  (step parameter info unavailable — .log file missing?)")
		print()
	elif 'stepped' in (props.get('Flags', '') or ''):
		print("Warning: file has 'stepped' flag but .log not found; step boundaries unknown.")
		print()

	if props:
		print("Variables:")
		for var in props.get('Variables', []):
			print(f"  - {var}")


_AXIS_TRACES = {"time", "frequency"}  # always written at full precision


def _fmt(arr: NDArray, precision: int) -> list:
	"""Format a numpy array for CSV output.

	precision=0 uses full float precision. Otherwise rounds to N significant
	figures using 'g' format, then converts back to float so csv.writer emits
	the shortest exact representation of the rounded value.
	"""
	if precision == 0:
		return arr.tolist()
	return [float(f"{v:.{precision}g}") for v in arr]


def _process_trace(
	trace: str,
	data: NDArray,
	complex_mode: str,
	precision: int = 6,
) -> tuple[list[str], list[list]]:
	"""Process a single trace and return header columns and data columns."""
	data = np.asarray(data)
	# Axis traces (time, frequency) are always written at full precision to
	# preserve adaptive timestep resolution and fine AC sweep points.
	eff = 0 if trace.lower() in _AXIS_TRACES else precision

	# Frequency trace: always export real part only
	if trace.lower() == "frequency":
		return [trace], [_fmt(np.real(data), eff)]

	if not np.iscomplexobj(data):
		return [trace], [_fmt(data, eff)]

	# Complex data handling
	if complex_mode == "ri":
		return (
			[f"{trace}_re", f"{trace}_im"],
			[_fmt(data.real, eff), _fmt(data.imag, eff)]
		)
	elif complex_mode == "ma":
		return (
			[f"{trace}_mag", f"{trace}_ang"],
			[_fmt(np.abs(data), eff), _fmt(np.degrees(np.arctan2(data.imag, data.real)), eff)]
		)
	else:  # "python"
		if eff == 0:
			return [trace], [[str(v) for v in data]]
		return [trace], [[f"{v.real:.{precision}g}{v.imag:+.{precision}g}j" for v in data]]


def raw_to_csv(
	raw_path: str,
	csv_path: Optional[str] = None,
	selected_traces: Optional[list[str]] = None,
	complex_mode: str = "ri",
	quiet: bool = False,
	force: bool = False,
	step: Optional[int] = None,
	precision: int = 6,
) -> None:
	"""Convert LTspice .raw file to CSV.

	:param raw_path: Path to the .raw file.
	:param csv_path: Output CSV path. Defaults to same name as raw_path with .csv extension.
	:param selected_traces: Traces to export. None exports all traces.
	:param complex_mode: Complex number format: 'ri', 'ma', or 'python'.
	:param quiet: Suppress output summary when True.
	:param force: Overwrite existing output without prompting when True.
	:param step: 1-indexed step to export. None exports all steps (with prefix columns for stepped files).
	:param precision: Significant figures for waveform values. 0 = full float precision.
	                  Time and frequency axes always use full precision regardless of this setting.
	:raises OSError: If raw_path cannot be opened.
	:raises ValueError: If no valid traces remain after filtering, or step is out of range.
	:raises FileExistsError: If csv_path exists and the user declines overwrite.
	"""
	if precision < 0:
		raise ValueError("precision must be 0 or greater")

	raw = _open_raw(raw_path)
	all_traces = raw.get_trace_names()

	# Filter traces
	if selected_traces:
		traces = [t for t in selected_traces if t in all_traces]
		missing = [t for t in selected_traces if t not in all_traces]

		if missing:
			print(f"Warning: The following traces were not found and will be skipped: {', '.join(missing)}")

		if not traces:
			raise ValueError(f"No valid traces selected. Available variables: {', '.join(all_traces)}")
	else:
		traces = all_traces

	# Step handling
	all_step_indices = raw.get_steps()  # [0] for non-stepped, [0,1,...] for stepped
	step_params = raw.steps             # None or list of dicts with parameter values
	n_steps = len(all_step_indices)

	if step is not None:
		if step < 1 or step > n_steps:
			raise ValueError(f"Step {step} out of range. File has {n_steps} step(s).")
		export_steps = [all_step_indices[step - 1]]
		show_step_cols = False
	else:
		export_steps = all_step_indices
		show_step_cols = n_steps > 1

	# Warn when stepped flag present but log is missing (only relevant when no explicit --step)
	if step is None and n_steps == 1:
		try:
			flags = raw.get_raw_property('Flags') or ''
			if 'stepped' in flags:
				print("Warning: file has 'stepped' flag but .log not found; exporting step 0 only.")
		except Exception:
			pass

	# Build trace header (inspect first export step to determine column types)
	trace_header: list[str] = []
	for trace in traces:
		sample = np.asarray(raw.get_wave(trace, step=export_steps[0]))
		cols, _ = _process_trace(trace, sample, complex_mode, precision)
		trace_header.extend(cols)

	# Full header with optional step/param prefix
	if show_step_cols:
		param_names = list(step_params[0].keys()) if step_params else []
		header = ['step'] + param_names + trace_header
	else:
		header = trace_header

	# Determine output path
	if csv_path is None:
		csv_path = os.path.splitext(raw_path)[0] + '.csv'

	# Check overwrite
	if os.path.exists(csv_path) and not force:
		response = input(f"File exists: {csv_path}\nOverwrite? (y/n): ").strip().lower()
		if response != 'y':
			raise FileExistsError(f"Conversion cancelled: {csv_path} already exists.")

	total_rows = 0

	with open(csv_path, 'w', newline='') as f:
		writer = csv.writer(f)
		writer.writerow(header)

		for step_idx in export_steps:
			# Build step prefix columns for this step
			if show_step_cols:
				if step_params:
					param_values = list(step_params[step_idx].values())
				else:
					param_values = []
				step_prefix: list = [step_idx + 1] + param_values  # 1-indexed step number
			else:
				step_prefix = []

			# Collect trace data for this step
			step_data_cols: list[list] = []
			for trace in traces:
				data = np.asarray(raw.get_wave(trace, step=step_idx))
				_, data_cols = _process_trace(trace, data, complex_mode, precision)
				step_data_cols.extend(data_cols)

			n_rows = len(step_data_cols[0]) if step_data_cols else 0
			total_rows += n_rows

			for row in zip(*step_data_cols):
				writer.writerow(step_prefix + list(row))

	if not quiet:
		try:
			size_bytes = os.path.getsize(csv_path)
			print(f"Wrote CSV: {os.path.abspath(csv_path)}")
			print(f"Size: {_hr_size(size_bytes)} ({size_bytes} bytes)")
			print(f"Dimensions: {len(header)} columns x {total_rows} rows")
			if show_step_cols:
				print(f"Steps exported: {n_steps}")
		except Exception:
			print(f"Wrote CSV: {os.path.abspath(csv_path)}")


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Convert LTspice .raw simulation files to CSV format",
		epilog="""
Examples:
  # Preview file metadata (short summary)
  python ltspice_raw2csv.py simulation.raw -s

  # Preview with detailed variable list and step info
  python ltspice_raw2csv.py simulation.raw -d

  # Convert all traces to CSV (all steps if stepped)
  python ltspice_raw2csv.py simulation.raw -o output.csv

  # Export specific traces
  python ltspice_raw2csv.py simulation.raw -o output.csv -t "frequency,V(out),I(R1)"

  # Export only step 2 of a .STEP sweep
  python ltspice_raw2csv.py simulation.raw -o output.csv --step 2

  # Convert with magnitude/angle for complex data
  python ltspice_raw2csv.py simulation.raw -o output.csv -c ma

  # Convert silently without output summary
  python ltspice_raw2csv.py simulation.raw -o output.csv -q
		""",
		formatter_class=argparse.RawDescriptionHelpFormatter
	)

	parser.add_argument("rawfile", help="Path to LTspice .raw file")
	parser.add_argument("-o", "--output", dest="csvfile", nargs="?", const="AUTO", metavar="PATH",
		help="Convert to CSV. If specified without PATH, output file uses input name with .csv extension")
	parser.add_argument("-s", "--short", action="store_true", help="Show short preview (metadata only, no variable list)")
	parser.add_argument("-d", "--detailed", "--list-traces", action="store_true", help="Show detailed preview (metadata + step info + variable list)")
	parser.add_argument("-t", "--traces", type=str, metavar="TRACES", help="Comma-separated list of trace names to export (default: all traces)")
	parser.add_argument("--step", type=int, metavar="N",
		help="Export only step N (1-indexed). Default: export all steps for stepped files, "
		     "with 'step' and parameter columns prepended. Use -d to list available steps.")
	parser.add_argument("-c", "--complex-mode", type=str, choices=["ri", "ma", "python"], default="ri",
		metavar="{ri,ma,python}",
		help="""Format for complex numbers:
  ri (default)  - Real/Imaginary: columns {trace}_re, {trace}_im
  ma            - Magnitude/Angle: columns {trace}_mag, {trace}_ang (degrees)
  python        - Python format: single column with complex notation (e.g., '1+2j')""")
	def _positive_int_or_zero(value: str) -> int:
		n = int(value)
		if n < 0:
			raise argparse.ArgumentTypeError("precision must be 0 or a positive integer")
		return n
	parser.add_argument("-p", "--precision", type=_positive_int_or_zero, default=6, metavar="N",
		help="Significant figures for waveform values (default: 6). Use 0 for full float precision. "
		     "Time and frequency axes are always written at full precision.")
	parser.add_argument("-q", "--quiet", action="store_true", help="Suppress output summary after conversion")
	parser.add_argument("-f", "--force", action="store_true", help="Overwrite output file without confirmation")
	parser.add_argument("--op", dest="export_op", action="store_true",
		help="Also export the operating point file ({name}.op.raw) to {name}.op.csv if it exists. "
		     "Note: .op.raw files have no 'time' trace; if --traces includes 'time' it will be skipped with a warning.")

	args = parser.parse_args()

	# Handle AUTO output path (when -o flag used without argument)
	if args.csvfile == "AUTO":
		args.csvfile = os.path.splitext(args.rawfile)[0] + '.csv'

	# Preview modes (when no -o specified)
	if args.csvfile is None:
		try:
			if args.detailed:
				preview_detailed(args.rawfile)
			else:
				preview_short(args.rawfile)
		except OSError as e:
			print(f"Error: {e}")
			sys.exit(1)
		return

	# Conversion mode
	selected_traces: Optional[list[str]] = None
	if args.traces:
		selected_traces = [t.strip() for t in args.traces.split(",")]

	try:
		raw_to_csv(args.rawfile, args.csvfile, selected_traces, args.complex_mode,
		           args.quiet, args.force, args.step, args.precision)
		if args.export_op:
			op_raw = os.path.splitext(args.rawfile)[0] + '.op.raw'
			if os.path.exists(op_raw):
				op_csv = os.path.splitext(args.csvfile)[0] + '.op.csv'
				# .op.raw is never stepped; step=None (default) is always correct here
				raw_to_csv(op_raw, op_csv, selected_traces, args.complex_mode,
				           args.quiet, args.force, precision=args.precision)
			elif not args.quiet:
				print(f"Note: No operating point file found ({op_raw}), skipping --op export.")
	except (ValueError, FileExistsError, OSError) as e:
		print(f"Error: {e}")
		sys.exit(1)


if __name__ == "__main__":
	main()
