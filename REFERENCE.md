# LTspice Reference

Agent-facing reference for reading, writing, and modifying LTspice `.asc` schematics and `.net`/`.cir` netlists.

> **Attribution:** This document is based on LTspice® documentation and help files, © Analog Devices, Inc. (ADI). LTspice is a trademark of Analog Devices. This reference is a paraphrase and summary for interoperability purposes.

---

## 1. Netlist General Conventions

### Case Sensitivity
LTspice netlists are **case-insensitive** (Unicode-aware case folding). `R1`, `r1`, and `R1` are the same. Model names, node names, and directives are all case-insensitive.

### First Line
The first line of a netlist (`.net`/`.cir`) is treated as a **title/comment** and is ignored by the simulator. Never place a circuit element or directive on line 1.

### Line Continuation
A `+` at the start of a line (column 1) **continues the previous logical line**. Whitespace before/after `+` is optional but the `+` must be the first non-whitespace character.

```
.model MyMOS NMOS(level=3
+ tox=10n vth0=0.5
+ u0=450)
```

### Comments
- `*` as the **first character** of a line: entire line is a comment.
- `;` anywhere on a line: rest of line is a comment (inline comment).
- `$` anywhere on a line: rest of line is a comment (alternate inline comment).

```
* This whole line is a comment
R1 a b 1k  ; inline comment
```

### Node Naming
- Node names are case-insensitive strings.
- Node **`0`** is ground. `GND` is also treated as ground by LTspice convention (via a built-in flag symbol). Purely numeric node names other than `0` (e.g., `00`, `1`, `2`) are distinct nodes, not ground.
- Node names cannot contain spaces. Use underscore or alphanumeric.
- `$G_` prefix: nodes whose names start with `$G_` are automatically **global** (equivalent to `.global` declaration).

### Number Format and Suffixes
Numbers may use engineering suffixes (case-insensitive except `Meg`):

| Suffix | Multiplier | Notes |
|--------|-----------|-------|
| T | 1e12 | tera |
| G | 1e9 | giga |
| Meg | 1e6 | must be `Meg` (not `M`); case-insensitive |
| K | 1e3 | kilo |
| m | 1e-3 | milli (lower or upper) |
| mil | 25.4e-6 | mils (mechanical) |
| u or μ | 1e-6 | micro |
| n | 1e-9 | nano |
| p | 1e-12 | pico |
| f | 1e-15 | femto |

Format `6K34` means `6.34K` (= 6340). Digits after the suffix are fractional digits.

Trailing non-numeric characters that are not a recognized suffix are ignored: `10Ω` = `10`, `4.7uF` = `4.7u` = 4.7e-6.

### Parameter Expressions `{expr}`
Curly braces delimit a **parameter expression** that is evaluated at simulation time:
- `R1 a b {R_val}` — use `.param R_val=1k`
- `R1 a b {2*R_val+100}` — arithmetic expression
- Required when the value is an expression (not just a plain number) to prevent ambiguity with element suffixes.

### Element Type Identification
The first letter of an element name (instance name) determines its type:

| Letter | Element |
|--------|---------|
| R | Resistor |
| C | Capacitor |
| L | Inductor |
| K | Mutual inductance |
| V | Voltage source |
| I | Current source |
| E | Voltage-controlled voltage source |
| F | Current-controlled current source |
| G | Voltage-controlled current source |
| H | Current-controlled voltage source |
| B | Behavioral (arbitrary) source |
| S | Voltage-controlled switch |
| W | Current-controlled switch |
| D | Diode |
| Q | BJT |
| M | MOSFET |
| J | JFET |
| Z | MESFET or IGBT |
| T | Lossless transmission line |
| O | Lossy transmission line |
| U | Uniform distributed RC line |
| X | Subcircuit instance |
| @ | Frequency Response Analyzer (FRA device) |
| & | Frequency Response Analysis Probe (FRAPROBE) |

---

## 2. Simulation Directives

### `.TRAN` — Transient Analysis

```
.tran <Tstep> <Tstop> [<Tstart> [<dTmax>]] [modifiers]
.tran <Tstop>
```

- `Tstep`: suggested time step (output interval); simulator may use smaller internal steps.
- `Tstop`: end time.
- `Tstart`: time at which output saving begins (default 0); simulation still runs from t=0.
- `dTmax`: maximum internal time step (default = `Tstop/100` or `Tstep`, whichever smaller).

**Modifiers** (space-separated after parameters):
- `UIC` — Use Initial Conditions; skip DC operating point, use `.ic` values directly.
- `steady` — Run until steady state detected before recording.
- `nodiscard` — Do not discard pre-`Tstart` data.
- `startup` — Ramp sources from 0 at t=0 (soft-start).
- `step <dt>` — Override minimum step size.
- `convreport` — Print convergence failure details.

**State save/load** (on separate lines referencing the `.tran` directive):
```
.tran 1u 10m
.savestate statefile.bin 5m   * save state at t=5m
.loadstate statefile.bin      * start from saved state
```

### `.AC` — Small-Signal AC Analysis

```
.ac <oct|dec|lin> <Nsteps> <StartFreq> <EndFreq>
.ac list <f1> <f2> ...
.ac file=<filename>
```

- `oct`: steps per octave; `dec`: steps per decade; `lin`: linearly spaced.
- `Nsteps`: number of points per decade/octave, or total points for `lin`.
- Frequencies in Hz.

### `.DC` — DC Sweep

```
.dc <source1> <start1> <stop1> <step1> [<source2> <start2> <stop2> <step2> ...]
.dc <source1> list <v1> <v2> ...
```

- Up to 3 nested sweeps.
- `source1` may be a voltage/current source name, a model parameter (`param NAME`), or `temp`.
- Example: `.dc V1 0 5 0.1 V2 0 3 1`

### `.OP` — DC Operating Point

```
.op
```

Finds DC bias point. Results appear in `.log` file and in the schematic annotation (node voltages and branch currents). Use `.options logopinfo` to log all OP data.

**Convergence methods** (LTspice tries in order if needed):
1. Standard Newton-Raphson
2. Damped pseudo-transient (Gmin stepping)
3. Source stepping
4. Diagonal Jacobian
5. Damped Newton with source stepping

### `.NOISE` — Noise Analysis

```
.noise V(<out>[,<ref>]) <src> <oct|dec|lin> <Nsteps> <StartFreq> <EndFreq>
```

- `V(<out>)`: output node voltage; `V(<out>,<ref>)`: differential.
- `<src>`: name of independent source driving the input.
- Output traces available: `V(onoise)` (output-referred), `V(inoise)` (input-referred).
- Individual noise contributors listed in `.log` file.

### `.TF` — DC Transfer Function

```
.TF V(<node>[,<ref>]) <source>
.TF I(<Vsource>) <source>
```

Computes small-signal DC gain, input resistance, and output resistance.

### `.FOUR` — Fourier Analysis

```
.four <freq> [<Nharmonics>] [<Nperiods>] <trace1> [<trace2> ...]
```

- `freq`: fundamental frequency (Hz).
- `Nharmonics`: number of harmonics to compute (default 9).
- `Nperiods`: number of periods to use from end of simulation (default 1); `-1` uses entire simulation range.
- Results printed in `.log` file (THD, magnitude, phase per harmonic).

### `.STEP` — Parameter Sweep

```
.step [oct|dec|lin] param <name> <start> <stop> <incr>
.step [oct|dec|lin] param <name> <start> <stop> <N>   * for oct/dec
.step param <name> list <v1> <v2> ...
.step param <name> file=<filename>
.step <source> <start> <stop> <incr>
.step <TYPE> model(<PARAM>) <start> <stop> <incr>
.step temp <start> <stop> <incr>
```

- Up to 3 nested `.step` directives are supported.
- `oct`/`dec`/`lin`: logarithmic/linear spacing.
- `TYPE model(PARAM)`: step a model parameter (e.g., `.step NPN Q2N3904(Bf) 100 300 50`).
- `temp`: sweep temperature.
- File form: one value per line in file.

