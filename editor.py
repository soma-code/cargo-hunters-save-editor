import json
import shutil
import sys
import uuid as _uuid
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime

DEFAULT_SAVE = Path.home() / "AppData/LocalLow/OrderOfMeta/Cargo Hunters/offline.save"

CELL = 56  # pixels per grid cell
GRID_ROWS = 30   # J axis — vertical (matches base stash Height from template)
GRID_COLS = 8    # I axis — horizontal (matches base stash Width from template)

# When frozen by PyInstaller, item_templates.json is bundled into _MEIPASS.
# At runtime we cache it next to the exe so it survives across relaunches.
def _items_db_path() -> Path:
    if getattr(sys, "frozen", False):
        bundled = Path(sys._MEIPASS) / "item_templates.json"
        cache = Path(sys.executable).parent / "item_templates.json"
        if not cache.exists() and bundled.exists():
            shutil.copy2(bundled, cache)
        return cache
    return Path(__file__).parent / "item_templates.json"

_ITEMS_DB_CACHE = _items_db_path()

_GAME_BUNDLE_SUFFIX = (
    "steamapps/common/Cargo Hunters/CargoHunters_Data"
    "/StreamingAssets/aa/StandaloneWindows64"
    "/repositoriesgroup_assets_all_*.bundle"
)


def _find_game_bundle() -> str | None:
    """Locate the Cargo Hunters asset bundle across common Steam library locations."""
    import glob as _glob
    roots = []
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\WOW6432Node\Valve\Steam")
        roots.append(Path(winreg.QueryValueEx(key, "InstallPath")[0]))
    except Exception:
        pass
    roots += [Path("C:/Program Files (x86)/Steam"), Path("C:/Program Files/Steam")]
    for root in roots:
        matches = _glob.glob(str(root / _GAME_BUNDLE_SUFFIX))
        if matches:
            return matches[0]
    return None


def _item_size(info: dict, save_item: dict | None = None) -> tuple[int, int]:
    """Return (i_span, j_span) for an item, respecting IsRotated."""
    w = max(1, int(info.get("Width", 1)))
    h = max(1, int(info.get("Height", 1)))
    rotated = bool(save_item.get("IsRotated")) if save_item else False

    if not info.get("IsResizable", False):
        return (h, w) if rotated else (w, h)

    # Weapon — try to read actual attachment dimensions from save data
    if save_item is not None:
        ad = save_item.get("AdditionalData", {}).get("_data", {})
        bc_w = int(ad.get("BaseComponent_width", 0))
        bc_h = int(ad.get("BaseComponent_height", 0))
        rw, rh = (w + bc_w, h + bc_h) if (bc_w > 0 or bc_h > 0) else (w, h)
        return (rh, rw) if rotated else (rw, rh)

    # No save data (spawn dialog) — use MaxSize as upper bound
    max_w = info.get("MaxWidth")
    max_h = info.get("MaxHeight")
    if max_w and max_h:
        return int(max_w), int(max_h)
    return w, h

COUNTER_LABELS = {
    "SessionNumber": "Sessions Played",
    "SessionSurvivedCount": "Sessions Survived",
    "DistancePassed": "Distance Passed",
    "KilledEntities": "Enemies Killed",
    "LootCollected": "Loot Collected",
    "LootPriceCollected": "Loot Value Collected",
    "LootWeightCollected": "Loot Weight Collected",
}

_CAT_COLORS = {
    "1":  "#c83030",  # Weapons        — red
    "5":  "#a07848",  # Bags           — tan
    "6":  "#708028",  # Chest rigs     — olive
    "7":  "#289898",  # Headgear       — teal
    "9":  "#3868a8",  # Body armor     — steel blue
    "10": "#c86020",  # Grenades       — orange
    "13": "#18a8c0",  # Body parts     — cyan (robotic/bionic)
    "14": "#28a050",  # Repair kits    — green
    "17": "#9040b8",  # Valuables      — purple
    "18": "#c89810",  # Quest items / keys — gold
    "20": "#5878a0",  # Attachments    — slate blue
    "22": "#788898",  # Containers     — silver
    "23": "#c89810",  # Keys (world)   — gold
}

# Ammo shades: standard = brass, AP = dark steel-olive, E = bright yellow
_AMMO_COLORS = {
    "ap": "#586018",  # dark, muted — hard penetrator
    "e":  "#d4c838",  # bright, warm — soft/expanding
    "":   "#a0a828",  # standard     — brass
}


def _cat_color(info: dict) -> str:
    cat_id = str(info.get("CategoryID", ""))
    if cat_id == "3":
        name = info.get("ItemName", "")
        suffix = name.rsplit(" ", 1)[-1].lower() if " " in name else ""
        return _AMMO_COLORS.get(suffix, _AMMO_COLORS[""])
    return _CAT_COLORS.get(cat_id, "#555555")


# ── Dark theme ──────────────────────────────────────────────────────────────

_BG  = "#1a1a1a"   # main background — matches the stash canvas
_BG2 = "#242424"   # panels / treeview rows
_BG3 = "#333333"   # inputs / buttons / treeview headings
_FG  = "#cccccc"   # primary text
_FG2 = "#888888"   # muted text (inactive tabs)
_SEL = "#0a5a9a"   # selection highlight
_BDR = "#444444"   # borders


