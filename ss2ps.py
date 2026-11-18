"""ss2ps - converts a SuperSlicer print profile (.ini) into a PrusaSlicer print profile (.ini).

Usage:
    ss2ps                                   -> opens the window
    ss2ps <superslicer_print.ini>           -> window pre-filled (also by drag-and-drop onto the exe)
    ss2ps <src.ini> [-o out.ini] [--nozzle 0.4] [--overrides overrides.ini] [-y] [-f]

Output:
    - the PrusaSlicer .ini (every PrusaSlicer 2.9.x print key)
    - a .md report listing: conversions, doubts, defaults, ignored SuperSlicer keys
"""
import argparse
import datetime
import os
import sys

__version__ = "1.2.0"

# ---------------------------------------------------------------------------
# PrusaSlicer 2.9.x defaults for keys that have NO SuperSlicer equivalent.
# Every PrusaSlicer 2.9.6 print key is either here or produced by Converter.run().
# ---------------------------------------------------------------------------
PRUSA_ONLY_DEFAULTS = {
    "arc_fitting": "disabled",
    "automatic_extrusion_widths": "0",
    "automatic_infill_combination": "0",
    "automatic_infill_combination_max_layer_height": "100%",
    "bed_temperature_extruder": "0",
    "brim_type": "outer_only",
    "custom_parameters_print": "",
    "enable_dynamic_overhang_speeds": "0",
    "gcode_resolution": "0.0125",
    "interlocking_beam": "0",
    "interlocking_beam_layer_count": "2",
    "interlocking_beam_width": "0.8",
    "interlocking_boundary_avoidance": "2",
    "interlocking_depth": "2",
    "interlocking_orientation": "22.5",
    "overhang_speed_0": "15",
    "overhang_speed_1": "15",
    "overhang_speed_2": "20",
    "overhang_speed_3": "25",
    "scarf_seam_entire_loop": "0",
    "scarf_seam_length": "20",
    "scarf_seam_max_segment_length": "1",
    "scarf_seam_on_inner_perimeters": "0",
    "scarf_seam_only_on_smooth": "1",
    "scarf_seam_placement": "nowhere",
    "scarf_seam_start_height": "0%",
    "seam_gap_distance": "15%",
    "toolchange_ordering": "optimized",
    "travel_short_distance_acceleration": "250",
    "wipe_tower_acceleration": "0",
    "wipe_tower_extra_flow": "100%",
}