### `.PARAM` — User-Defined Parameters

```
.param <name>=<expression>
.param <name>="<string>"
```

- Parameters are global unless defined inside a `.subckt` (where they are local with optional defaults).
- `temp` is a reserved parameter (simulation temperature in °C).

**Predefined constants:**

| Name | Value |
|------|-------|
| PI | 3.14159265358979... |
| BOLTZ | 1.38065e-23 J/K |
| ECHARGE | 1.60218e-19 C |
| PLANCK | 6.62607e-34 J·s |
| KELVIN | 273.15 |
| GMIN | simulator Gmin value |

**Functions available in `.param` expressions:**

`abs(x)`, `acos(x)`, `acosh(x)`, `asin(x)`, `asinh(x)`, `atan(x)`, `atanh(x)`, `atan2(y,x)`, `cos(x)`, `cosh(x)`, `exp(x)`, `floor(x)`, `ceil(x)`, `hypot(x,y)`, `int(x)`, `ln(x)`, `log(x)` (base 10), `log2(x)`, `max(x,y)`, `min(x,y)`, `pow(x,y)`, `pwr(x,y)`, `pwrs(x,y)`, `rand(x)`, `random(x)`, `round(x)`, `sin(x)`, `sinh(x)`, `sqrt(x)`, `tan(x)`, `tanh(x)`, `sgn(x)`, `u(x)` (unit step), `uramp(x)`

**Statistical functions:** `gauss(sigma)`, `flat(x)`, `mc(nom,tol)` (Monte Carlo)

**Conditional:** `if(cond,true_val,false_val)`, `select(cond,a,b)`, `table(x, x1,y1, x2,y2, ...)` (piecewise linear lookup)

**String operations:** `str(x)` converts number to string; `val("string")` parses string to number.

**Operator precedence** (high to low): unary `-`/`+` → `**`/`^` → `*`/`/`/`%` → `+`/`-` → comparisons → `!` → `&&` → `||`

### `.FUNC` — User-Defined Functions

```
.func <name>([arg1, arg2, ...]) {<expression>}
```

- Functions use **dynamic scoping**: they see the `.param` environment at the point of use.
- Recursive functions are supported.
- Example: `.func Rdiv(R1,R2) {R1*R2/(R1+R2)}`

### `.MEAS` / `.MEASURE` — Evaluate Simulation Results

**Point-based:**
```
.meas [tran|ac|dc|noise|tf] <name> FIND <expr> [AT <t>] [RISE|FALL|CROSS=<n>] [TD=<delay>]
.meas [tran|ac|dc] <name> PARAM <expr>
.meas [tran|ac|dc] <name> <expr> WHEN <cond> [RISE|FALL|CROSS=<n>] [TD=<delay>]
```

**Range-based:**
```
.meas [tran|ac|dc] <name> AVG|MAX|MIN|PP|RMS|INTEG <expr> [FROM <t1>] [TO <t2>]
.meas [tran|ac|dc] <name> DERIV <expr> [AT <t>]
```

**Two-point (TRIG/TARG):**
```
.meas tran <name> TRIG <expr1> [VAL=<v>] [RISE|FALL|CROSS=<n>] [TD=<td>]
+                 TARG <expr2> [VAL=<v>] [RISE|FALL|CROSS=<n>] [TD=<td>]
```

- `RISE=<n>`: nth rising edge; `FALL`: falling; `CROSS`: either.
- Results available as `.param` values in subsequent `.meas` statements.
- Results written to `.log` and optionally to SQLite `.db` file.

### `.IC` — Set Initial Conditions

```
.ic [V(<node>)=<value>] ... [I(<inductor>)=<value>] ...
```

- Sets initial node voltages and inductor currents for transient analysis.
- Applied at t=0. With `UIC` in `.tran`, the DC operating point is skipped.
- Multiple `.ic` directives are allowed (last one wins for duplicates).

### `.NODESET` — DC Operating Point Hints

```
.nodeset V(<node>)=<value> ...
```

- Provides starting-point hints for the DC solver; does not force the final solution.
- Useful for breaking symmetry or aiding convergence in multi-stable circuits.

### `.TEMP` — Temperature

```
.temp <T1> [<T2> ...]
```

- Sets simulation temperature(s) in °C.
- Multiple values are equivalent to `.step temp list T1 T2 ...`
- Default temperature is 27°C (set via `.options temp=27`).

### `.OPTIONS` — Simulator Options

```
.options <keyword>=<value> ...
```

Key options (with defaults):

| Option | Default | Description |
|--------|---------|-------------|
| abstol | 1e-12 A | Absolute current tolerance |
| reltol | 0.001 | Relative tolerance |
| vntol | 1e-6 V | Absolute voltage tolerance |
| trtol | 1.0 | Transient error tolerance multiplier |
| chgtol | 1e-14 C | Charge tolerance |
| gmin | 1e-12 S | Minimum conductance |
| method | trap | Integration method: `trap`, `modtrap`, `gear`, `euler` |
| maxord | 2 | Maximum order for Gear integration |
| itl1 | 100 | DC iteration limit |
| itl2 | 50 | DC transfer curve iteration limit |
| itl4 | 10 | Transient time-point iteration limit |
| itl6 | 0 | Source-stepping iterations (0=auto) |
| temp | 27 | Default temperature (°C) |
| tnom | 27 | Nominal temperature for model params (°C) |
| numdgt | 6 | Significant digits in output |
| plotwinsize | 0 | Waveform compression: 0=off |
| logopinfo | 0 | Log OP info: 1=enable |
| nomarch | 0 | 1=suppress waveform file |
| noopiter | 0 | 1=skip DC OP iteration |
| srcsteps | 4 | Number of source-stepping steps |
| gminsteps | 10 | Number of Gmin-stepping steps |
| maxstep | — | Max transient timestep |
| baudrate | — | Baud rate for serial source |

### `.SAVE` — Limit Saved Data

```
.save <trace1> [<trace2> ...]
.save *           * save all node voltages
.save V(*)        * save all node voltages
.save I(*)        * save all element currents
```

- Without `.save`, all node voltages and first-order element currents are saved.
- With `.save`, only the listed quantities are saved.
- Wildcards: `*` (any string), `?` (single character).
- Hierarchical reference: `V(X1:X2:node)` for subcircuit nodes.
- `I(Lx)`, `I(Vx)`, `I(Rx)` for element currents.

### `.WAVE` — Write to WAV File

```
.wave <filename.wav> <Nbits> <SampleRate> V(<n1>) [V(<n2>) ...]
```

- `Nbits`: 1–32 bits per sample.
- `SampleRate`: 1–4,294,967,295 samples/second.
- Up to `Nbits * channels` bits per frame.

### `.NET` — Network Parameters

```
.net [V(<out>[,<ref>]) | I(<Rout>)] <Vin|Iin> [Rin=<v>] [Rout=<v>]
```

- Computes S, Y, Z, H parameters.
- Default `Rin` = `Rout` = 50Ω.

### `.GLOBAL` — Global Nodes

```
.global <node1> [<node2> ...]
```

- Makes listed nodes visible across all subcircuit hierarchy levels.
- Equivalent to a wire connecting all instances of the node at top level.
- Nodes prefixed `$G_` are automatically global without `.global`.

### `.BACKANNO` — Back-Annotation

```
.backanno
```

- Causes device currents to be annotated back onto the schematic after simulation.
- Automatically included in netlists generated from `.asc` schematics by LTspice.

---

### `.INCLUDE` — Include Another File

```
.include <filename>
.inc <filename>
```

- Inserts the contents of `<filename>` into the netlist at the point of the directive.
- Used for netlists and subcircuit definitions that are not in library format.
- Path may be absolute or relative to the current file.

---

### `.LIB` — Include a Library

```
.lib <filename> [<entry>]
```

- Loads a model/subcircuit library file.
- If `<entry>` is specified, only that named subcircuit or model is loaded from the file (reduces memory use for large libraries).
- Path may be absolute or relative. LTspice also searches the standard library paths.