def _apply_dark_theme(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".",
        background=_BG, foreground=_FG,
        troughcolor=_BG2, bordercolor=_BDR,
        darkcolor=_BG2, lightcolor=_BG3,
        selectbackground=_SEL, selectforeground=_FG,
        fieldbackground=_BG3, font=("Segoe UI", 9),
    )
    style.configure("TFrame", background=_BG)
    style.configure("TLabel", background=_BG, foreground=_FG)
    style.configure("TButton",
        background=_BG3, foreground=_FG,
        bordercolor=_BDR, lightcolor=_BG3, darkcolor=_BG3, padding=4,
    )
    style.map("TButton",
        background=[("active", "#444444"), ("pressed", "#555555")],
        relief=[("pressed", "flat")],
    )
    style.configure("TEntry", fieldbackground=_BG3, foreground=_FG,
                    bordercolor=_BDR, insertcolor=_FG)
    style.configure("TCheckbutton", background=_BG, foreground=_FG)
    style.map("TCheckbutton",
        background=[("active", _BG)],
        foreground=[("active", _FG)],
        indicatorcolor=[("selected", _SEL), ("!selected", _BG3)],
    )
    style.configure("TNotebook", background=_BG, bordercolor=_BDR, tabmargins=0)
    style.configure("TNotebook.Tab",
        background=_BG2, foreground=_FG2, padding=[10, 4], bordercolor=_BDR,
    )
    style.map("TNotebook.Tab",
        background=[("selected", _BG), ("active", _BG3)],
        foreground=[("selected", _FG), ("active", _FG)],
        expand=[("selected", [1, 1, 1, 0])],
    )
    style.configure("TSeparator", background=_BDR)
    style.configure("TScrollbar",
        background=_BG3, troughcolor=_BG2,
        arrowcolor=_FG, bordercolor=_BDR,
        lightcolor=_BG3, darkcolor=_BG3,
    )
    style.map("TScrollbar", background=[("active", "#4a4a4a")])
    style.configure("Treeview",
        background=_BG2, foreground=_FG,
        fieldbackground=_BG2, bordercolor=_BDR, rowheight=22,
    )
    style.configure("Treeview.Heading",
        background=_BG3, foreground=_FG, bordercolor=_BDR, relief="flat",
    )
    style.map("Treeview",
        background=[("selected", _SEL)],
        foreground=[("selected", _FG)],
    )
    style.map("Treeview.Heading", background=[("active", "#444444")])
    root.configure(bg=_BG)