# Keys whose name AND meaning are identical in both slicers.
DIRECT_KEYS = [
    "avoid_crossing_curled_overhangs", "avoid_crossing_perimeters",
    "avoid_crossing_perimeters_max_detour", "bottom_solid_layers",
    "bottom_solid_min_thickness", "bridge_acceleration", "bridge_speed",
    "brim_separation", "brim_width", "compatible_printers",
    "compatible_printers_condition", "complete_objects", "default_acceleration",
    "dont_support_bridges", "draft_shield", "external_perimeter_acceleration",
    "external_perimeter_speed", "external_perimeters_first", "extra_perimeters",
    "extra_perimeters_on_overhangs", "fill_angle", "fill_density", "fill_pattern",
    "first_layer_acceleration", "first_layer_acceleration_over_raft",
    "first_layer_height", "first_layer_infill_speed", "first_layer_speed",
    "first_layer_speed_over_raft", "fuzzy_skin", "gap_fill_enabled",
    "gap_fill_speed", "gcode_comments", "gcode_label_objects",
    "gcode_substitutions", "infill_acceleration", "infill_anchor",
    "infill_anchor_max", "infill_every_layers", "infill_extruder", "infill_first",
    "infill_overlap", "infill_speed", "inherits", "interface_shells", "ironing",
    "ironing_flowrate", "ironing_spacing", "ironing_speed", "ironing_type",
    "layer_height", "max_print_speed",
    "max_volumetric_extrusion_rate_slope_negative",
    "max_volumetric_extrusion_rate_slope_positive", "max_volumetric_speed",
    "min_bead_width", "min_feature_size", "min_skirt_length",
    "mmu_segmented_region_interlocking_depth", "mmu_segmented_region_max_width",
    "notes", "only_one_perimeter_first_layer",
    "only_retract_when_crossing_perimeters", "ooze_prevention",
    "output_filename_format", "perimeter_acceleration", "perimeter_extruder",
    "perimeter_generator", "perimeter_speed", "perimeters", "post_process",
    "raft_contact_distance", "raft_expansion", "raft_first_layer_density",
    "raft_first_layer_expansion", "raft_layers", "seam_position",
    "single_extruder_multi_material_priming", "skirt_distance", "skirt_height",
    "skirts", "slice_closing_radius", "slicing_mode", "small_perimeter_speed",
    "solid_infill_acceleration", "solid_infill_below_area",
    "solid_infill_every_layers", "solid_infill_extruder", "solid_infill_speed",
    "spiral_vase", "staggered_inner_seams", "standby_temperature_delta",
    "support_material", "support_material_angle", "support_material_auto",
    "support_material_buildplate_only", "support_material_closing_radius",
    "support_material_enforce_layers", "support_material_extruder",
    "support_material_interface_contact_loops",
    "support_material_interface_extruder", "support_material_interface_layers",
    "support_material_interface_spacing", "support_material_interface_speed",
    "support_material_pattern", "support_material_spacing",
    "support_material_speed", "support_material_style",
    "support_material_synchronize_layers", "support_material_threshold",
    "support_material_with_sheath", "support_material_xy_spacing",
    "support_tree_angle", "support_tree_angle_slow", "support_tree_branch_diameter",
    "support_tree_branch_diameter_angle", "support_tree_branch_diameter_double_wall",
    "support_tree_branch_distance", "support_tree_tip_diameter",
    "support_tree_top_rate", "thin_walls", "top_solid_infill_acceleration",
    "top_solid_infill_speed", "top_solid_layers", "top_solid_min_thickness",
    "travel_acceleration", "travel_speed", "travel_speed_z",
    "wall_distribution_count", "wall_transition_angle",
    "wall_transition_filter_deviation", "wall_transition_length", "wipe_tower",
    "wipe_tower_bridging", "wipe_tower_brim_width", "wipe_tower_cone_angle",
    "wipe_tower_extra_spacing", "wipe_tower_extruder",
    "wipe_tower_no_sparse_layers", "wipe_tower_width", "xy_size_compensation",
]

# Extrusion widths: SuperSlicer % (of nozzle) -> absolute mm.
WIDTH_KEYS = {
    # PrusaSlicer key: SuperSlicer key
    "extrusion_width": "extrusion_width",
    "external_perimeter_extrusion_width": "external_perimeter_extrusion_width",
    "perimeter_extrusion_width": "perimeter_extrusion_width",
    "infill_extrusion_width": "infill_extrusion_width",
    "solid_infill_extrusion_width": "solid_infill_extrusion_width",
    "top_infill_extrusion_width": "top_infill_extrusion_width",
    "first_layer_extrusion_width": "first_layer_extrusion_width",
    "support_material_extrusion_width": "support_material_extrusion_width",
}


FILL_PATTERN_MAP = {
    # SuperSlicer -> PrusaSlicer
    "monotonicgapfill": "monotoniclines",
    "rectilineargapfill": "rectilinear",
    "concentricgapfill": "concentric",
    "smooth": "monotonic",
    "smoothtriple": "monotonic",
    "smoothhilbert": "monotonic",
    "sawtooth": "rectilinear",
    "rectiwithperimeter": "rectilinear",
    "scatteredrectilinear": "rectilinear",
}
PRUSA_TOP_BOTTOM_PATTERNS = {"rectilinear", "monotonic", "monotoniclines", "alignedrectilinear",
                             "concentric", "hilbertcurve", "archimedeanchords", "octagramspiral"}