---

### `.END` — End of Netlist

```
.end
```

- Marks the end of the top-level netlist. Everything after `.end` is ignored.
- Required as the final line of standalone `.cir`/`.net` files.
- Not required (and typically absent) in `.asc`-generated netlists — LTspice appends it automatically.

---

### `.FRA` — Time-Domain Frequency Response Analysis

```
.fra [Tstart=<val>] [dTmax=<val>] [Tstep=<val>] [Tstop=<val>] [uic] [startup] [loadstate[=<filename>]] [savestate[=<filename>]] [savestatetime=<time>]
```

- Runs a specialised transient simulation that sweeps sinusoidal stimuli across a frequency range to produce a Bode plot. Intended primarily for SMPS loop-stability analysis.
- Requires at least one `@` (FRA) device instance in the circuit; the `@` device controls all frequency-sweep parameters.
- All parameters are optional and keyword-specified (any order).
- `Tstop` is optional — simulation auto-stops when all FRA devices have completed their sweep.
- `uic`, `startup`, `loadstate`, `savestate`, `savestatetime` behave identically to `.TRAN`.
- Output is written to `<circuit>.fra_<fra_instance>.raw` as complex (AC-like) data.
- Example: `.fra` (all parameters taken from the `@` device)

---

## 3. Circuit Elements

### R — Resistor

```
Rxxx n+ n- <value> [tc=<tc1>[,<tc2>[,<tc3>...]]] [temp=<T>] [m=<N>]
Rxxx n+ n- R=<expr> [tc=...]
```

- Temperature coefficient: `R = R0 * (1 + tc1*ΔT + tc2*ΔT² + ...)`; `ΔT = T - Tnom`.
- `temp=<T>`: instance temperature override.
- `m=<N>`: multiplicity (N resistors in parallel).
- Value may be `{expr}`.

### C — Capacitor

```
Cxxx n+ n- <value> [Rser=<v>] [Lser=<v>] [Rpar=<v>] [Cpar=<v>] [ic=<v>] [m=<N>]
Cxxx n+ n- Q=<expr> [ic=<v>]
```

- `Rser`, `Lser`, `Rpar`, `Cpar`: parasitics.
- `ic=<v>`: initial voltage.
- `m=<N>`: multiplicity.
- **Nonlinear form**: `Q=<expr>` where expression uses `x` = voltage across the capacitor (V(n+) - V(n-)). Capacitance = dQ/dV.
- Example: `C1 a 0 Q=1p*x + 0.1p*x^2`

### L — Inductor

```
Lxxx n+ n- <value> [Rser=<v>] [Cpar=<v>] [ic=<v>] [m=<N>]
Lxxx n+ n- Flux=<expr> [ic=<v>]
```

- `Rser`: series resistance (default 1mΩ).
- `Cpar`: parallel capacitance.
- `ic=<v>`: initial current.
- **Nonlinear form**: `Flux=<expr>` where `x` = current through inductor. Inductance = dFlux/dI.
- **Hysteretic core** (on same line or via `symattr`):
  ```
  Lxxx n+ n- <inductance> Hc=<coercivity> Br=<remnance> Bs=<saturation>
  + Lm=<mean_path_len> Lg=<gap_len> A=<cross_area> N=<turns>
  ```

### K — Mutual Inductance

```
Kxxx <L1> <L2> [<L3> ...] <coupling_coefficient>
```

- Coupling coefficient: -1.0 to 1.0.
- For two inductors: `M = k * sqrt(L1 * L2)`.
- For N inductors: expanded into N*(N-1)/2 pair couplings, each with the same coefficient.
- Multiple `K` statements can couple different pairs differently.

### V — Voltage Source

```
Vxxx n+ n- <value>
Vxxx n+ n- <waveform>
Vxxx n+ n- SINE(...)
Vxxx n+ n- PULSE(...)
```

See Section 4 for waveform syntax.

Additional options:
- `Rser=<v>`: internal series resistance.
- `Cpar=<v>`: parallel capacitance.
- `Ilimit=<v>`: current limit (behavioral).
- `Trigger=<expr>`: trigger expression for waveform start.

### I — Current Source

```
Ixxx n+ n- <value>
Ixxx n+ n- <waveform>
Ixxx n+ n- R=<value>   * makes it a resistor with Norton equivalent
```

- `load`: flag indicating this is a load source (for steady-state detection).
- `tbl=(<v1>,<i1>) (<v2>,<i2>) ...`: piecewise-linear V-I characteristic.
- `table=(<v1>,<i1>) ...`: same as `tbl=`.
- `step(<level>)`: step-load current (for `.tran steady`).

### E — Voltage-Controlled Voltage Source (VCVS)

```
Exxx n+ n- nc+ nc- <gain>
Exxx n+ n- VALUE={<expr>}
Exxx n+ n- TABLE(<expression>)=(<x1>,<y1>) (<x2>,<y2>) ...
Exxx n+ n- tbl=(<x1>,<y1>) (<x2>,<y2>) ...
Exxx n+ n- LAPLACE={<expr>} [window=<w>] [nfft=<N>] [mtol=<v>]
Exxx n+ n- POLY(<N>) <nc1+> <nc1-> [<nc2+> <nc2-> ...] <p0> <p1> ...
```

- Linear: `Vout = gain * (Vnc+ - Vnc-)`.
- `VALUE={expr}`: behavioral; expression may use `V(nc+,nc-)`, `I(Vsrc)`, etc.
- `LAPLACE={}`: frequency-domain transfer function (convolution in time domain).

### F — Current-Controlled Current Source (CCCS)

```
Fxxx n+ n- <Vnam> <gain>
Fxxx n+ n- VALUE={<expr>}
Fxxx n+ n- POLY(<N>) <Vnam1> [<Vnam2> ...] <p0> <p1> ...
```

- `Vnam`: name of voltage source through which controlling current flows (must be a `V` element; use a `V 0V` dummy if needed).
- `gain`: `Iout = gain * I(Vnam)`.
- `VALUE={expr}`: behavioral.

### G — Voltage-Controlled Current Source (VCCS)

```
Gxxx n+ n- nc+ nc- <transconductance>
Gxxx n+ n- VALUE={<expr>}
Gxxx n+ n- TABLE(<expression>)=(<x1>,<y1>) ...
Gxxx n+ n- LAPLACE={<expr>}
Gxxx n+ n- POLY(<N>) ...
```

- Linear: `Iout = Gm * (Vnc+ - Vnc-)`.

### H — Current-Controlled Voltage Source (CCVS)

```
Hxxx n+ n- <Vnam> <transresistance>
Hxxx n+ n- VALUE={<expr>}
Hxxx n+ n- POLY(<N>) <Vnam1> [<Vnam2> ...] <p0> <p1> ...
```

- `Vout = Rm * I(Vnam)`.

### B — Behavioral (Arbitrary) Source

```
Bxxx n+ n- V=<expr>      * voltage source
Bxxx n+ n- I=<expr>      * current source
Bxxx n+ n- R=<expr>      * resistor (instantaneous)
Bxxx n+ n- P=<expr>      * power (Watts dissipated)
```

**Expression variables and functions available in B-source expressions:**

- `V(n)`, `V(n+,n-)`: node voltage.
- `I(Vxxx)`, `I(Rxxx)`, `I(Lxxx)`, etc.: element current.
- `time`: simulation time variable.
- `ddt(x)`: time derivative d/dt.
- `idt(x)`: integral from t=0 (use `idtmod` for modulo integration).
- `sdt(x)`: integral (same as `idt` in most contexts).
- `absdelay(expr, td)`: expression delayed by `td` seconds.
- `idtmod(x, modulus [,offset [,ic]])`: modulo integrator.

