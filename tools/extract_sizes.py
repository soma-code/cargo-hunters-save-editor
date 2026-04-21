"""
Utility script for extracting item size data from Cargo Hunters Unity assets.
This is a developer tool used to rebuild item_templates.json when the game updates.

Configure the two paths below before running:
  ASSETS_DIR  — CargoHunters_Data folder inside your Steam install
  DUMMY_DLL_DIR — DummyDll folder produced by Il2CppDumper (optional, for typed extraction)

Output is written to item_sizes_raw.json in the current directory.
"""
import sys
import os
import json

# ── Configure these paths for your machine ──────────────────────────────────
ASSETS_DIR = ""   # e.g. "C:/Program Files (x86)/Steam/steamapps/common/Cargo Hunters/CargoHunters_Data"
DUMMY_DLL_DIR = os.path.join(os.path.dirname(__file__), "il2cppdumper", "DummyDll")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "item_sizes_raw.json")
# ────────────────────────────────────────────────────────────────────────────

try:
    import UnityPy
    from UnityPy.tools.TypeTreeGenerator import generate_typetree_from_assembly
    print("UnityPy version:", UnityPy.__version__)
    has_typetree_gen = True
except ImportError as e:
    print("Import error:", e)
    has_typetree_gen = False


def try_load_with_dummydll():
    """Attempt to load type trees from DummyDll assemblies."""
    try:
        import UnityPy
        from UnityPy.tools.TypeTreeGenerator import TypeTreeGenerator
        print("TypeTreeGenerator available")

        dll_files = [os.path.join(DUMMY_DLL_DIR, f) for f in os.listdir(DUMMY_DLL_DIR) if f.endswith('.dll')]
        print(f"Found {len(dll_files)} DLL files")

        gen = TypeTreeGenerator()
        for dll in dll_files:
            try:
                gen.add_assembly(dll)
            except Exception:
                pass

        print("Generator loaded, searching assets...")

        assets_files = [
            os.path.join(ASSETS_DIR, f)
            for f in os.listdir(ASSETS_DIR)
            if f.endswith('.assets')
        ]

        results = {}
        for af in sorted(assets_files):
            env = UnityPy.load(af)
            for obj in env.objects:
                if obj.type.name == "MonoBehaviour":
                    try:
                        tree = obj.read_typetree(generator=gen)
                        if tree and ("Width" in tree or "width" in tree or "_width" in tree):
                            print(f"Found item data in {os.path.basename(af)}, obj {obj.path_id}: {tree}")
                            results[str(obj.path_id)] = tree
                    except Exception:
                        pass

        return results
    except Exception as e:
        print(f"TypeTreeGenerator approach failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def try_load_typetree_from_modules():
    """Try load_typetree_from_modules if available."""
    try:
        import UnityPy
        if hasattr(UnityPy, 'load_typetree_from_modules'):
            print("load_typetree_from_modules found on UnityPy module")
        from UnityPy.tools import TypeTreeGenerator
        print("TypeTreeGenerator module attrs:", [a for a in dir(TypeTreeGenerator) if not a.startswith('_')])
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def scan_monobehaviours_raw():
    """Scan all assets files, print MonoBehaviour type_tree contents (even if empty)."""
    import UnityPy

    assets_files = [
        os.path.join(ASSETS_DIR, f)
        for f in os.listdir(ASSETS_DIR)
        if f.endswith('.assets')
    ]

    print(f"\nScanning {len(assets_files)} assets files for MonoBehaviours...")

    for af in sorted(assets_files):
        env = UnityPy.load(af)
        mb_count = sum(1 for o in env.objects if o.type.name == "MonoBehaviour")
        if mb_count == 0:
            continue

        print(f"\n{os.path.basename(af)}: {mb_count} MonoBehaviours")

        checked = 0
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                data = obj.read()
                script_name = ""
                if hasattr(data, 'm_Script') and data.m_Script:
                    try:
                        script = data.m_Script.read()
                        script_name = getattr(script, 'm_ClassName', '') or ''
                    except Exception:
                        pass
                try:
                    tree = obj.read_typetree()
                    if tree:
                        keys = list(tree.keys())[:5]
                        print(f"  Script={script_name}, tree keys: {keys}")
                        tl = {k.lower(): v for k, v in tree.items()}
                        if 'width' in tl or 'height' in tl or '_width' in tl:
                            print(f"  *** HAS SIZE DATA: {tree}")
                    else:
                        if checked < 2:
                            print(f"  Script={script_name}, empty tree")
                except Exception as e:
                    if checked < 2:
                        print(f"  Script={script_name}, read_typetree error: {e}")
            except Exception as e:
                if checked < 2:
                    print(f"  read error: {e}")

            checked += 1
            if checked >= 5:
                break


if __name__ == "__main__":
    if not ASSETS_DIR:
        print("ERROR: Set ASSETS_DIR at the top of this script before running.")
        sys.exit(1)

    print("=== Method 1: TypeTreeGenerator with DummyDll ===")
    try_load_typetree_from_modules()

    print("\n=== Method 2: Raw MonoBehaviour scan ===")
    scan_monobehaviours_raw()

    print("\n=== Method 3: Full DummyDll extraction ===")
    results = try_load_with_dummydll()
    if results:
        print(f"Found {len(results)} items with size data!")
        with open(OUTPUT_FILE, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Written to {OUTPUT_FILE}")
    else:
        print("No size data found via DummyDll approach")