class Converter:
    def __init__(self, ss, nozzle, overrides=None):
        self.ss = ss
        self.nozzle = nozzle
        self.overrides = overrides or {}
        self.used = set()          # SuperSlicer keys consumed
        self.out = {}              # PrusaSlicer key -> value
        self.log = []              # (status, PrusaSlicer key, value, note)
        self.doubts = []           # [{key, value, options, note}] to be confirmed by the user

    # -- helpers --------------------------------------------------------------
    def get(self, key, default=None):
        self.used.add(key)
        return self.ss.get(key, default)

    @staticmethod
    def disabled(v):
        return v is not None and v.startswith("!")

    def width_mm(self, v):
        """SuperSlicer: % = percentage of nozzle diameter. Returns absolute mm."""
        if v is None or v == "" or self.disabled(v):
            return "0"
        if v.endswith("%"):
            return fmt(float(v[:-1]) / 100 * self.nozzle)
        return v

    def set(self, key, value, status="direct", note=""):
        self.out[key] = value
        self.log.append((status, key, value, note))

    def doubt(self, key, value, options, note, closed=False):
        """Proposed value the user should confirm. `options` = suggested alternatives.
        closed=True: only the listed options are valid; otherwise any number is accepted."""
        opts = [value] + [o for o in options if o != value]
        self.set(key, value, "doubt", note)
        self.doubts.append({"key": key, "value": value, "options": opts, "note": note, "closed": closed})

    def apply_choices(self, choices):
        """Applies the user's answers to the doubts: {key: value}."""
        for d in self.doubts:
            v = choices.get(d["key"], d["value"]).strip()
            if v == d["value"]:
                continue
            self.out[d["key"]] = v
            self.log = [(st, k, v, f"{n} -- user chose `{v}` (proposed `{d['value']}`)")
                        if st == "doubt" and k == d["key"] else (st, k, val, n)
                        for st, k, val, n in self.log]

    # -- conversion -------------------------------------------------------------
    def run(self):
        g = self.get

        for k in DIRECT_KEYS:
            if k in self.ss:
                v = g(k)
                if self.disabled(v):
                    self.doubt(k, v[1:], [], f"value disabled in SuperSlicer (`{v}`), copied as is")
                else:
                    self.set(k, v)

        # Extrusion widths: % of nozzle -> mm
        for pk, sk in WIDTH_KEYS.items():
            v = g(sk, "")
            mm = self.width_mm(v)
            self.set(pk, mm, "converted",
                     f"SS `{v}` -> {mm} mm (nozzle {self.nozzle} mm)" if v else "SS empty = auto -> 0 (auto)")
        g("first_layer_infill_extrusion_width")  # no equivalent
        for k in ("external_perimeter_extrusion_spacing", "perimeter_extrusion_spacing",
                  "infill_extrusion_spacing", "solid_infill_extrusion_spacing",
                  "top_infill_extrusion_spacing", "first_layer_extrusion_spacing",
                  "first_layer_infill_extrusion_spacing", "extrusion_spacing"):
            g(k)  # spacing = SuperSlicer's alternative form of width, redundant

        # Bridge flow: 80% -> 0.8
        v = g("bridge_flow_ratio", "100%")
        r = fmt(float(v.rstrip("%")) / 100) if v.endswith("%") else v
        self.set("bridge_flow_ratio", r, "converted", f"`{v}` -> ratio {r}")

        # Thick bridges
        bt = g("bridge_type", "nozzle")
        self.set("thick_bridges", "1" if bt == "nozzle" else "0", "converted",
                 f"bridge_type=`{bt}`: 'nozzle' (nozzle-diameter bridges) ~ thick_bridges=1 in PrusaSlicer")

        # Bridge angle
        v = g("bridge_angle", "0")
        self.set("bridge_angle", "0" if self.disabled(v) else v, "converted",
                 f"`{v}` -> disabled = 0 (auto)" if self.disabled(v) else "")

        # Top / bottom patterns
        for k in ("top_fill_pattern", "bottom_fill_pattern"):
            v = g(k, "monotonic")
            nv = FILL_PATTERN_MAP.get(v, v)
            if nv not in PRUSA_TOP_BOTTOM_PATTERNS:
                self.doubt(k, "monotoniclines", sorted(PRUSA_TOP_BOTTOM_PATTERNS),
                           f"unknown SuperSlicer pattern `{v}`", closed=True)
                continue
            st = "direct" if nv == v else "converted"
            self.set(k, nv, st, "" if nv == v else f"`{v}` does not exist in PrusaSlicer -> `{nv}`")
        v = g("solid_fill_pattern")
        if v:
            self.log.append(("ignored", "solid_fill_pattern", v,
                             "PrusaSlicer has no pattern setting for internal solid infill"))

        # Vertical shell
        v = g("ensure_vertical_shell_thickness", "enabled")
        m = {"enabled_old": "enabled", "enabled": "enabled", "partial": "partial",
             "disabled": "disabled", "1": "enabled", "0": "disabled"}
        if v in ("enabled", "partial", "disabled"):
            self.set("ensure_vertical_shell_thickness", v)
        else:
            self.doubt("ensure_vertical_shell_thickness", m.get(v, "enabled"), ["enabled", "partial", "disabled"],
                       f"`{v}` has no exact PrusaSlicer equivalent (partial = PrusaSlicer default, lighter)",
                       closed=True)

        # Elephant foot compensation
        v = g("first_layer_size_compensation", "0")
        g("first_layer_size_compensation_layers"); g("first_layer_size_compensation_no_collapse")
        efc = fmt(abs(float(v))) if float(v) <= 0 else "0"
        self.set("elefant_foot_compensation", efc, "converted",
                 f"first_layer_size_compensation `{v}` -> elefant_foot_compensation {efc} (sign inverted)")

        # Resolution
        v = g("resolution", "0")
        self.doubt("resolution", v, ["0"], "slice simplification copied as is (0 = no simplification, PrusaSlicer default)")
        g("resolution_internal")

        # Single perimeter on top surfaces
        v = g("only_one_perimeter_top", "0")
        g("only_one_perimeter_top_other_algo")
        self.set("top_one_perimeter_type", "top" if v == "1" else "none", "converted",
                 f"only_one_perimeter_top={v} -> {'top (all top surfaces)' if v == '1' else 'none'}")

        # Overhangs
        ow = g("overhangs_width", "75%")
        g("overhangs_width_speed"); g("overhangs_dynamic_speed"); g("overhangs_speed")
        g("overhangs_speed_enforce"); g("overhangs_bridge_threshold"); g("overhangs_bridge_upper_layers")
        g("overhangs_max_slope"); g("overhangs_reverse"); g("overhangs_reverse_threshold")
        on = "0" if self.disabled(ow) or ow in ("0", "0%") else "1"
        self.set("overhangs", on, "converted",
                 f"overhangs_width=`{ow}` -> overhang perimeter detection {'enabled' if on == '1' else 'disabled'}")

        # Speed over internal bridges
        v = g("internal_bridge_speed", "100%")
        self.set("over_bridge_speed", v, "converted",
                 f"internal_bridge_speed `{v}` -> over_bridge_speed")
        g("over_bridge_flow_ratio")

        # Supports
        v = g("support_material_contact_distance", "0.2")
        g("support_material_contact_distance_type")
        self.set("support_material_contact_distance", v)
        v = g("support_material_bottom_contact_distance", "0")
        self.set("support_material_bottom_contact_distance", v)
        v = g("support_material_bottom_interface_layers", "-1")
        self.set("support_material_bottom_interface_layers", "-1" if self.disabled(v) else v, "converted",
                 f"`{v}` disabled -> -1 (same as top)" if self.disabled(v) else "")
        v = g("support_material_top_interface_pattern", "rectilinear")
        g("support_material_bottom_interface_pattern")
        self.set("support_material_interface_pattern", v, "converted", "from support_material_top_interface_pattern")

        # Fuzzy skin : % -> mm
        for k in ("fuzzy_skin_point_dist", "fuzzy_skin_thickness"):
            v = g(k, "0.3")
            mm = self.width_mm(v)
            self.set(k, mm, "converted", f"`{v}` -> {mm} mm")

        # print_custom_variables: not transferred (listed as ignored)

        # User overrides
        for k, (v, why) in self.overrides.items():
            old = self.out.get(k)
            self.log = [r for r in self.log if not (r[0] == "doubt" and r[1] == k)]
            self.set(k, v, "override", f"{old} -> {v}: {why}")
        self.doubts = [d for d in self.doubts if d["key"] not in self.overrides]

        # Keys with no equivalent: PrusaSlicer defaults
        for k, v in PRUSA_ONLY_DEFAULTS.items():
            if k not in self.out:
                self.set(k, v, "default", "no SuperSlicer equivalent, PrusaSlicer default")

        self.set("print_settings_id", "")
        g("print_settings_id"); g("print_version")

        # SuperSlicer keys not consumed = ignored
        for k in sorted(self.ss):
            if k not in self.used:
                self.log.append(("ignored", k, self.ss[k], "no PrusaSlicer equivalent"))
        return self.out