**Math functions:** `abs`, `acos`, `acosh`, `asin`, `asinh`, `atan`, `atanh`, `atan2`, `ceil`, `cos`, `cosh`, `exp`, `floor`, `hypot`, `int`, `ln`, `log`, `log2`, `max`, `min`, `pow`, `pwr`, `pwrs`, `rand`, `round`, `sgn`, `sin`, `sinh`, `sqrt`, `tan`, `tanh`, `u(x)` (unit step), `uramp(x)`

**Limiting:** `uplim(x, limit)`, `dnlim(x, limit)` — soft limits with smooth transition.

**Noise:** `white(power_density)`, `noise(f,power)` — inject noise.

**Small-signal only:** `smallsig(node,gain)` — applies only during AC analysis.

**CRITICAL operator note:** In B-source expressions, `^` is **bitwise XOR**, not exponentiation. Use `**` or `pow(x,y)` for exponentiation.

**Laplace convolution:**
```
Bxxx n+ n- V=laplace(V(in), {<H(s)>})
```
`s` is the complex frequency variable. This computes the convolution of the input with the impulse response of H(s).

### S — Voltage-Controlled Switch

```
Sxxx n1 n2 nc+ nc- <model> [on|off]
.model <mname> SW [Vt=<v>] [Vh=<v>] [Ron=<v>] [Roff=<v>] [Lser=<v>] [Vser=<v>] [Ilimit=<v>]
```

- `Vt`: threshold voltage (default 0).
- `Vh`: hysteresis voltage (default 0).
  - `Vh > 0`: hysteresis band (turns on at Vt+Vh, off at Vt-Vh).
  - `Vh = 0`: sharp (ideal) switching.
  - `Vh < 0`: smooth (gradual) transition.
- `Ron`: on-state resistance (default 1Ω).
- `Roff`: off-state resistance (default 1MΩ).
- `Lser`: series inductance.
- `Vser`: series voltage offset.
- `Ilimit`: current limiting.

**Level 2 switch** (charge-based, smoother transitions):
```
.model <mname> SW level=2 [Vt=<v>] [Vh=<v>] [Ron=<v>] [Roff=<v>]
```

### W — Current-Controlled Switch

```
Wxxx n1 n2 <Vnam> <model> [on|off]
.model <mname> CSW [It=<v>] [Ih=<v>] [Ron=<v>] [Roff=<v>]
```

- `Vnam`: voltage source through which controlling current flows.
- `It`: threshold current.
- `Ih`: hysteresis current.

### D — Diode

```
Dxxx anode cathode <model> [area] [off] [m=<v>] [n=<v>] [temp=<T>]
```

**Idealized diode model** (no semiconductor physics):
```
.model <mname> D Ron=<v> Roff=<v> Vfwd=<v> [Vrev=<v>] [Ilimit=<v>] [Revilimit=<v>]
+ [Epsilon=<v>] [Revepsilon=<v>]
```

**Standard SPICE semiconductor diode model** (key parameters):

| Param | Description | Default |
|-------|-------------|---------|
| Is | Saturation current | 1e-14 A |
| Rs | Series ohmic resistance | 0 Ω |
| N | Emission coefficient | 1 |
| Tt | Transit time | 0 |
| Cjo | Zero-bias junction capacitance | 0 F |
| Vj | Junction potential | 1 V |
| M | Grading coefficient | 0.5 |
| Eg | Activation energy | 1.11 eV |
| Xti | Saturation current temperature exponent | 3.0 |
| Kf | Flicker noise coefficient | 0 |
| Af | Flicker noise exponent | 1 |
| Fc | Forward-bias depletion capacitance coefficient | 0.5 |
| Bv | Reverse breakdown voltage | ∞ |
| Ibv | Current at Bv | 1e-10 A |
| Nbv | Reverse breakdown ideality factor | 1 |
| Ibvl | Low-level reverse breakdown current | 0 |
| Nbvl | Low-level breakdown ideality factor | 1 |
| Tbv1 | Bv linear temp coefficient | 0 |
| Trs1 | Rs linear temp coefficient | 0 |
| Trs2 | Rs quadratic temp coefficient | 0 |

`area`: scales Is, Cjo; `m=N`: N diodes in parallel; `n=N`: N diodes in series.

### Q — Bipolar Junction Transistor (BJT)

```
Qxxx C B E [Sub] <model> [area] [off] [temp=<T>]
```

- `Sub`: optional substrate node.
- `area`: scales currents and capacitances.

**Level 1 (Gummel-Poon) key parameters** (`.model <name> NPN|PNP`):

| Param | Description | Default |
|-------|-------------|---------|
| Is | Transport saturation current | 1e-16 A |
| Bf | Ideal max forward beta | 100 |
| Nf | Forward current emission coefficient | 1 |
| Vaf | Forward Early voltage | ∞ |
| Ikf | Corner for high-current beta rolloff | ∞ |
| Ise | B-E leakage saturation current | 0 |
| Ne | B-E leakage emission coefficient | 1.5 |
| Br | Ideal max reverse beta | 1 |
| Nr | Reverse current emission coefficient | 1 |
| Var | Reverse Early voltage | ∞ |
| Ikr | Corner for reverse high-current rolloff | ∞ |
| Isc | B-C leakage saturation current | 0 |
| Nc | B-C leakage emission coefficient | 2 |
| Rb | Zero-bias base resistance | 0 |
| Irb | Current at Rb/2 | ∞ |
| Rbm | Minimum base resistance | Rb |
| Re | Emitter resistance | 0 |
| Rc | Collector resistance | 0 |
| Cje | B-E zero-bias depletion capacitance | 0 |
| Vje | B-E built-in potential | 0.75 V |
| Mje | B-E junction grading factor | 0.33 |
| Tf | Ideal forward transit time | 0 |
| Xtf | Transit time bias dependence | 0 |
| Vtf | Transit time dependency on Vbc | ∞ |
| Itf | Transit time dependence on Ic | 0 |
| Ptf | Excess phase at 1/(2π*Tf) Hz | 0° |
| Cjc | B-C zero-bias depletion capacitance | 0 |
| Vjc | B-C built-in potential | 0.75 V |
| Mjc | B-C junction grading factor | 0.33 |
| Xcjc | Fraction of Cjc to internal base node | 1 |
| Tr | Ideal reverse transit time | 0 |
| Cjs | C-Sub zero-bias capacitance | 0 |
| Vjs | Substrate built-in potential | 0.75 V |
| Mjs | Substrate grading factor | 0 |
| Xtb | Forward/reverse beta temp exponent | 0 |
| Eg | Bandgap voltage | 1.11 eV |
| Xti | Is temperature exponent | 3 |
| Kf | Flicker noise coefficient | 0 |
| Af | Flicker noise exponent | 1 |
| Fc | Forward-bias depletion cap coefficient | 0.5 |
| Tnom | Parameter measurement temperature | 27°C |

**level=504**: MEXTRAM 504 model (separate parameter set, see vendor docs).
**level=9** or **level=4**: VBIC model.

### M — MOSFET

**Monolithic (4-terminal):**
```
Mxxx Nd Ng Ns Nb <model> [L=<v>] [W=<v>] [AD=<v>] [AS=<v>] [PD=<v>] [PS=<v>]
+ [NRD=<v>] [NRS=<v>] [off] [temp=<T>] [m=<N>]
```

**VDMOS (3-terminal power MOSFET):**
```
Mxxx Nd Ng Ns <model> [m=<N>] [off] [temp=<T>]
```

**Model level table:**

| Level | Model |
|-------|-------|
| 1 | Shichman-Hodges (default) |
| 2 | MOS2 (Groove) |
| 3 | MOS3 (empirical) |
| 4 | BSIM |
| 5 | BSIM2 |
| 6 | MOS6 |
| 7 | BSIM3v3.1 |
| 8 | BSIM3v3.2 |
| 9 | BSIMSOI |
| 12 | EKV 2.6 (bulk) |
| 14 | BSIM4 |
| 44 | EKV 2.6 (SOI) |
| 49 | BSIM3v3.3 |
| 54 | BSIM4 (alternate) |
| 55 | EKV 2.6 (extended) |
| 73 | HiSIM-HV |
| VDMOS | Vertical DMOS power model |