def _contrast(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return "#000000" if (r * 299 + g * 587 + b * 114) / 1000 > 128 else "#ffffff"


_tk_fonts: dict = {}

def _get_tk_font(size: int) -> tkfont.Font:
    if size not in _tk_fonts:
        _tk_fonts[size] = tkfont.Font(family="Segoe UI", size=size)
    return _tk_fonts[size]

def _measure_split(fnt: tkfont.Font, text: str, max_w: int) -> int:
    """Longest prefix of text whose pixel width fits in max_w. Returns 0 if nothing fits."""
    lo, hi, result = 1, len(text), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if fnt.measure(text[:mid]) <= max_w:
            result = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return result

def _truncate(fnt: tkfont.Font, text: str, max_w: int) -> str:
    """Longest prefix of text + ellipsis that fits in max_w. Empty string if nothing fits."""
    lo, hi, result = 1, len(text), ""
    while lo <= hi:
        mid = (lo + hi) // 2
        t = text[:mid] + ("…" if mid < len(text) else "")
        if fnt.measure(t) <= max_w:
            result = t
            lo = mid + 1
        else:
            hi = mid - 1
    return result

def _fit_label(name: str, box_w: int, box_h: int) -> tuple:
    """Return (label_text, font_tuple) that fits inside box_w x box_h pixels."""
    for fs in (9, 8, 7):
        fnt = _get_tk_font(fs)
        lh = fnt.metrics("linespace")
        if box_h >= lh * 2 + 2:
            split = _measure_split(fnt, name, box_w)
            if split >= len(name):
                return name, ("Segoe UI", fs)
            if split > 0:
                line2 = _truncate(fnt, name[split:], box_w)
                return name[:split] + ("\n" + line2 if line2 else ""), ("Segoe UI", fs)
        if fnt.measure(name) <= box_w:
            return name, ("Segoe UI", fs)
    fnt = _get_tk_font(7)
    return _truncate(fnt, name, box_w) or "…", ("Segoe UI", 7)


def _load_items_db(_save_path=None):
    """Load item templates from cached JSON or extract from game bundle."""
    cache = _ITEMS_DB_CACHE
    if not cache.exists():
        _extract_items_db(cache)
    if not cache.exists():
        return {}
    try:
        with open(cache, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}
    db = {}
    for entry in raw:
        tid = entry.get("_id", "")
        if not tid:
            continue
        name, w, h, resizable, max_w, max_h, cat_id, price, stack_cap, has_cond, cond_max = "", 1, 1, False, None, None, "", "", None, False, None
        for comp in entry.get("_components", []):
            t = comp.get("$t")
            if t == 26276:
                name = comp.get("Name", "")
            elif t == 4373:
                d = comp.get("_data", {})
                sz = d.get("Size", {})
                w, h = sz.get("Width", 1), sz.get("Height", 1)
                resizable = d.get("IsResizable", False)
                ms = d.get("MaxSize", {})
                if ms:
                    max_w, max_h = ms.get("Width"), ms.get("Height")
            elif t == 1204:
                cat_id = str(comp.get("_data", {}).get("CategoryId", ""))
            elif t == 51833:
                items_list = comp.get("_data", {}).get("Price", {}).get("Items", [])
                if items_list:
                    price = str(items_list[0].get("Count", ""))
            elif t == 24348:
                stack_cap = comp.get("_data", {}).get("StackCapacity")
            elif t == 35317:
                has_cond = True
                qty_per_seg = comp.get("_data", {}).get("DecreaseByType", [{}])[0].get("QuantityPerSegment")
                if qty_per_seg:
                    cond_max = qty_per_seg / 1000
        db[tid] = {
            "ItemID": tid, "ItemName": name,
            "Width": w, "Height": h,
            "IsResizable": resizable,
            "MaxWidth": max_w, "MaxHeight": max_h,
            "CategoryID": cat_id, "BasePrice": price,
            "StackCapacity": stack_cap,
            "HasCondition": has_cond,
            "ConditionMax": cond_max,
        }
    return db


def _extract_items_db(dest: Path):
    """Try to extract item_templates.json from the game bundle using UnityPy."""
    try:
        import UnityPy
        bundle = _find_game_bundle()
        if not bundle:
            return
        env = UnityPy.load(bundle)
        for obj in env.objects:
            if obj.type.name != "TextAsset":
                continue
            data = obj.read()
            if getattr(data, "m_Name", "") == "item_templates":
                text = getattr(data, "m_Script", None) or ""
                if isinstance(text, bytes):
                    text = text.decode("utf-8", errors="replace")
                dest.write_text(text, encoding="utf-8")
                return
    except Exception:
        pass


def _find_stash_container_id(data):
    """Return ID of the main inventory grid container (the backpack inside the root)."""
    root_id = data["InventoryDto"]["ItemDto"]["Id"]
    items = data["InventoryDto"]["ItemsContainerDto"]["Items"]
    children = [i for i in items if i.get("ParentId") == root_id]
    for child in children:
        cid = child["Id"]
        grandchildren = [i for i in items if i.get("ParentId") == cid]
        if any("J" in i.get("Position", {}) for i in grandchildren):
            return cid
    return children[0]["Id"] if children else root_id


def _collect_descendants(item_id, items):
    """Return set of item_id plus all descendant IDs."""
    by_parent = {}
    for item in items:
        pid = item.get("ParentId")
        if pid:
            by_parent.setdefault(pid, []).append(item["Id"])
    result, queue = set(), [item_id]
    while queue:
        current = queue.pop()
        result.add(current)
        queue.extend(by_parent.get(current, []))
    return result


# ── Spawn Dialog ────────────────────────────────────────────────────────────

class SpawnDialog(tk.Toplevel):
    def __init__(self, parent, items_db, grid, row, col):
        super().__init__(parent)
        self.title(f"Spawn Item  —  row {row}, col {col}")
        self.geometry("660x520")
        self.resizable(True, True)
        self.grab_set()
        self._items_db = items_db
        self._grid = grid
        self._row = row
        self._col = col
        self._all_rows = sorted(items_db.values(), key=lambda r: r["ItemName"])
        self._sort_col = "Name"
        self._sort_rev = False
        self._build()

    def _build(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter())
        entry = ttk.Entry(top, textvariable=self._search_var, width=44)
        entry.pack(side="left", padx=6)
        entry.focus_set()

        cols = ("Name", "Size", "Category", "Base Price")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for col, w in zip(cols, (280, 60, 80, 100)):
            self._tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=w, minwidth=40)
        sb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True, padx=6, pady=4)
        self._tree.bind("<Double-1>", lambda e: self._confirm())
        self._tree.bind("<Return>", lambda e: self._confirm())

        bot = ttk.Frame(self, padding=6)
        bot.pack(fill="x")
        ttk.Button(bot, text="Add to stash", command=self._confirm).pack(side="right")
        ttk.Button(bot, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Label(bot, text="Quantity:").pack(side="left")
        self._qty_var = tk.IntVar(value=1)
        self._qty_spin = ttk.Spinbox(bot, from_=1, to=1, textvariable=self._qty_var, width=6)
        self._qty_spin.pack(side="left", padx=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._filter()

    def _sort_by(self, col):
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = False
        cols = ("Name", "Size", "Category", "Base Price")
        arrows = {c: "" for c in cols}
        arrows[col] = " ▲" if not self._sort_rev else " ▼"
        for c in cols:
            self._tree.heading(c, text=c + arrows[c])
        self._filter()

    def _filter(self):
        q = self._search_var.get().lower()
        rows = [r for r in self._all_rows if not q or q in r["ItemName"].lower()]

        def _sort_key(r):
            if self._sort_col == "Name":
                return r["ItemName"].lower()
            if self._sort_col == "Size":
                i_sp, j_sp = _item_size(r)
                return i_sp * j_sp
            if self._sort_col == "Category":
                try:
                    return int(r.get("CategoryID", 0))
                except (ValueError, TypeError):
                    return 0
            if self._sort_col == "Base Price":
                try:
                    return int(r.get("BasePrice", 0))
                except (ValueError, TypeError):
                    return 0
            return ""

        rows.sort(key=_sort_key, reverse=self._sort_rev)

        self._tree.delete(*self._tree.get_children())
        for row in rows:
            i_sp, j_sp = _item_size(row)
            self._tree.insert("", "end", iid=row["ItemID"], values=(
                row["ItemName"],
                f"{i_sp}x{j_sp}",
                row.get("CategoryID", ""),
                row.get("BasePrice", ""),
            ))

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        info = self._items_db.get(sel[0], {})
        cap = info.get("StackCapacity") or 1
        self._qty_spin.configure(to=cap)
        if self._qty_var.get() > cap:
            self._qty_var.set(cap)
        self._qty_spin.configure(state="normal" if cap > 1 else "disabled")

    def _confirm(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Pick an item first.", parent=self)
            return
        template_id = sel[0]
        info = self._items_db[template_id]
        i_sp, j_sp = _item_size(info)
        cap = info.get("StackCapacity") or 1
        try:
            qty = max(1, min(cap, int(self._qty_var.get())))
        except (ValueError, tk.TclError):
            qty = 1
        self._grid.spawn_item(template_id, self._row, self._col, i_sp, j_sp, qty)
        self.destroy()


# ── Stash Grid ──────────────────────────────────────────────────────────────

class StashGrid(ttk.Frame):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self._editor = editor
        self._grid_items = {}   # (row, col) -> item dict
        self._item_cells = {}   # item_id -> [(row, col), ...]
        self._stash_id = None
        self._max_row = GRID_ROWS
        self._max_col = GRID_COLS
        self._j_offset = 0      # rows hidden at top when clipping
        self._i_offset = 0      # cols hidden at left when clipping
        self._clip_var = tk.BooleanVar(value=True)
        self._drag_item = None
        self._drag_w = 0
        self._drag_h = 0
        self._drag_rotated = False
        self._drag_ghost_ids = []
        self._last_drag_event = None
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=(4, 0))
        self._info_var = tk.StringVar(value="Load a save to see the stash.")
        ttk.Label(top, textvariable=self._info_var, anchor="w", font=("Segoe UI", 9)).pack(
            side="left", fill="x", expand=True
        )
        ttk.Checkbutton(
            top, text="Clip to content", variable=self._clip_var,
            command=self.refresh,
        ).pack(side="right")
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._canvas = tk.Canvas(frame, bg="#1a1a1a", highlightthickness=0, cursor="crosshair")
        sb_h = ttk.Scrollbar(frame, orient="horizontal", command=self._canvas.xview)
        sb_v = ttk.Scrollbar(frame, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(xscrollcommand=sb_h.set, yscrollcommand=sb_v.set)
        sb_v.pack(side="right", fill="y")
        sb_h.pack(side="bottom", fill="x")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._canvas.bind("<Button-1>", self._on_left_press)
        self._canvas.bind("<B1-Motion>", self._on_drag_motion)
        self._canvas.bind("<ButtonRelease-1>", self._on_drop)
        self._canvas.bind("<Button-3>", self._on_right_click)
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<KeyPress-r>", self._on_rotate)
        self._canvas.bind("<KeyPress-R>", self._on_rotate)
        self._canvas.bind("<Escape>", self._on_drag_cancel)
        self._canvas.bind("<Leave>", lambda e: self._info_var.set(
            "Right-click an item to delete it  |  Right-click an empty cell to spawn"
        ))
        self._canvas.bind("<MouseWheel>", lambda e: self._canvas.yview_scroll(-1 * (e.delta // 120), "units"))

    def refresh(self):
        data = self._editor.data
        items_db = self._editor.items_db
        if data is None:
            return

        all_items = data["InventoryDto"]["ItemsContainerDto"]["Items"]
        self._stash_id = _find_stash_container_id(data)

        self._grid_items = {}
        self._item_cells = {}

        for item in all_items:
            if item.get("ParentId") != self._stash_id:
                continue
            pos = item.get("Position", {})
            if "J" not in pos:
                continue
            # J = row (vertical/tall axis), I = col (horizontal/narrow axis)
            row = pos["J"]
            col = pos.get("I", 0)
            tid = item.get("TemplateId", "")
            info = items_db.get(tid, {})
            w, h = _item_size(info, item)   # w = I-span, h = J-span
            cells = []
            for dr in range(h):
                for dc in range(w):
                    self._grid_items[(row + dr, col + dc)] = item
                    cells.append((row + dr, col + dc))
            self._item_cells[item["Id"]] = cells

        if self._grid_items:
            min_r = min(r for r, c in self._grid_items)
            min_c = min(c for r, c in self._grid_items)
            max_r = max(r for r, c in self._grid_items)
            max_c = max(c for r, c in self._grid_items)
            if self._clip_var.get():
                self._j_offset = min_r
                self._i_offset = min_c
            else:
                self._j_offset = 0
                self._i_offset = 0
            self._max_row = max(GRID_ROWS - self._j_offset, max_r - self._j_offset + 4)
            self._max_col = max(GRID_COLS - self._i_offset, max_c - self._i_offset + 2)
        else:
            self._j_offset = 0
            self._i_offset = 0
            self._max_row, self._max_col = GRID_ROWS, GRID_COLS

        self._draw(items_db)
        self._info_var.set("Right-click an item to delete it  |  Right-click an empty cell to spawn")

    def _draw(self, items_db):
        c = self._canvas
        c.delete("all")
        W = self._max_col * CELL
        H = self._max_row * CELL
        c.configure(scrollregion=(0, 0, W + 2, H + 2))

        for row in range(self._max_row + 1):
            c.create_line(0, row * CELL, W, row * CELL, fill="#2d2d2d")
        for col in range(self._max_col + 1):
            c.create_line(col * CELL, 0, col * CELL, H, fill="#2d2d2d")

        drawn = set()
        for item in self._editor.data["InventoryDto"]["ItemsContainerDto"]["Items"]:
            iid = item["Id"]
            if iid in drawn or iid not in self._item_cells:
                continue
            drawn.add(iid)
            pos = item.get("Position", {})
            r0 = pos["J"]
            c0 = pos.get("I", 0)
            tid = item.get("TemplateId", "")
            info = items_db.get(tid, {})
            w, h = _item_size(info, item)   # w = I-span, h = J-span
            name = info.get("ItemName", tid[:8])
            color = _cat_color(info)
            fg = _contrast(color)

            x1, y1 = (c0 - self._i_offset) * CELL + 1, (r0 - self._j_offset) * CELL + 1
            x2, y2 = (c0 - self._i_offset + w) * CELL - 1, (r0 - self._j_offset + h) * CELL - 1

            c.create_rectangle(x1, y1, x2, y2, fill=color, outline="#555", tags=("item", iid))

            box_w = x2 - x1 - 6
            box_h = y2 - y1 - 4
            label, font = _fit_label(name, box_w, box_h)
            c.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                          text=label, fill=fg, font=font, tags=("item", iid),
                          justify="center")

            ad = item.get("AdditionalData", {}).get("_data", {})
            small = ("Segoe UI", 7)

            # Bottom right: stack quantity
            qty = ad.get("StackableComponent_quantity")
            if qty is not None and qty > 1:
                c.create_text(x2 - 3, y2 - 2, text=str(qty), fill=fg, font=small,
                              anchor="se", tags=("item", iid))

            # Bottom left: raw condition value (higher = better)
            cond_d = ad.get("Condition_d")
            if cond_d is not None:
                c.create_text(x1 + 3, y2 - 2, text=f"{cond_d:.1f}", fill=fg, font=small,
                              anchor="sw", tags=("item", iid))

    def _canvas_cell(self, event):
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        return int(y // CELL) + self._j_offset, int(x // CELL) + self._i_offset

    # ── Drag / drop ─────────────────────────────────────────────────────────

    def _lift_item(self, item_id):
        """Remove item from grid tracking and canvas without touching save data."""
        cells = self._item_cells.pop(item_id, [])
        for cell in cells:
            if self._grid_items.get(cell, {}).get("Id") == item_id:
                del self._grid_items[cell]
        self._canvas.delete(item_id)

    def _clear_ghost(self):
        for gid in self._drag_ghost_ids:
            self._canvas.delete(gid)
        self._drag_ghost_ids = []

    def _cells_free(self, row, col, w, h):
        if row < 0 or col < 0 or row + h > GRID_ROWS or col + w > GRID_COLS:
            return False
        for dr in range(h):
            for dc in range(w):
                if self._grid_items.get((row + dr, col + dc)) is not None:
                    return False
        return True

    def _find_valid_cell(self, row, col, w, h):
        """Return (row, col) of nearest free area large enough for w×h, or None."""
        for radius in range(40):
            best = None
            best_dist = float("inf")
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if max(abs(dr), abs(dc)) != radius:
                        continue
                    r, c = row + dr, col + dc
                    if self._cells_free(r, c, w, h):
                        d = abs(dr) + abs(dc)
                        if d < best_dist:
                            best_dist = d
                            best = (r, c)
            if best:
                return best
        return None

    def _update_ghost(self, event):
        self._clear_ghost()
        if self._drag_item is None:
            return
        self._last_drag_event = event
        row, col = self._canvas_cell(event)
        w, h = self._drag_w, self._drag_h

        if self._cells_free(row, col, w, h):
            r_draw, c_draw, color = row, col, "#40e040"
        else:
            snap = self._find_valid_cell(row, col, w, h)
            if snap:
                r_draw, c_draw, color = snap[0], snap[1], "#e0a020"
            else:
                r_draw, c_draw, color = row, col, "#e04040"

        x1 = (c_draw - self._i_offset) * CELL + 2
        y1 = (r_draw - self._j_offset) * CELL + 2
        x2 = (c_draw - self._i_offset + w) * CELL - 2
        y2 = (r_draw - self._j_offset + h) * CELL - 2
        gid = self._canvas.create_rectangle(
            x1, y1, x2, y2, outline=color, width=2, fill="", dash=(6, 3), tags="ghost"
        )
        self._drag_ghost_ids.append(gid)

    def _on_left_press(self, event):
        row, col = self._canvas_cell(event)
        item = self._grid_items.get((row, col))
        if not item:
            return
        tid = item.get("TemplateId", "")
        info = self._editor.items_db.get(tid, {})
        w, h = _item_size(info, item)
        self._drag_item = item
        self._drag_rotated = bool(item.get("IsRotated", False))
        self._drag_w, self._drag_h = w, h
        self._lift_item(item["Id"])
        self._canvas.focus_set()
        self._update_ghost(event)

    def _on_drag_motion(self, event):
        if self._drag_item is None:
            return
        self._update_ghost(event)

    def _on_rotate(self, event):
        if self._drag_item is None:
            return
        self._drag_rotated = not self._drag_rotated
        self._drag_w, self._drag_h = self._drag_h, self._drag_w
        if self._last_drag_event:
            self._update_ghost(self._last_drag_event)

    def _on_drop(self, event):
        if self._drag_item is None:
            return
        self._clear_ghost()
        row, col = self._canvas_cell(event)
        w, h = self._drag_w, self._drag_h
        target = (row, col) if self._cells_free(row, col, w, h) else self._find_valid_cell(row, col, w, h)
        item = self._drag_item
        self._drag_item = None
        if target is None:
            self.refresh()
            return
        item["Position"]["I"] = target[1]
        item["Position"]["J"] = target[0]
        if self._drag_rotated:
            item["IsRotated"] = True
        else:
            item.pop("IsRotated", None)
        self.refresh()

    def _on_drag_cancel(self, event):
        if self._drag_item is None:
            return
        self._clear_ghost()
        self._drag_item = None
        self.refresh()

    # ── Hover / right-click ──────────────────────────────────────────────────

    def _on_motion(self, event):
        row, col = self._canvas_cell(event)
        item = self._grid_items.get((row, col))
        if item:
            tid = item.get("TemplateId", "")
            info = self._editor.items_db.get(tid, {})
            name = info.get("ItemName", tid[:8])
            pos = item.get("Position", {})
            i_sp, j_sp = _item_size(info, item)
            self._info_var.set(
                f"{name}  [{i_sp}×{j_sp}]  "
                f"Price: {info.get('BasePrice','?')}  |  "
                f"J={pos.get('J','?')} (row)  I={pos.get('I', 0)} (col)"
            )
        else:
            self._info_var.set(f"Empty — J={row} (row), I={col} (col)  |  Right-click to spawn")

    def _on_right_click(self, event):
        row, col = self._canvas_cell(event)
        item = self._grid_items.get((row, col))
        menu = tk.Menu(self, tearoff=0, bg=_BG3, fg=_FG,
                       activebackground=_SEL, activeforeground=_FG,
                       borderwidth=1, relief="flat")
        if item:
            tid = item.get("TemplateId", "")
            name = self._editor.items_db.get(tid, {}).get("ItemName", "item")
            menu.add_command(
                label=f'Delete  \u201c{name}\u201d',
                command=lambda i=item["Id"]: self._delete_item(i),
            )
            if item.get("AdditionalData", {}).get("_data", {}).get("Condition_d") is not None:
                menu.add_separator()
                menu.add_command(label="Set to mint", command=lambda i=item: self._set_mint(i))
                menu.add_command(label="Set condition…", command=lambda i=item: self._set_condition(i))
            menu.add_separator()
            menu.add_command(label="Spawn different item here…", command=lambda: self._open_spawn(row, col))
        else:
            menu.add_command(label="Spawn item here…", command=lambda: self._open_spawn(row, col))
        menu.tk_popup(event.x_root, event.y_root)

    def _delete_item(self, item_id):
        items = self._editor.data["InventoryDto"]["ItemsContainerDto"]["Items"]
        to_remove = _collect_descendants(item_id, items)
        self._editor.data["InventoryDto"]["ItemsContainerDto"]["Items"] = [
            i for i in items if i["Id"] not in to_remove
        ]
        self.refresh()

    def _set_mint(self, item):
        ad = item.get("AdditionalData", {}).get("_data", {})
        ad.pop("Condition_d", None)
        ad.pop("Condition_mt", None)
        self.refresh()

    def _set_condition(self, item):
        ad = item.setdefault("AdditionalData", {}).setdefault("_data", {})
        cond_d = ad.get("Condition_d", 1.0)
        cond_mt = ad.get("Condition_mt")
        tid = item.get("TemplateId", "")
        template_max = self._editor.items_db.get(tid, {}).get("ConditionMax")
        max_val = cond_mt if cond_mt and cond_mt > 0 else template_max if template_max else cond_d if cond_d > 0 else 1.0
        current_pct = int(round(cond_d / max_val * 100)) if max_val else 100

        dlg = tk.Toplevel(self._editor)
        dlg.title("Set Condition")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.geometry("260x100")

        ttk.Label(dlg, text="Condition (0 = broken, 100 = perfect):").pack(pady=(12, 4))
        var = tk.IntVar(value=current_pct)
        spin = ttk.Spinbox(dlg, from_=0, to=100, textvariable=var, width=8)
        spin.pack()

        def _apply():
            try:
                pct = max(0, min(100, int(var.get()))) / 100
            except (ValueError, tk.TclError):
                pct = 1.0
            ad["Condition_d"] = max_val * pct
            dlg.destroy()
            self.refresh()

        ttk.Button(dlg, text="Apply", command=_apply).pack(pady=8)
        spin.focus_set()

    def _open_spawn(self, row, col):
        SpawnDialog(self._editor, self._editor.items_db, self, row, col)

    def spawn_item(self, template_id, row, col, w, h, qty=1):
        if row < 0 or col < 0 or row + h > GRID_ROWS or col + w > GRID_COLS:
            messagebox.showerror(
                "Out of bounds",
                f"Item doesn't fit within the {GRID_COLS}×{GRID_ROWS} stash grid.",
                parent=self._editor,
            )
            return
        for dr in range(h):
            for dc in range(w):
                if (row + dr, col + dc) in self._grid_items:
                    messagebox.showerror(
                        "Overlap",
                        f"Cell ({row + dr}, {col + dc}) is already occupied.\n"
                        "Pick an empty area or delete the existing item first.",
                        parent=self._editor,
                    )
                    return
        new_item = {
            "Id": str(_uuid.uuid4()),
            "ParentId": self._stash_id,
            "TemplateId": template_id,
            "Position": {"I": col, "J": row},
            "IsInspected": True,
        }
        if qty > 1:
            new_item["AdditionalData"] = {"_data": {"StackableComponent_quantity": qty}}
        self._editor.data["InventoryDto"]["ItemsContainerDto"]["Items"].append(new_item)
        self.refresh()


# ── Main Editor ─────────────────────────────────────────────────────────────

class SaveEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        _apply_dark_theme(self)
        self.title("Cargo Hunters Save Editor")
        self.resizable(True, True)
        self.geometry("1000x680")

        self.save_path = tk.StringVar(value=str(DEFAULT_SAVE))
        self.data = None
        self.items_db = {}
        self._skill_vars = []
        self._counter_vars = {}
        self._shop_vars = []

        self._build_ui()
        if DEFAULT_SAVE.exists():
            self._load()

    def _build_ui(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Save file:").pack(side="left")
        ttk.Entry(top, textvariable=self.save_path, width=60).pack(side="left", padx=4)
        ttk.Button(top, text="Browse", command=self._browse).pack(side="left")
        ttk.Button(top, text="Reload", command=self._load).pack(side="left", padx=4)

        self.nb = ttk.Notebook(self, padding=6)
        self.nb.pack(fill="both", expand=True, padx=6, pady=4)

        self._stash_tab = ttk.Frame(self.nb)
        self._account_tab = ttk.Frame(self.nb)
        self._skills_tab = ttk.Frame(self.nb)
        self._currency_tab = ttk.Frame(self.nb)
        self._counters_tab = ttk.Frame(self.nb)
        self._raw_tab = ttk.Frame(self.nb)

        self.nb.add(self._stash_tab, text="Stash")
        self.nb.add(self._account_tab, text="Account")
        self.nb.add(self._skills_tab, text="Skills")
        self.nb.add(self._currency_tab, text="Currency")
        self.nb.add(self._counters_tab, text="Counters")
        self.nb.add(self._raw_tab, text="Raw JSON")

        bot = ttk.Frame(self, padding=6)
        bot.pack(fill="x")
        ttk.Button(bot, text="Save (backs up first)", command=self._save).pack(side="right")
        self.status = ttk.Label(bot, text="No file loaded.")
        self.status.pack(side="left")

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Open save file",
            filetypes=[("Save files", "*.save"), ("All files", "*.*")],
        )
        if path:
            self.save_path.set(path)
            self._load()

    def _load(self):
        path = Path(self.save_path.get())
        if not path.exists():
            messagebox.showerror("Error", f"File not found:\n{path}")
            return
        with open(path, encoding="utf-8") as f:
            self.data = json.load(f)
        self.items_db = _load_items_db()
        self._build_stash_tab()
        self._build_account_tab()
        self._build_skills_tab()
        self._build_currency_tab()
        self._build_counters_tab()
        self._build_raw_tab()
        db_note = f"  ({len(self.items_db)} items in DB)" if self.items_db else "  (no item templates found)"
        self.status.config(text=f"Loaded: {path.name}{db_note}")

    def _clear(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    # ── Stash tab ───────────────────────────────────────────────────────────
    def _build_stash_tab(self):
        self._clear(self._stash_tab)
        self._stash_grid = StashGrid(self._stash_tab, self)
        self._stash_grid.pack(fill="both", expand=True)
        self._stash_grid.refresh()

    # ── Account tab ─────────────────────────────────────────────────────────
    def _build_account_tab(self):
        self._clear(self._account_tab)
        f = self._account_tab
        dto = self.data["AccountDto"]
        xp = dto["ExperienceDto"]
        self._acc_vars = {}
        rows = [
            ("Nickname", "Nickname", dto["Nickname"]),
            ("Level", "xp_level", xp["Level"]),
            ("Experience Points", "xp_points", xp["ExperiencePoints"]),
            ("Next Level XP Goal", "xp_next", xp["NextLevelExperienceGoal"]),
        ]
        for i, (label, key, val) in enumerate(rows):
            ttk.Label(f, text=label, anchor="e", width=22).grid(row=i, column=0, sticky="e", padx=8, pady=5)
            var = tk.StringVar(value=str(val))
            self._acc_vars[key] = var
            ttk.Entry(f, textvariable=var, width=30).grid(row=i, column=1, sticky="w", pady=5)
        ttk.Label(f, text="Account ID", anchor="e", width=22).grid(row=4, column=0, sticky="e", padx=8, pady=5)
        ttk.Label(f, text=dto["AccountId"], foreground="gray").grid(row=4, column=1, sticky="w", pady=5)

    # ── Skills tab ──────────────────────────────────────────────────────────
    def _build_skills_tab(self):
        self._clear(self._skills_tab)
        f = self._skills_tab

        canvas = tk.Canvas(f, borderwidth=0, highlightthickness=0, bg=_BG)
        sb = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        skills = self.data["AccountDto"]["SkillsDto"]["Skills"]
        all_keys = []
        for skill in skills:
            for k, v in skill.items():
                if k != "Id" and isinstance(v, (int, float)) and k not in all_keys:
                    all_keys.append(k)

        headers = ["Skill ID"] + all_keys
        for col, h in enumerate(headers):
            ttk.Label(inner, text=h, width=22 if col > 0 else 10, anchor="center").grid(row=0, column=col, padx=8)
        ttk.Separator(inner, orient="horizontal").grid(row=1, column=0, columnspan=len(headers), sticky="ew", pady=4)

        self._skill_vars = []
        for i, skill in enumerate(skills):
            ttk.Label(inner, text=str(skill["Id"]), width=10, anchor="center").grid(row=i + 2, column=0, pady=2)
            for col, key in enumerate(all_keys, start=1):
                val = skill.get(key, "")
                var = tk.StringVar(value=str(val) if val != "" else "")
                self._skill_vars.append((skill["Id"], key, var))
                ttk.Entry(inner, textvariable=var, width=20).grid(row=i + 2, column=col, pady=2, padx=4)

    # ── Currency tab ────────────────────────────────────────────────────────
    def _build_currency_tab(self):
        self._clear(self._currency_tab)
        f = self._currency_tab
        self._shop_vars = []

        ttk.Label(f, text="Shop", width=8, anchor="center").grid(row=0, column=0, padx=8, pady=4)
        ttk.Label(f, text="Currency ID (UUID)", width=38, anchor="w").grid(row=0, column=1, padx=8, pady=4)
        ttk.Label(f, text="Balance", width=16, anchor="center").grid(row=0, column=2, padx=8, pady=4)
        ttk.Separator(f, orient="horizontal").grid(row=1, column=0, columnspan=3, sticky="ew", pady=4)

        row = 2
        for shop_idx, shop in enumerate(self.data["AccountShops"]):
            for currency_id, amount in shop["Balance"].items():
                ttk.Label(f, text=f"Shop {shop_idx + 1}", anchor="center").grid(row=row, column=0, padx=8, pady=3)
                ttk.Label(f, text=currency_id, foreground="gray", font=("Courier", 9)).grid(
                    row=row, column=1, sticky="w", padx=8, pady=3
                )
                var = tk.StringVar(value=str(amount))
                self._shop_vars.append((shop_idx, currency_id, var))
                ttk.Entry(f, textvariable=var, width=16).grid(row=row, column=2, pady=3)
                row += 1

    # ── Counters tab ────────────────────────────────────────────────────────
    def _build_counters_tab(self):
        self._clear(self._counters_tab)
        f = self._counters_tab
        self._counter_vars = {}

        ttk.Label(f, text="Stat", width=28, anchor="e").grid(row=0, column=0, padx=8, pady=4)
        ttk.Label(f, text="Value", width=20, anchor="w").grid(row=0, column=1, padx=8, pady=4)
        ttk.Separator(f, orient="horizontal").grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)

        row = 2
        counters = self.data["AccountDto"]["Counters"].get("Counters", [])
        for counter_block in counters:
            for key, val in counter_block.get("All", {}).items():
                label = COUNTER_LABELS.get(key, key)
                ttk.Label(f, text=label, width=28, anchor="e").grid(row=row, column=0, padx=8, pady=3)
                var = tk.StringVar(value=str(val))
                self._counter_vars[(counter_block.get("$t"), key)] = var
                ttk.Entry(f, textvariable=var, width=20).grid(row=row, column=1, sticky="w", padx=8, pady=3)
                row += 1

    # ── Raw JSON tab ────────────────────────────────────────────────────────
    def _build_raw_tab(self):
        self._clear(self._raw_tab)
        f = self._raw_tab
        text = tk.Text(f, wrap="none", font=("Courier", 9),
                       bg=_BG2, fg=_FG, insertbackground=_FG,
                       selectbackground=_SEL, selectforeground=_FG)
        sb_v = ttk.Scrollbar(f, orient="vertical", command=text.yview)
        sb_h = ttk.Scrollbar(f, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        sb_v.pack(side="right", fill="y")
        sb_h.pack(side="bottom", fill="x")
        text.pack(fill="both", expand=True)
        text.insert("1.0", json.dumps(self.data, indent=2))
        text.config(state="disabled")

    # ── Save ────────────────────────────────────────────────────────────────
    def _save(self):
        if self.data is None:
            messagebox.showwarning("Nothing loaded", "Load a save file first.")
            return

        # Warn if any stash items sit outside the base stash bounds
        stash_id = _find_stash_container_id(self.data)
        all_items = self.data["InventoryDto"]["ItemsContainerDto"]["Items"]
        oob = []
        for item in all_items:
            if item.get("ParentId") != stash_id:
                continue
            pos = item.get("Position", {})
            if "J" not in pos:
                continue
            tid = item.get("TemplateId", "")
            info = self.items_db.get(tid, {})
            w, h = _item_size(info, item)
            j, i = pos["J"], pos.get("I", 0)
            if j < 0 or i < 0 or j + h > GRID_ROWS or i + w > GRID_COLS:
                oob.append(info.get("ItemName", tid[:24]))
        if oob:
            names = "\n".join(f"  • {n}" for n in oob[:10])
            if len(oob) > 10:
                names += f"\n  … and {len(oob) - 10} more"
            proceed = messagebox.askyesno(
                "Items outside stash bounds",
                f"{len(oob)} item(s) are outside the {GRID_COLS}×{GRID_ROWS} stash "
                f"grid and will be returned to your mailbox by the game:\n\n{names}\n\n"
                "Save anyway?",
            )
            if not proceed:
                return

        errors = []

        try:
            dto = self.data["AccountDto"]
            xp = dto["ExperienceDto"]
            dto["Nickname"] = self._acc_vars["Nickname"].get()
            xp["Level"] = int(self._acc_vars["xp_level"].get())
            xp["ExperiencePoints"] = int(self._acc_vars["xp_points"].get())
            xp["NextLevelExperienceGoal"] = int(self._acc_vars["xp_next"].get())
        except ValueError as e:
            errors.append(f"Account tab: {e}")

        for skill_id, key, var in self._skill_vars:
            raw = var.get().strip()
            if raw == "":
                continue
            try:
                val = int(raw)
                for skill in self.data["AccountDto"]["SkillsDto"]["Skills"]:
                    if skill["Id"] == skill_id:
                        skill[key] = val
            except ValueError as e:
                errors.append(f"Skill {skill_id} {key}: {e}")

        for shop_idx, currency_id, var in self._shop_vars:
            try:
                self.data["AccountShops"][shop_idx]["Balance"][currency_id] = int(var.get())
            except ValueError as e:
                errors.append(f"Shop {shop_idx + 1} balance: {e}")

        counters = self.data["AccountDto"]["Counters"].get("Counters", [])
        for counter_block in counters:
            block_t = counter_block.get("$t")
            for key in list(counter_block.get("All", {}).keys()):
                var = self._counter_vars.get((block_t, key))
                if var:
                    try:
                        counter_block["All"][key] = int(var.get())
                    except ValueError as e:
                        errors.append(f"Counter {key}: {e}")

        if errors:
            messagebox.showerror("Validation errors", "\n".join(errors))
            return

        path = Path(self.save_path.get())
        backup = self._rotate_backups(path)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, separators=(",", ":"))

        self._build_raw_tab()
        self.status.config(text=f"Saved. Backup: {backup.name}")
        messagebox.showinfo("Saved", f"Save written.\nBackup: {backup.name}")

    def _rotate_backups(self, path: Path, keep: int = 5) -> Path:
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        def slot(n):
            return parent / f"{stem}{suffix}.bak{n}"

        for n in range(keep, 1, -1):
            dst = slot(n)
            src = slot(n - 1)
            if dst.exists():
                dst.unlink()
            if src.exists():
                src.rename(dst)

        backup = slot(1)
        shutil.copy2(path, backup)
        return backup


if __name__ == "__main__":
    app = SaveEditor()
    app.mainloop()