def fmt(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def parse_ini(path):
    data = {}
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#") or " = " not in line and not line.endswith(" ="):
                continue
            k, _, v = line.partition(" =")
            data[k.strip()] = v[1:] if v.startswith(" ") else v
    return data


def parse_overrides(path):
    """Overrides file: `key = value`. The `# ...` comment right above a line is used as the reason."""
    res, why = {}, ""
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                why = ""
            elif line.startswith("#"):
                why = line.lstrip("# ").strip()
            elif "=" in line:
                k, _, v = line.partition("=")
                res[k.strip()] = (v.strip(), why or "user override")
                why = ""
    return res


def app_dir():
    """Folder of the exe (PyInstaller) or of the script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def default_overrides_path():
    p = os.path.join(app_dir(), "overrides.ini")
    return p if os.path.isfile(p) else None


def prusa_print_dir():
    p = os.path.join(os.environ.get("APPDATA", ""), "PrusaSlicer", "print")
    return p if os.path.isdir(p) else None


def superslicer_print_dir():
    p = os.path.join(os.environ.get("APPDATA", ""), "SuperSlicer", "print")
    return p if os.path.isdir(p) else None


REPORT_ORDER = ["doubt", "override", "converted", "default", "ignored", "direct"]


def valid_choice(d, v):
    """True if `v` is an acceptable answer for doubt `d`."""
    if d["closed"]:
        return v in d["options"]
    try:
        float(v.rstrip("%"))
        return True
    except ValueError:
        return v in d["options"]


def output_path_for(src, out_dir=None):
    base = os.path.splitext(os.path.basename(src))[0]
    out_dir = out_dir or prusa_print_dir() or os.path.dirname(os.path.abspath(src))
    return os.path.join(out_dir, f"{base}.ini")


def prepare(src, nozzle=0.4, overrides_path=None):
    """Parses and converts `src`. Returns the Converter (its `doubts` still to be confirmed)."""
    ss = parse_ini(src)
    if "perimeters" not in ss or "layer_height" not in ss:
        raise ValueError(f"{os.path.basename(src)} does not look like a SuperSlicer print profile")
    overrides = parse_overrides(overrides_path) if overrides_path else {}
    conv = Converter(ss, nozzle, overrides)
    conv.run()
    conv.src, conv.overrides_path = src, overrides_path
    return conv


def write(conv, out_path):
    """Writes the PrusaSlicer profile and its report. Returns (ini path, report path, counts per status)."""
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# converted from SuperSlicer by ss2ps {__version__} on {datetime.datetime.now():%Y-%m-%d %H:%M}\n")
        for k in sorted(conv.out):
            f.write(f"{k} = {conv.out[k]}\n")

    rep_path = os.path.splitext(out_path)[0] + " - report.md"
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(f"# Conversion report: {os.path.basename(conv.src)}\n\n"
                f"Nozzle: {conv.nozzle} mm  \nOverrides: {conv.overrides_path or 'none'}\n")
        for st in REPORT_ORDER:
            rows = [r for r in conv.log if r[0] == st]
            if not rows:
                continue
            f.write(f"\n## {st} ({len(rows)})\n\n| key | value | note |\n|---|---|---|\n")
            for _, k, v, n in rows:
                f.write(f"| {k} | `{v}` | {n} |\n")

    counts = {st: sum(1 for r in conv.log if r[0] == st) for st in REPORT_ORDER}
    return out_path, rep_path, counts


def convert_file(src, out_path=None, nozzle=0.4, overrides_path=None, ask=None):
    """Full conversion. `ask(doubts) -> {key: value}` lets the user settle the doubts (None = keep proposals)."""
    conv = prepare(src, nozzle, overrides_path)
    if ask and conv.doubts:
        conv.apply_choices(ask(conv.doubts))
    return write(conv, out_path or output_path_for(src))


def ask_console(doubts):
    """Asks each doubt in the terminal. Enter = keep the proposed value."""
    print(f"\n{len(doubts)} setting(s) need your confirmation (Enter = keep proposed value):")
    res = {}
    for d in doubts:
        print(f"\n  {d['key']}: {d['note']}")
        print("    options: " + ", ".join(d["options"]))
        while True:
            a = input(f"    value [{d['value']}]: ").strip() or d["value"]
            if valid_choice(d, a):
                break
            print("    invalid value, choose one of the options" if d["closed"] else "    a number is expected")
        res[d["key"]] = a
    print()
    return res


def summary(out_path, rep_path, counts):
    c = ", ".join(f"{k}: {v}" for k, v in counts.items())
    return f"PrusaSlicer profile:\n{out_path}\n\nReport:\n{rep_path}\n\n{c}"


# ---------------------------------------------------------------------------
# Graphical interface (tkinter)
# ---------------------------------------------------------------------------
def ask_gui(root, doubts):
    """Modal window: one editable drop-down per doubt. Returns {key: value}, or None if cancelled."""
    import tkinter as tk
    from tkinter import ttk

    win = tk.Toplevel(root)
    win.title("Please confirm these settings")
    win.transient(root)
    win.grab_set()
    frm = ttk.Frame(win, padding=12)
    frm.grid(sticky="nsew")
    ttk.Label(frm, text="These settings could not be converted with certainty.\n"
                        "Keep the proposed value or choose another one (you can also type a value).",
              justify="left").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
    for c, t in enumerate(("Setting", "Value", "Why")):
        ttk.Label(frm, text=t, font=("", 9, "bold")).grid(row=1, column=c, sticky="w", padx=(0, 8))
    vars_ = {}
    for i, d in enumerate(doubts, start=2):
        ttk.Label(frm, text=d["key"]).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 8))
        v = tk.StringVar(value=d["value"])
        ttk.Combobox(frm, textvariable=v, values=d["options"], width=18,
                     state="readonly" if d["closed"] else "normal").grid(row=i, column=1, padx=(0, 8))
        ttk.Label(frm, text=d["note"], wraplength=380, justify="left").grid(row=i, column=2, sticky="w")
        vars_[d["key"]] = v

    result = {}

    def ok():
        from tkinter import messagebox
        bad = [d["key"] for d in doubts if not valid_choice(d, vars_[d["key"]].get().strip())]
        if bad:
            messagebox.showerror("Invalid value", "A number is expected for:\n" + "\n".join(bad), parent=win)
            return
        result.update({k: v.get().strip() for k, v in vars_.items()})
        win.destroy()

    btns = ttk.Frame(frm)
    btns.grid(row=len(doubts) + 2, column=0, columnspan=3, pady=(12, 0))
    ttk.Button(btns, text="OK", command=ok).grid(row=0, column=0, padx=4)
    ttk.Button(btns, text="Cancel", command=win.destroy).grid(row=0, column=1, padx=4)
    win.bind("<Return>", lambda e: ok())
    win.bind("<Escape>", lambda e: win.destroy())
    root.wait_window(win)
    return result or None


def gui(initial_src=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title(f"SuperSlicer -> PrusaSlicer print settings converter {__version__}")
    root.resizable(True, False)
    frm = ttk.Frame(root, padding=12)
    frm.grid(sticky="nsew")
    root.columnconfigure(0, weight=1)
    frm.columnconfigure(1, weight=1)

    src = tk.StringVar(value=initial_src or "")
    nozzle = tk.StringVar(value="0.4")
    ovr = tk.StringVar(value=default_overrides_path() or "")
    outdir = tk.StringVar(value=prusa_print_dir() or "")

    def pick_src():
        p = filedialog.askopenfilename(title="SuperSlicer print profile",
                                       initialdir=superslicer_print_dir() or os.getcwd(),
                                       filetypes=[(".ini profiles", "*.ini"), ("All files", "*.*")])
        if p:
            src.set(p)

    def pick_ovr():
        p = filedialog.askopenfilename(title="Overrides file (optional)", initialdir=app_dir(),
                                       filetypes=[(".ini files", "*.ini"), ("All files", "*.*")])
        if p:
            ovr.set(p)

    def pick_out():
        p = filedialog.askdirectory(title="Output folder", initialdir=outdir.get() or os.getcwd())
        if p:
            outdir.set(p)

    rows = [("SuperSlicer profile", src, pick_src), ("Overrides (optional)", ovr, pick_ovr),
            ("Output folder", outdir, pick_out)]
    for i, (lbl, var, cmd) in enumerate(rows):
        ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=var, width=70).grid(row=i, column=1, sticky="ew", padx=6)
        ttk.Button(frm, text="...", width=4, command=cmd).grid(row=i, column=2)
    ttk.Label(frm, text="Nozzle diameter (mm)").grid(row=3, column=0, sticky="w", pady=3)
    ttk.Entry(frm, textvariable=nozzle, width=8).grid(row=3, column=1, sticky="w", padx=6)

    def run():
        s = src.get().strip()
        if not os.path.isfile(s):
            messagebox.showerror("Error", "Please choose a SuperSlicer profile (.ini).")
            return
        try:
            n = float(nozzle.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Error", "Invalid nozzle diameter.")
            return
        o = ovr.get().strip() or None
        if o and not os.path.isfile(o):
            messagebox.showerror("Error", f"Overrides file not found:\n{o}")
            return
        d = outdir.get().strip() or os.path.dirname(os.path.abspath(s))
        out_path = output_path_for(s, d)
        if os.path.abspath(out_path) == os.path.abspath(s):
            messagebox.showerror("Error", "The output would overwrite the SuperSlicer profile.\n"
                                          "Choose another output folder.")
            return
        if os.path.exists(out_path) and not messagebox.askyesno(
                "Replace?", f"{out_path}\nalready exists. Replace it?"):
            return
        try:
            conv = prepare(s, n, o)
            if conv.doubts:
                choices = ask_gui(root, conv.doubts)
                if choices is None:
                    return
                conv.apply_choices(choices)
            res = write(conv, out_path)
        except Exception as e:  # shown to the user
            messagebox.showerror("Error", str(e))
            return
        messagebox.showinfo("Conversion done",
                            summary(*res) + "\n\nRestart PrusaSlicer to see the new profile.")

    ttk.Button(frm, text="Convert", command=run).grid(row=4, column=0, columnspan=3, pady=(10, 0))
    root.mainloop()


def main():
    # No argument (double-click) or a single .ini dropped onto the exe: window (pre-filled).
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1].lower().endswith(".ini")
                              and getattr(sys, "frozen", False)):
        gui(sys.argv[1] if len(sys.argv) == 2 else None)
        return

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="SuperSlicer print profile (.ini)")
    ap.add_argument("-o", "--out", help="output .ini file (default: PrusaSlicer print folder)")
    ap.add_argument("--nozzle", type=float, default=0.4, help="nozzle diameter (to convert %% widths to mm)")
    ap.add_argument("--overrides", help="overrides file (default: overrides.ini next to the program, if present)")
    ap.add_argument("--no-overrides", action="store_true", help="ignore overrides.ini")
    ap.add_argument("-y", "--yes", action="store_true",
                    help="accept the proposed values for doubtful settings without asking")
    ap.add_argument("-f", "--force", action="store_true", help="overwrite the output file if it exists")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args()

    out_path = args.out or output_path_for(args.src)
    if os.path.abspath(out_path) == os.path.abspath(args.src):
        ap.error("the output would overwrite the SuperSlicer profile, use -o")
    if os.path.exists(out_path) and not args.force:
        ap.error(f"{out_path} already exists (use -f to overwrite, or -o)")
    interactive = not args.yes and sys.stdin is not None and sys.stdin.isatty()
    ovr = None if args.no_overrides else (args.overrides or default_overrides_path())
    print(summary(*convert_file(args.src, out_path, args.nozzle, ovr, ask_console if interactive else None)))


if __name__ == "__main__":
    main()