**Level 1-3 key parameters:**

| Param | Description | Default |
|-------|-------------|---------|
| VTO | Threshold voltage | 0 V |
| KP | Transconductance | 2e-5 A/V² |
| GAMMA | Bulk threshold parameter | 0 |
| PHI | Surface potential | 0.6 V |
| LAMBDA | Channel-length modulation | 0 |
| RD | Drain ohmic resistance | 0 |
| RS | Source ohmic resistance | 0 |
| CBD | B-D zero-bias capacitance | 0 |
| CBS | B-S zero-bias capacitance | 0 |
| IS | Bulk junction saturation current | 1e-14 A |
| PB | Bulk junction potential | 0.8 V |
| CGSO | Gate-Source overlap cap per W | 0 |
| CGDO | Gate-Drain overlap cap per W | 0 |
| CGBO | Gate-Bulk overlap cap per L | 0 |
| RSH | Sheet resistance | 0 |
| CJ | Zero-bias bulk cap per area | 0 |
| MJ | Bulk grading coefficient | 0.5 |
| CJSW | Sidewall cap per perimeter | 0 |
| MJSW | Sidewall grading | 0.5 |
| JS | Bulk saturation current density | 0 |
| TOX | Oxide thickness | ∞ |
| NSUB | Substrate doping | 0 |
| NSS | Surface state density | 0 |
| TPG | Gate material type | 1 |
| LD | Lateral diffusion | 0 |
| UO | Surface mobility | 600 cm²/V·s |
| UCRIT | Critical field (level 2) | 1e4 V/cm |
| UEXP | Critical field exponent (level 2) | 0 |
| UTRA | Transverse field mobility (level 2) | 0 |
| VMAX | Max drift velocity | 0 |
| NEFF | Total channel charge (level 2) | 1 |
| XJ | Metallurgical junction depth | 0 |
| NMOS | N-channel flag | — |
| PMOS | P-channel flag | — |

**Binning** (model selection by W and L): use `<basename>.1`, `<basename>.2`, etc., with `LMIN`/`LMAX`/`WMIN`/`WMAX` in each bin model.

**VDMOS key parameters:**

| Param | Description | Default |
|-------|-------------|---------|
| Kp | Transconductance | 0.2 A/V² |
| Vto | Threshold voltage | 2 V |
| Lambda | Channel-length modulation | 0 |
| Ksubthres | Subthreshold conduction | 100 mV/decade |
| Rd | Drain series resistance | 0 |
| Rs | Source series resistance | 0 |
| Rb | Body diode series resistance | 0 |
| Cgdmax | Max gate-drain capacitance | 0 |
| Cgdmin | Min gate-drain capacitance | 0 |
| Cgs | Gate-source capacitance | 0 |
| Cjo | Body diode zero-bias junction cap | 0 |
| Vj | Body diode junction potential | 0.5 V |
| M | Body diode grading coefficient | 0.5 |
| Is | Body diode saturation current | 1e-14 A |
| N | Body diode ideality factor | 1 |
| Tt | Body diode transit time | 0 |
| BVds | Drain-source breakdown voltage | ∞ |
| Vgs_max | Max gate-source voltage | ∞ |
| Vgd_max | Max gate-drain voltage | ∞ |
| Vds_max | Max drain-source voltage | ∞ |
| Id_max | Max drain current | ∞ |
| Iave | Max average current | ∞ |
| Ipk | Max peak current | ∞ |
| dVt | Threshold voltage temp coefficient | 0 V/°C |
| mu_exp | Mobility temperature exponent | 2.5 |

### J — JFET

```
Jxxx D G S <model> [area] [off] [temp=<T>]
.model <mname> NJF|PJF [params]
```

Key parameters:

| Param | Description | Default |
|-------|-------------|---------|
| Vto | Threshold voltage | -2 V |
| Beta | Transconductance | 1e-4 A/V² |
| Lambda | Channel-length modulation | 0 |
| Rd | Drain ohmic resistance | 0 |
| Rs | Source ohmic resistance | 0 |
| Cgs | Zero-bias G-S capacitance | 0 |
| Cgd | Zero-bias G-D capacitance | 0 |
| Pb | Gate junction potential | 1 V |
| m | Gate junction grading coefficient | 0.5 |
| Is | Gate junction saturation current | 1e-14 A |
| B | Doping tail parameter | 1 |
| Kf | Flicker noise coefficient | 0 |
| Af | Flicker noise exponent | 1 |
| Fc | Forward-bias depletion cap coefficient | 0.5 |
| Tnom | Parameter measurement temperature | 27°C |
| BetaTce | Beta temperature coefficient | 0 %/°C |
| VtoTc | Vto temperature coefficient | 0 V/°C |
| N | Gate junction emission coefficient | 1 |
| Isr | Recombination current | 0 |
| Nr | Recombination emission coefficient | 2 |
| alpha | Ionization coefficient | 0 |
| Vk | Ionization knee voltage | 0 |

### Z — MESFET and IGBT

**MESFET:**
```
Zxxx D G S <model> [area] [m=<v>] [off] [temp=<T>]
.model <mname> NMF|PMF [params]
```

Key MESFET parameters: `Vto`(-2V), `Beta`(1e-4), `B`(0.3/V), `Alpha`(2/V), `Lambda`(0), `Rd`, `Rs`, `Cgs`, `Cgd`, `Pb`(1V), `Kf`, `Af`, `Fc`, `Is`(1e-14).

**IGBT:**
```
Zxxx C G E <model> [area] [m=<v>] [off] [temp=<T>]
.model <mname> NIGBT|PIGBT [params]
```

Key IGBT parameters: `Agd`(5e-6 A/V²), `area`(1e-5 m²), `BVF`(1), `BVN`(4), `Cgs`(1.24e-8 F/cm²), `Coxd`(3.5e-8 F/cm²), `Jsne`(6.5e-13 A/cm²), `KF`(1), `KP`(0.38 A/V²), `MUN`(1500), `MUP`(450), `NB`(2e14 /cm³), `Tau`(7.1e-6 s), `Theta`(0.02 /V), `Vt`(4.7 V), `Vtd`(1e-3 V), `WB`(9e-5 m), `subthres`(0.02), `Kfn`, `Afn`, `tnom`(27°C).

### T — Lossless Transmission Line

```
Txxx L+ L- R+ R- Zo=<v> Td=<v> [Ic=<v>]
Txxx L+ L- R+ R- Zo=<v> F=<v> [NL=<v>]
```

- `Zo`: characteristic impedance (Ω).
- `Td`: one-way time delay (seconds).
- `F=<freq> NL=<v>`: specify frequency and normalized electrical length (NL=0.25 = quarter wave at F).
- No losses; use `O` (LTRA) element for lossy lines.

### X — Subcircuit Instance

```
Xxxx <n1> <n2> ... <subckt_name>|{<string_expr>} [<param>=<value> ...]
```

- Nodes listed before the subcircuit name (positional).
- String expression form: `{concat("nfet_",type)}` — evaluates to subcircuit name at simulation time.
- Parameters override defaults defined in `.subckt` header.
- Example:
  ```
  X1 in out gnd LDO VIN=3.3 VOUT=1.8
  .subckt LDO in out gnd params: VIN=5 VOUT=3.3
  ```

---

### @ — Frequency Response Analyzer (FRA Device)

Symbol name: `FRA`

```
@xxx in out [zm] fstart=<val> fend=<val> [delay=<val>] [oct=<val>] [fcoarse=<val>]
+ [nmax=<val>] [pp0=<val>] [pp1=<val>] [f0=<val>] [f1=<val>] [pp=<f v pairs>]
+ [tavgmin=<val>] [tsettle=<val>] [rpar=<val>] [flist=<values>]
+ [acmag=<val>] [acphase=<val>] [refnode=<netname>] [intnode=<netname>]
```

