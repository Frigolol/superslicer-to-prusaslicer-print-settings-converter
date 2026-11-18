# SuperSlicer to PrusaSlicer print settings converter

Convert a **SuperSlicer print profile** (`.ini`) into a **PrusaSlicer 2.9** print profile, with a report explaining every setting: what was copied, what was converted, what has no equivalent.

---

## Features

- Produces a complete PrusaSlicer 2.9.x print profile (every print key PrusaSlicer expects, nothing extra).
- Converts semantics, not just names:
  - extrusion widths in `%` of nozzle → absolute mm
  - `bridge_flow_ratio` `80%` → `0.8`
  - `first_layer_size_compensation` (negative) → `elefant_foot_compensation` (positive)
  - SuperSlicer fill patterns (`monotonicgapfill`, …) → closest PrusaSlicer pattern
  - disabled values (`!0`) → PrusaSlicer equivalent (auto, `-1`, …)
  - `only_one_perimeter_top` → `top_one_perimeter_type`, `bridge_type` → `thick_bridges`, `overhangs_width` → `overhangs`, …
- Writes a Markdown report next to the profile, grouping settings by status:

  | status | meaning |
  |---|---|
  | `doubt` | converted, but worth checking |
  | `override` | value forced by your overrides file |
  | `converted` | converted (unit / name / semantics) |
  | `default` | PrusaSlicer-only setting, PrusaSlicer default used |
  | `ignored` | SuperSlicer setting with no PrusaSlicer equivalent |
  | `direct` | same name, same meaning, copied as is |

- **Overrides file**: force your own values (e.g. `gcode_label_objects = firmware` for Klipper) on every conversion.
- Windows `.exe` with a small window, drag-and-drop, and a command-line mode.

Only **print settings** are handled for now (not filament or printer settings).

## Download

Get `ss2ps.exe` from the [Releases](../../releases) page. No installation, no Python needed.

## Usage

### Window

1. Double-click `ss2ps.exe` (or drag a SuperSlicer `.ini` onto it).
2. Pick the SuperSlicer print profile — the dialog opens in `%APPDATA%\SuperSlicer\print`.
3. Check the nozzle diameter (used to turn `%` widths into mm).
4. Optional: pick an overrides file.
5. Click **Convert**.

By default the profile is written straight into `%APPDATA%\PrusaSlicer\print` as `<name> (PS).ini`, next to its report `<name> (PS) - report.md`. Restart PrusaSlicer and pick the profile in the print settings list.

### Command line

```
ss2ps.exe "<SuperSlicer profile>.ini" [-o out.ini] [--nozzle 0.4] [--overrides my_overrides.ini] [--no-overrides]
```

or with Python 3.8+ (no dependencies):

```
python ss2ps.py "<SuperSlicer profile>.ini" --nozzle 0.4
```

| option | default |
|---|---|
| `-o`, `--out` | `%APPDATA%\PrusaSlicer\print\<name> (PS).ini` (or next to the source if PrusaSlicer isn't installed) |
| `--nozzle` | `0.4` |
| `--overrides` | `overrides.ini` next to the exe / script, if present |
| `--no-overrides` | ignore `overrides.ini` |

## Overrides

Some differences are not a matter of conversion but of preference (for example, PrusaSlicer applies `small_perimeter_speed` to *every* small perimeter, whereas SuperSlicer ramps it between two lengths). Put your choices in an overrides file:

```ini
# Klipper: exclude objects through the firmware
gcode_label_objects = firmware

# 10 mm/s is too slow in PrusaSlicer
small_perimeter_speed = 50
```

- one `prusaslicer_key = value` per line;
- the `#` comment directly above a line is copied to the report as the reason;
- name it `overrides.ini` and place it next to `ss2ps.exe` / `ss2ps.py` to apply it automatically.

See [`overrides.example.ini`](overrides.example.ini).

## Build the exe yourself

```
pip install pyinstaller
build.bat
```

The exe is created in `dist\ss2ps.exe`.

## Limitations

- Target: PrusaSlicer 2.9.x print settings, source: SuperSlicer 2.5–2.7.
- Many SuperSlicer-only features (`infill_connection`, `perimeter_direction`, `gap_fill_*` details, seam costs, per-feature accelerations, milling, …) have no PrusaSlicer equivalent and are listed as `ignored` in the report.
- Always read the `doubt` section of the report and test-print before relying on a converted profile.

Issues and pull requests with more mappings are welcome.

## License

[MIT](LICENSE)

