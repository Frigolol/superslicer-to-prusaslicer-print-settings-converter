"""ss2ps - convertit un profil d'impression SuperSlicer (.ini) en profil PrusaSlicer (.ini).

Usage :
    ss2ps                                   -> ouvre la fenêtre
    ss2ps <superslicer_print.ini>           -> conversion directe (aussi par glisser-déposer sur l'exe)
    ss2ps <src.ini> [-o sortie.ini] [--nozzle 0.4] [--overrides overrides.ini]

Produit :
    - le .ini PrusaSlicer (toutes les clés print de PrusaSlicer 2.9.x)
    - un rapport .md listant : conversions, doutes, valeurs par défaut, clés SuperSlicer ignorées
"""
import argparse
import datetime
import os
import sys

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Valeurs par défaut PrusaSlicer 2.9.x pour les clés qui n'ont PAS d'équivalent
# SuperSlicer (ou dont l'équivalent est désactivé). Toutes les clés print de
# PrusaSlicer 2.9.6 sont listées ici ou dans RULES.
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

# Clés dont le nom ET la sémantique sont identiques dans les deux slicers.
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

# Clés SuperSlicer volontairement ignorées (pas d'équivalent PrusaSlicer) mais
# dont la valeur a de l'impact : elles sont signalées dans le rapport.
WIDTH_KEYS = {
    # clé PrusaSlicer : clé SuperSlicer
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
        self.used = set()          # clés SS consommées
        self.out = {}              # clé Prusa -> valeur
        self.log = []              # (statut, clé prusa, valeur, explication)

    # -- helpers --------------------------------------------------------------
    def get(self, key, default=None):
        self.used.add(key)
        return self.ss.get(key, default)

    @staticmethod
    def disabled(v):
        return v is not None and v.startswith("!")

    def width_mm(self, v):
        """SuperSlicer : % = pourcentage du diamètre de buse. On sort des mm absolus."""
        if v is None or v == "" or self.disabled(v):
            return "0"
        if v.endswith("%"):
            return fmt(float(v[:-1]) / 100 * self.nozzle)
        return v

    def set(self, key, value, status="direct", note=""):
        self.out[key] = value
        self.log.append((status, key, value, note))

    # -- conversion -------------------------------------------------------------
    def run(self):
        g = self.get

        for k in DIRECT_KEYS:
            if k in self.ss:
                v = g(k)
                if self.disabled(v):
                    self.set(k, v[1:], "doute", f"valeur désactivée dans SuperSlicer (`{v}`), reprise telle quelle")
                else:
                    self.set(k, v)

        # Largeurs d'extrusion : % buse -> mm
        for pk, sk in WIDTH_KEYS.items():
            v = g(sk, "")
            mm = self.width_mm(v)
            self.set(pk, mm, "converti",
                     f"SS `{v or '(vide)'}` -> {mm} mm (base buse {self.nozzle} mm)" if v else "SS vide = auto -> 0 (auto)")
        g("first_layer_infill_extrusion_width")  # pas d'équivalent ; signalé si actif
        for k in ("external_perimeter_extrusion_spacing", "perimeter_extrusion_spacing",
                  "infill_extrusion_spacing", "solid_infill_extrusion_spacing",
                  "top_infill_extrusion_spacing", "first_layer_extrusion_spacing",
                  "first_layer_infill_extrusion_spacing", "extrusion_spacing"):
            g(k)  # spacing = forme alternative de width chez SS, redondant

        # Débit de pont : 80% -> 0.8
        v = g("bridge_flow_ratio", "100%")
        r = fmt(float(v.rstrip("%")) / 100) if v.endswith("%") else v
        self.set("bridge_flow_ratio", r, "converti", f"`{v}` -> ratio {r}")

        # Ponts épais
        bt = g("bridge_type", "nozzle")
        self.set("thick_bridges", "1" if bt == "nozzle" else "0", "converti",
                 f"bridge_type=`{bt}` : 'nozzle' (pont au diamètre de buse) ≈ thick_bridges=1 chez Prusa")

        # Angle de pont
        v = g("bridge_angle", "0")
        self.set("bridge_angle", "0" if self.disabled(v) else v, "converti",
                 f"`{v}` -> désactivé = 0 (auto)" if self.disabled(v) else "")

        # Motifs top / bottom
        for k in ("top_fill_pattern", "bottom_fill_pattern"):
            v = g(k, "monotonic")
            nv = FILL_PATTERN_MAP.get(v, v)
            if nv not in PRUSA_TOP_BOTTOM_PATTERNS:
                nv = "monotoniclines"
            st = "direct" if nv == v else "converti"
            self.set(k, nv, st, "" if nv == v else f"`{v}` n'existe pas chez Prusa -> `{nv}`")
        v = g("solid_fill_pattern")
        if v:
            self.log.append(("ignoré", "solid_fill_pattern", v,
                             "Prusa n'a pas de motif pour le solide interne (toujours rectiligne/monotone)"))

        # Coque verticale
        v = g("ensure_vertical_shell_thickness", "enabled")
        m = {"enabled_old": "enabled", "enabled": "enabled", "partial": "partial",
             "disabled": "disabled", "1": "enabled", "0": "disabled"}
        self.set("ensure_vertical_shell_thickness", m.get(v, "enabled"),
                 "direct" if v in ("enabled", "partial", "disabled") else "doute",
                 "" if v in ("enabled", "partial", "disabled") else f"`{v}` -> `{m.get(v, 'enabled')}`")

        # Compensation patte d'éléphant
        v = g("first_layer_size_compensation", "0")
        g("first_layer_size_compensation_layers"); g("first_layer_size_compensation_no_collapse")
        efc = fmt(abs(float(v))) if float(v) <= 0 else "0"
        self.set("elefant_foot_compensation", efc, "converti",
                 f"first_layer_size_compensation `{v}` -> elefant_foot_compensation {efc} (signe inversé)")

        # Résolution
        v = g("resolution", "0")
        self.set("resolution", v, "doute", "SS 'resolution' -> Prusa 'resolution' (simplification du slice)")
        g("resolution_internal")

        # Un seul périmètre sur le dessus
        v = g("only_one_perimeter_top", "0")
        g("only_one_perimeter_top_other_algo")
        self.set("top_one_perimeter_type", "top" if v == "1" else "none", "converti",
                 f"only_one_perimeter_top={v} -> {'top (toutes surfaces sup.)' if v == '1' else 'none'}")

        # Surplombs
        ow = g("overhangs_width", "75%")
        g("overhangs_width_speed"); g("overhangs_dynamic_speed"); g("overhangs_speed")
        g("overhangs_speed_enforce"); g("overhangs_bridge_threshold"); g("overhangs_bridge_upper_layers")
        g("overhangs_max_slope"); g("overhangs_reverse"); g("overhangs_reverse_threshold")
        on = "0" if self.disabled(ow) or ow in ("0", "0%") else "1"
        self.set("overhangs", on, "converti",
                 f"overhangs_width=`{ow}` -> détection des périmètres en surplomb {'activée' if on == '1' else 'désactivée'}")

        # Vitesse au-dessus des ponts internes
        v = g("internal_bridge_speed", "100%")
        self.set("over_bridge_speed", v, "converti",
                 f"internal_bridge_speed `{v}` -> over_bridge_speed")
        g("over_bridge_flow_ratio")

        # Supports
        v = g("support_material_contact_distance", "0.2")
        g("support_material_contact_distance_type")
        self.set("support_material_contact_distance", v)
        v = g("support_material_bottom_contact_distance", "0")
        self.set("support_material_bottom_contact_distance", v)
        v = g("support_material_bottom_interface_layers", "-1")
        self.set("support_material_bottom_interface_layers", "-1" if self.disabled(v) else v, "converti",
                 f"`{v}` désactivé -> -1 (identique au dessus)" if self.disabled(v) else "")
        v = g("support_material_top_interface_pattern", "rectilinear")
        g("support_material_bottom_interface_pattern")
        self.set("support_material_interface_pattern", v, "converti", "depuis support_material_top_interface_pattern")

        # Fuzzy skin : % -> mm
        for k in ("fuzzy_skin_point_dist", "fuzzy_skin_thickness"):
            v = g(k, "0.3")
            mm = self.width_mm(v)
            self.set(k, mm, "converti", f"`{v}` -> {mm} mm")

        # print_custom_variables : non utilisé -> ignoré (listé dans "ignoré")

        # Choix utilisateur
        for k, (v, why) in self.overrides.items():
            old = self.out.get(k)
            self.set(k, v, "choix", f"{old} -> {v} : {why}")

        # Valeurs sans équivalent : défauts Prusa
        for k, v in PRUSA_ONLY_DEFAULTS.items():
            if k not in self.out:
                self.set(k, v, "défaut", "pas d'équivalent SuperSlicer, valeur par défaut PrusaSlicer")

        self.set("print_settings_id", "")
        g("print_settings_id"); g("print_version")

        # Clés SS non consommées = ignorées
        for k in sorted(self.ss):
            if k not in self.used:
                self.log.append(("ignoré", k, self.ss[k], "pas d'équivalent PrusaSlicer"))
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
    """Fichier overrides : `cle = valeur`. Le commentaire `# ...` juste au-dessus sert de justification."""
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
                res[k.strip()] = (v.strip(), why or "override utilisateur")
                why = ""
    return res


def app_dir():
    """Dossier de l'exe (PyInstaller) ou du script."""
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


REPORT_ORDER = ["doute", "choix", "converti", "défaut", "ignoré", "direct"]


def convert_file(src, out_path=None, nozzle=0.4, overrides_path=None):
    """Convertit `src`. Retourne (chemin ini, chemin rapport, compteurs par statut)."""
    ss = parse_ini(src)
    if "perimeters" not in ss or "layer_height" not in ss:
        raise ValueError(f"{os.path.basename(src)} ne ressemble pas à un profil d'impression SuperSlicer")
    overrides = parse_overrides(overrides_path) if overrides_path else {}
    conv = Converter(ss, nozzle, overrides)
    out = conv.run()

    if not out_path:
        base = os.path.splitext(os.path.basename(src))[0]
        out_dir = prusa_print_dir() or os.path.dirname(os.path.abspath(src))
        out_path = os.path.join(out_dir, f"{base} (PS).ini")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# converted from SuperSlicer by ss2ps {__version__} on {datetime.datetime.now():%Y-%m-%d %H:%M}\n")
        for k in sorted(out):
            f.write(f"{k} = {out[k]}\n")

    rep_path = os.path.splitext(out_path)[0] + " - rapport.md"
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(f"# Rapport de conversion : {os.path.basename(src)}\n\n"
                f"Buse : {nozzle} mm  \nOverrides : {overrides_path or 'aucun'}\n")
        for st in REPORT_ORDER:
            rows = [r for r in conv.log if r[0] == st]
            if not rows:
                continue
            f.write(f"\n## {st} ({len(rows)})\n\n| clé | valeur | note |\n|---|---|---|\n")
            for _, k, v, n in rows:
                f.write(f"| {k} | `{v}` | {n} |\n")

    counts = {st: sum(1 for r in conv.log if r[0] == st) for st in REPORT_ORDER}
    return out_path, rep_path, counts


def summary(out_path, rep_path, counts):
    c = ", ".join(f"{k}: {v}" for k, v in counts.items())
    return f"Profil PrusaSlicer :\n{out_path}\n\nRapport :\n{rep_path}\n\n{c}"


# ---------------------------------------------------------------------------
# Interface graphique (tkinter)
# ---------------------------------------------------------------------------
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
        p = filedialog.askopenfilename(title="Profil d'impression SuperSlicer",
                                       initialdir=superslicer_print_dir() or os.getcwd(),
                                       filetypes=[("Profils .ini", "*.ini"), ("Tous", "*.*")])
        if p:
            src.set(p)

    def pick_ovr():
        p = filedialog.askopenfilename(title="Fichier overrides (optionnel)", initialdir=app_dir(),
                                       filetypes=[("Fichiers .ini", "*.ini"), ("Tous", "*.*")])
        if p:
            ovr.set(p)

    def pick_out():
        p = filedialog.askdirectory(title="Dossier de sortie", initialdir=outdir.get() or os.getcwd())
        if p:
            outdir.set(p)

    rows = [("Profil SuperSlicer", src, pick_src), ("Overrides (optionnel)", ovr, pick_ovr),
            ("Dossier de sortie", outdir, pick_out)]
    for i, (lbl, var, cmd) in enumerate(rows):
        ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=var, width=70).grid(row=i, column=1, sticky="ew", padx=6)
        ttk.Button(frm, text="...", width=4, command=cmd).grid(row=i, column=2)
    ttk.Label(frm, text="Diamètre de buse (mm)").grid(row=3, column=0, sticky="w", pady=3)
    ttk.Entry(frm, textvariable=nozzle, width=8).grid(row=3, column=1, sticky="w", padx=6)

    def run():
        s = src.get().strip()
        if not os.path.isfile(s):
            messagebox.showerror("Erreur", "Choisis un profil SuperSlicer (.ini).")
            return
        try:
            n = float(nozzle.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erreur", "Diamètre de buse invalide.")
            return
        o = ovr.get().strip() or None
        if o and not os.path.isfile(o):
            messagebox.showerror("Erreur", f"Fichier overrides introuvable :\n{o}")
            return
        d = outdir.get().strip() or os.path.dirname(os.path.abspath(s))
        out_path = os.path.join(d, os.path.splitext(os.path.basename(s))[0] + " (PS).ini")
        if os.path.exists(out_path) and not messagebox.askyesno(
                "Remplacer ?", f"{out_path}\nexiste déjà. Le remplacer ?"):
            return
        try:
            res = convert_file(s, out_path, n, o)
        except Exception as e:  # erreur affichée à l'utilisateur
            messagebox.showerror("Erreur", str(e))
            return
        messagebox.showinfo("Conversion terminée",
                            summary(*res) + "\n\nRelance PrusaSlicer pour voir le nouveau profil.")

    ttk.Button(frm, text="Convertir", command=run).grid(row=4, column=0, columnspan=3, pady=(10, 0))
    root.mainloop()


def main():
    # Sans argument (double-clic) ou un seul .ini glissé sur l'exe : fenêtre (pré-remplie).
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1].lower().endswith(".ini")
                              and getattr(sys, "frozen", False)):
        gui(sys.argv[1] if len(sys.argv) == 2 else None)
        return

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="profil d'impression SuperSlicer (.ini)")
    ap.add_argument("-o", "--out", help="fichier .ini de sortie (défaut : dossier print de PrusaSlicer)")
    ap.add_argument("--nozzle", type=float, default=0.4, help="diamètre de buse (pour convertir les %% en mm)")
    ap.add_argument("--overrides", help="fichier d'overrides (défaut : overrides.ini à côté du programme s'il existe)")
    ap.add_argument("--no-overrides", action="store_true", help="ignorer overrides.ini")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args()

    ovr = None if args.no_overrides else (args.overrides or default_overrides_path())
    print(summary(*convert_file(args.src, args.out, args.nozzle, ovr)))


if __name__ == "__main__":
    main()