- Used with `.fra` directive. Applies sinusoidal stimuli from `fstart` to `fend` and measures circuit response.
- Default mode (no `zm`): **gain analysis** — applies voltage stimuli, measures V(in)/V(out).
- `zm` keyword: **impedance analysis** — applies current stimuli, measures V(in,out).
- `in` and `out` are the two terminals; positive current flows from `in` to `out` through the device's internal series element.

| Parameter | Description | Unit | Default |
|-----------|-------------|------|---------|
| `fstart` | Sweep start frequency | Hz | required |
| `fend` | Sweep end frequency | Hz | required |
| `delay` | Time before first stimulus | s | 0 |
| `oct` | Points per octave (0.25, 0.5, 1, 2, 3, 4) | — | 4 |
| `fcoarse` | Below this freq, use ≤1 pt/octave (saves time) | Hz | — |
| `nmax` | Max simultaneous harmonic injections (1–8+) | — | 1 |
| `pp0` | Stimulus amplitude for f ≤ f0 | V or A | 1 mV / 10 mA |
| `pp1` | Stimulus amplitude for f ≥ f1 | V or A | — |
| `f0` | Upper freq for pp0 amplitude | Hz | — |
| `f1` | Lower freq for pp1 amplitude | Hz | — |
| `pp` | Piecewise log amplitude: `"f0 a0 f1 a1 ..."` | Hz,V pairs | — |
| `tavgmin` | Min analysis time per frequency | s | 0 |
| `tsettle` | Settling time before analysis at each freq | s | 10/fend |
| `rpar` | Parallel resistance (shunt) | Ω | 1 mΩ / 1 TΩ |
| `acmag` | AC current magnitude (`.ac` sims only) | A | 0 |
| `acphase` | AC current phase (`.ac` sims only) | deg | 0 |
| `refnode` | Reference node for gain analysis (not impedance) | — | 0 |
| `intnode` | Intermediate node for additional gain trace | — | — |
| `enabled` | Enable/disable device (0 or 1) | — | 1 |

**Amplitude specification options:**
- `pp0` only: constant amplitude across all frequencies.
- `pp0 + pp1 + f0 + f1`: log-interpolated between (f0, pp0) and (f1, pp1) — recommended.
- `pp="f0 a0 f1 a1 ..."`: arbitrary piecewise-log profile.

**Tuning guidelines (SMPS):**
- `tavgmin = 100/fsw` (fsw = switching frequency)
- `tsettle = 2/fcross` (fcross = expected 0 dB crossover frequency); default `10/fend` if omitted
- `fcoarse = 2…10 × fstart` to skip slow low-freq points
- `nmax=2` is a good starting point for speed vs. accuracy

**Example:**
```
@1 A B delay=1m fstart=1k fend=500k oct=1 fcoarse=10k nmax=2 pp0=2m pp1=1m f0=1k f1=10k tavgmin=100u tsettle=200u
.fra
```

---

### & — Frequency Response Analysis Probe (FRAPROBE)

Symbol name: `FRAPROBE`

```
&xxx o+ o- i+ i-
```

- Used alongside a `@` FRA device during `.fra` simulation to measure gain between any two differential node pairs.
- Computes and records `V(o+, o-) / V(i+, i-)` vs. frequency as a complex quantity.
- No control parameters — all sweep parameters are taken from the associated `@` device.
- Output trace name: `probe_<fraprobe_instance>` in the FRA raw file.
- Association with `@` devices: `&1` pairs with `@1`, `&2` with `@2`, etc. (by instance number).

**Typical use cases:**
- Measuring modulator gain (compensation point to output)
- Differential or current-feedback loops
- Intermediate loop analysis in multi-loop SMPS

**Example:**
```
@1 FB GND fstart=100 fend=1Meg oct=2 pp0=10m tavgmin=500u
&1 vout 0 comp 0
.fra
```
Output: `probe_1` = V(vout)/V(comp) vs. frequency in `circuit.fra_1.raw`.

---

## 4. Voltage/Current Source Waveforms

All waveforms apply to both `V` and `I` sources (prefix `V` for voltage, `I` for current). Parameters in `[]` are optional.

### PULSE

```
PULSE(<Vinitial> <Vpulsed> [<Tdelay> [<Trise> [<Tfall> [<Ton> [<Tperiod> [<Ncycles>]]]]]])
```

| Param | Description | Default |
|-------|-------------|---------|
| Vinitial | Initial value | required |
| Vpulsed | Pulsed value | required |
| Tdelay | Delay before first transition | 0 |
| Trise | Rise time | TSTEP |
| Tfall | Fall time | TSTEP |
| Ton | Pulse width (on time) | TSTOP |
| Tperiod | Period | TSTOP |
| Ncycles | Number of cycles (0 = infinite) | 0 |

Example: `V1 a 0 PULSE(0 5 1n 1n 1n 50n 100n)`

### SINE

```
SINE(<Voffset> <Vamplitude> [<Freq> [<Tdelay> [<Theta> [<Phi> [<Ncycles>]]]]])
```

| Param | Description | Default |
|-------|-------------|---------|
| Voffset | DC offset | required |
| Vamplitude | Amplitude (peak) | required |
| Freq | Frequency (Hz) | 1/TSTOP |
| Tdelay | Time delay | 0 |
| Theta | Damping factor (1/s); positive = decay | 0 |
| Phi | Phase (degrees) | 0 |
| Ncycles | Number of cycles (0 = infinite) | 0 |

Formula: `V = Voffset + Vamplitude * exp(-Theta*(t-Tdelay)) * sin(2π*Freq*(t-Tdelay) + π*Phi/180)`

Before Tdelay: `V = Voffset + Vamplitude * sin(π*Phi/180)`

### EXP

```
EXP(<V1> <V2> [<Td1> [<Tau1> [<Td2> [<Tau2>]]]])
```

| Param | Description | Default |
|-------|-------------|---------|
| V1 | Initial value | required |
| V2 | Final value (peak) | required |
| Td1 | Rise delay | 0 |
| Tau1 | Rise time constant | TSTEP |
| Td2 | Fall delay | Td1+TSTEP |
| Tau2 | Fall time constant | TSTEP |

Formula:
- `t < Td1`: `V = V1`
- `Td1 ≤ t < Td2`: `V = V1 + (V2-V1)*(1 - exp(-(t-Td1)/Tau1))`
- `t ≥ Td2`: `V = V1 + (V2-V1)*(1 - exp(-(t-Td1)/Tau1)) + (V1-V2)*(1 - exp(-(t-Td2)/Tau2))`

### PWL — Piecewise Linear

```
PWL(<t1> <V1> [<t2> <V2> ...])
PWL REPEAT FOR <N> (<t1> <V1> [<t2> <V2> ...]) ENDREPEAT
PWL REPEAT FOREVER (<t1> <V1> [<t2> <V2> ...]) ENDREPEAT
PWL file=<filename> [REPEAT FOR <N>|FOREVER]
PWL SCOPEDATA=<signal_name>
```

- Time-value pairs define breakpoints; linearly interpolated between.
- `REPEAT FOR <N>`: repeat the sequence N times.
- `REPEAT FOREVER`: repeat indefinitely (period = last time point).
- `file=<filename>`: read (t, V) pairs from file (whitespace-separated, one pair per line or space-separated).
- `SCOPEDATA=`: use captured waveform data from LTspice waveform viewer.

### SFFM — Single-Frequency FM

```
SFFM(<Voffset> <Vamplitude> <Fcarrier> <ModIndex> <Fsignal> [<Tdelay>])
```

| Param | Description |
|-------|-------------|
| Voffset | DC offset |
| Vamplitude | Amplitude |
| Fcarrier | Carrier frequency (Hz) |
| ModIndex | Modulation index |
| Fsignal | Signal frequency (Hz) |
| Tdelay | Delay before waveform starts |

Formula: `V = Voffset + Vamplitude * sin(2π*Fcarrier*t + ModIndex*sin(2π*Fsignal*t))`

### AM — Amplitude Modulation

```
AM(<Vamplitude> <Voffset> <Fmodulation> <Fcarrier> [<Tdelay>])
```

| Param | Description |
|-------|-------------|
| Vamplitude | Modulation amplitude |
| Voffset | Carrier offset (bias) |
| Fmodulation | Modulation frequency (Hz) |
| Fcarrier | Carrier frequency (Hz) |
| Tdelay | Delay before waveform starts |

Formula: `V = Vamplitude * (Voffset + sin(2π*Fmodulation*(t-Tdelay))) * sin(2π*Fcarrier*(t-Tdelay))`

Before Tdelay: V = 0.

### wavefile

```
wavefile=<filename> [chan=<n>]
```

- Plays back a `.wav` audio file as a source waveform.
- `chan=<n>`: channel number (0-based) for multichannel files.

---

## 5. `.MODEL` and `.SUBCKT`

### `.MODEL` — Define a SPICE Model

```
.model <modname> <type>[(<parameter list>)]
.model <modname>|{<string_expr>} <type>[(<parameter list>)]
```

**Model types:**

| Type | Element |
|------|---------|
| SW | Voltage-controlled switch (S) |
| CSW | Current-controlled switch (W) |
| URC | Uniform distributed RC line (U) |
| LTRA | Lossy transmission line (O) |
| D | Diode |
| NPN | NPN BJT |
| PNP | PNP BJT |
| NJF | N-channel JFET |
| PJF | P-channel JFET |
| NMOS | N-channel MOSFET |
| PMOS | P-channel MOSFET |
| NMF | N-channel MESFET |
| PMF | P-channel MESFET |
| NIGBT | N-channel IGBT |
| PIGBT | P-channel IGBT |
| VDMOS | Vertical DMOS power MOSFET |

**AKO (A Kind Of) inheritance:**
```
.model <newname> ako:<basename> [<type>] [(<parameter overrides>)]
```
Example: `.model SLOW ako:NORMAL D(tt=10n)`
Creates a new model identical to the named base model, with specified parameters overridden. Type must match base if specified.

**Multiple models with same name** but different types are allowed (not recommended).

**String expression** for model name: `.model {concat("n",fet_type)} NMOS(...)` — evaluated at simulation time.

### `.SUBCKT` — Define a Subcircuit

```
.subckt <name> [<node1> <node2> ...] [params: <param1>=<default1> ...]
<circuit elements>
.ends [<name>]
```

- Node names in the `.subckt` header are **local** to the subcircuit.
- `params:` keyword introduces optional parameters with defaults.
- Parameters without defaults must be supplied at instantiation.
- Nested subcircuits are supported (unlimited depth).
- `.ends` (or `.ends <name>`) terminates the definition; `<name>` is optional but good practice.

**Example:**
```
.subckt MyFilter in out gnd params: Fc=1k Q=0.707
R1 in n1 {1/(2*pi*Fc*0.1u)}
C1 n1 gnd 0.1u
R2 n1 out {1/(2*pi*Fc*0.1u)}
C2 out gnd 0.1u
.ends MyFilter
```

**Instantiation:**
```
X1 vin vout 0 MyFilter Fc=10k Q=1
X2 va vb 0 MyFilter         * uses defaults Fc=1k Q=0.707
```

The simulator flattens all subcircuit instances into a single netlist before simulation. There is no limit on subcircuit size or complexity.

---

## 6. `.asc` Schematic File Format

**Source note:** The LTspice `.asc` format is not formally documented in the official LTspice help. The following is based on community documentation and reverse engineering. LTspice official help covers schematic editor *behavior* (what operations do) but not the file format itself. The format described here is accurate for LTspice XVII and LTspice 24 (current versions).

### File Structure Overview

`.asc` files are plain text (UTF-8 or ASCII). Each line is a record with a keyword followed by fields. Lines are terminated with `\r\n` (Windows CRLF) or `\n`.

```
Version 4
SHEET 1 <width> <height>
<records...>
```

**First two lines are always:**
```
Version 4
SHEET 1 880 680
```

`Version 4` is the current format version. `SHEET 1` is the sheet declaration; `<width>` and `<height>` are the sheet size in internal units (optional, can be omitted or use default 880×680).

### Coordinate System

- Origin (0,0) is at the **top-left** corner of the sheet.
- X increases **right**, Y increases **down**.
- Grid unit = **16 LTspice units** = 1 grid square.
- Standard component pin spacing = 16 units.
- Typical component body = 48×32 or 64×48 units.
- Wire connections must be on exact grid points (multiples of 16).
- Coordinates are signed 32-bit integers.

### Record Types

#### `WIRE` — Wire (net connection)

```
WIRE <x1> <y1> <x2> <y2>
```

- Draws a wire from (x1,y1) to (x2,y2).
- Only horizontal or vertical wires are allowed (x1==x2 or y1==y2).
- Wires that touch at their endpoints or overlap are connected.

#### `FLAG` — Net Label / Named Node

```
FLAG <x> <y> <name>
```

- Places a named net label at (x,y).
- Special names: `0` = ground; `GND` is also ground.
- Net labels with the same name on the same sheet are electrically connected.
- Example: `FLAG 240 128 VCC`

#### `WIRE` segments ending at a `FLAG` connect to that net name.

#### `SYMBOL` — Component Instance

```
SYMBOL <symbol_name> <x> <y> <rotation>
```

- `symbol_name`: path relative to the LTspice library, or just the symbol filename without extension. Absolute paths are also allowed.
- Examples: `res`, `cap`, `ind`, `nmos4`, `pnp`, `voltage`, `current`, `e`, `f`, `g`, `h`, `bv`, `bi`
- Standard library symbols are in `%LOCALAPPDATA%\Programs\ADI\LTspice\lib\sym\` (LTspice 24) or `C:\Program Files\LTC\LTspiceXVII\lib\sym\` (XVII).
- `<x> <y>`: position of the symbol's origin (anchor point, typically pin 1 or center).
- `<rotation>`: one of: `R0`, `R90`, `R180`, `R270`, `M0`, `M90`, `M180`, `M270`
  - `R0`=normal, `R90`=90° CCW, `R180`=180°, `R270`=270° CCW (= 90° CW).
  - `M0`=mirrored (horizontal flip), `M90`=mirrored+90°, etc.

**SYMBOL records are followed by SYMATTR records** that configure the instance.

#### `SYMATTR` — Symbol Attribute

```
SYMATTR <attribute_name> <value>
```

- Must immediately follow the `SYMBOL` line it belongs to (before the next `SYMBOL` or other block-level record).
- Common attributes:

| Attribute | Description |
|-----------|-------------|
| `InstName` | Instance name (e.g., `R1`, `C3`, `U1`) |
| `Value` | Primary value (resistance, capacitance, model name, etc.) |
| `Value2` | Secondary value (e.g., initial condition `IC=0`) |
| `SpiceModel` | SPICE model name (for subcircuit instances) |
| `SpiceLine` | Additional SPICE parameters appended to element line |
| `SpiceLine2` | Second additional SPICE parameter line |
| `Prefix` | Element type prefix (overrides symbol default); e.g., `X` for subcircuit |
| `ModelFile` | Path to `.lib`/`.sub` file containing the model |
| `Description` | Human-readable description (not used in simulation) |

**Standard component examples:**

Resistor:
```
SYMBOL res 240 160 R0
SYMATTR InstName R1
SYMATTR Value 10k
```

Capacitor with initial condition:
```
SYMBOL cap 320 160 R0
SYMATTR InstName C1
SYMATTR Value 100n
SYMATTR Value2 IC=5
```

Voltage source:
```
SYMBOL voltage 128 160 R0
SYMATTR InstName V1
SYMATTR Value PULSE(0 3.3 0 1n 1n 50n 100n)
```

Subcircuit instance (X prefix):
```
SYMBOL MyOpAmp 400 200 R0
SYMATTR Prefix X
SYMATTR InstName U1
SYMATTR SpiceModel LM358
SYMATTR ModelFile LM358.sub
```

NMOS with model:
```
SYMBOL nmos4 400 272 R0
SYMATTR InstName M1
SYMATTR Value BSS138
SYMATTR SpiceModel BSS138
SYMATTR ModelFile BSS138.lib
```

#### `TEXT` — SPICE Directive or Annotation

```
TEXT <x> <y> <alignment> <fontsize> <text>
```

or with type flag:

```
TEXT <x> <y> <alignment> <fontsize> !<spice_directive>
TEXT <x> <y> <alignment> <fontsize> ;<comment_text>
```

- `alignment`: `Left`, `Right`, `Center`, `Top`, `Bottom`, `VLeft`, `VRight`, `VCenter` (V prefix = vertical text).
- `fontsize`: integer 1–7 (typical default is 2).
- Text prefixed with `!` is a **SPICE directive** (included verbatim in the netlist): `!.tran 1m`, `!.param R=1k`, etc.
- Text prefixed with `;` is a **comment** (not included in netlist).
- Text with no prefix is a schematic annotation (not included in netlist; same effect as `;`).
- Newlines within text: use `\n` escape.

Examples:
```
TEXT 16 448 Left 2 !.tran 10m
TEXT 16 480 Left 2 !.op
TEXT 16 512 Left 2 ;This is a comment
TEXT 240 64 Left 2 My Test Circuit
```

#### `LINE` — Drawing Line (cosmetic only)

```
LINE Normal <x1> <y1> <x2> <y2>
```

- Cosmetic only; has no electrical significance.
- `Normal` is the line style (only `Normal` is common).

#### `RECTANGLE` — Drawing Rectangle (cosmetic)

```
RECTANGLE Normal <x1> <y1> <x2> <y2>
```

#### `CIRCLE` — Drawing Circle/Ellipse (cosmetic)

```
CIRCLE Normal <x1> <y1> <x2> <y2>
```

#### `ARC` — Drawing Arc (cosmetic)

```
ARC Normal <x1> <y1> <x2> <y2> <xstart> <ystart> <xend> <yend>
```

#### `IOPIN` — I/O Pin (for symbols, not top-level schematics)

```
IOPIN <x> <y> <direction> <name>
```

- Used in `.asy` symbol files, not typically in `.asc` circuit schematics.
- `direction`: `In`, `Out`, `BiDir`.

#### `PIN` — Pin Definition (in `.asy` symbol files)

```
PIN <x> <y> <rotation> <length>
PINATTR PinName <name>
PINATTR SpiceOrder <N>
```

- Defines a pin in a symbol file (`.asy`).
- `SpiceOrder` determines the order of nodes in the SPICE element line.

### `.lib` / `.inc` Include Directives

Use `TEXT` records with SPICE directives:
```
TEXT 16 528 Left 2 !.lib models.lib
TEXT 16 544 Left 2 !.inc custom.sub
```

These are placed as `.lib` and `.include` lines in the generated netlist.

### Complete Minimal `.asc` Example

Simple RC circuit with transient analysis:

```
Version 4
SHEET 1 880 680
WIRE 128 160 80 160
WIRE 256 160 208 160
WIRE 256 160 256 208
WIRE 256 304 256 256
WIRE 80 304 80 160
WIRE 80 304 256 304
FLAG 80 160 in
FLAG 256 160 out
FLAG 256 304 0
SYMBOL voltage 80 176 R180
SYMATTR InstName V1
SYMATTR Value PULSE(0 1 0 1n 1n 500n 1u)
SYMBOL res 224 144 R90
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL cap 240 208 R0
SYMATTR InstName C1
SYMATTR Value 100n
TEXT 16 448 Left 2 !.tran 10u
TEXT 16 464 Left 2 !.backanno
TEXT 16 480 Left 2 ;Simple RC low-pass filter
```

### Symbol Rotation Reference

| Code | Description | Transform |
|------|-------------|-----------|
| R0 | Normal (0°) | Identity |
| R90 | 90° CCW | x'=-y, y'=x |
| R180 | 180° | x'=-x, y'=-y |
| R270 | 270° CCW (90° CW) | x'=y, y'=-x |
| M0 | Mirror horizontal | x'=-x, y'=y |
| M90 | Mirror + 90° CCW | x'=y, y'=x |
| M180 | Mirror + 180° | x'=x, y'=-y |
| M270 | Mirror + 270° CCW | x'=-y, y'=-x |

Rotation applies around the symbol's anchor point.

### Common Symbol Names (LTspice Standard Library)

| Symbol | Element |
|--------|---------|
| `res` | Resistor (R) |
| `cap` | Capacitor (C) |
| `ind` | Inductor (L) |
| `ind2` | Inductor with dot notation |
| `voltage` | Voltage source (V) |
| `current` | Current source (I) |
| `e` | VCVS (E) |
| `f` | CCCS (F) |
| `g` | VCCS (G) |
| `h` | CCVS (H) |
| `bv` | Behavioral voltage source (B, V=) |
| `bi` | Behavioral current source (B, I=) |
| `bi2` | Bidirectional behavioral source |
| `diode` | Diode (D) |
| `npn` | NPN BJT (Q) |
| `pnp` | PNP BJT (Q) |
| `nmos` | N-channel MOSFET 3-terminal |
| `nmos4` | N-channel MOSFET 4-terminal |
| `pmos` | P-channel MOSFET 3-terminal |
| `pmos4` | P-channel MOSFET 4-terminal |
| `njf` | N-channel JFET |
| `pjf` | P-channel JFET |
| `zener` | Zener diode (D) |
| `schottky` | Schottky diode (D) |
| `sw` | Voltage-controlled switch (S) |
| `csw` | Current-controlled switch (W) |
| `tline` | Lossless transmission line (T) |
| `load` | Current load symbol |
| `gnd` | Ground (FLAG 0) |
| `com` | Common/earth ground |
| `vcc`, `vdd`, `vee`, `vss` | Power rail flags |

### `.asy` Symbol File Format

Symbol files (`.asy`) define component appearances. Structure:

```
Version 4
SymbolType CELL|BLOCK|PINFLAG
LINE Normal <x1> <y1> <x2> <y2>
...
PIN <x> <y> <rotation> <length>
PINATTR PinName <name>
PINATTR SpiceOrder <N>
...
TEXT <x> <y> <alignment> <size> <text>
WINDOW <attr_id> <x> <y> <alignment> <size>
SYMATTR <attr> <default_value>
```

- `WINDOW <n>`: defines display position of attribute `n` on schematic.
  - Window 0: component value
  - Window 3: instance name
  - Window 39: SPICE model
- `SymbolType CELL`: standard component; `BLOCK`: hierarchical block; `PINFLAG`: a flag/power symbol.

### Hierarchical Schematics

For hierarchical designs, a block in the parent schematic references a `.asc` file:

```
SYMBOL <child_schematic_name> <x> <y> <rotation>
SYMATTR InstName X1
```

The child `.asc` file must have matching port names defined with `FLAG` + `IOPIN` combinations or net labels at the boundary.

### Key Rules for Writing Valid `.asc` Files

1. Always start with `Version 4` then `SHEET 1`.
2. All coordinates must be integers; prefer multiples of 16 for proper grid alignment.
3. `SYMATTR` records must directly follow their `SYMBOL` record.
4. Every `SYMBOL` must have at minimum `InstName` and `Value` `SYMATTR` records (for passive/active elements).
5. Ground nodes: use `FLAG <x> <y> 0` (not "GND" — though both work as net names).
6. Net connections: wires connect at endpoints. Two wires connecting at a T-junction are connected. Wire crossing without a node dot are **not** connected.
7. SPICE directives (`.tran`, `.ac`, `.param`, etc.) go in `TEXT` records with `!` prefix.
8. The LTspice-generated netlist from a `.asc` file always includes `.backanno` at the end.
9. For subcircuit instances, set `SYMATTR Prefix X` and use `SYMATTR SpiceModel <name>` for the subcircuit name.
10. `ModelFile` attribute causes LTspice to auto-include the referenced `.lib`/`.sub` file.
