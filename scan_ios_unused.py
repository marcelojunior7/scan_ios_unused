#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, argparse, plistlib

SWIFT_EXT = ('.swift',)
IB_EXT = ('.storyboard', '.xib')
PROTECTED_ASSETS = {'AppIcon', 'AccentColor', 'LaunchImage', 'LaunchScreen', 'AppStoreIcon'}

RE_IMAGE_SWIFTUI = re.compile(r'\bImage\s*\(\s*"(.*?)"\s*\)')
RE_COLOR_SWIFTUI = re.compile(r'\bColor\s*\(\s*"(.*?)"\s*\)')
RE_UIIMAGE_NAMED = re.compile(r'\bUIImage\s*\(\s*named\s*:\s*"(.*?)"\s*\)')
RE_UICOLOR_NAMED = re.compile(r'\bUIColor\s*\(\s*named\s*:\s*"(.*?)"\s*\)')
RE_XML_IMAGE_ATTR = re.compile(r'\bimage="([^"]+)"')
RE_XML_COLOR_NODE = re.compile(r'<color[^>]+name="([^"]+)"')
RE_TYPE_DECL = re.compile(r'^\s*(?:public|internal|private|open|fileprivate)?\s*(?:final|indirect|actor|class|struct|enum)\s+([A-Za-z_]\w*)', re.MULTILINE)

def is_hidden(path):
    return any(part.startswith('.') for part in path.split(os.sep))

def list_source_files(root, exts):
    for dirpath, _, filenames in os.walk(root):
        if is_hidden(dirpath):
            continue
        for f in filenames:
            if f.endswith(exts):
                yield os.path.join(dirpath, f)

def find_xcassets_dirs(root):
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        if is_hidden(dirpath):
            continue
        for d in dirnames:
            if d.endswith('.xcassets'):
                found.append(os.path.join(dirpath, d))
    return found

def slurp(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""

def collect_declared_assets_with_paths(project_root):
    declared_paths = {}
    for catalog in find_xcassets_dirs(project_root):
        for dirpath, _, filenames in os.walk(catalog):
            if 'Contents.json' in filenames:
                if os.path.abspath(dirpath) == os.path.abspath(catalog):
                    continue
                name = os.path.basename(dirpath)
                for suf in ('.imageset', '.colorset', '.dataset', '.appiconset', '.symbolset', '.iconset', '.cubetexture'):
                    if name.endswith(suf):
                        name = name[:-len(suf)]
                        break
                if name:
                    declared_paths.setdefault(name, set()).add(dirpath)
    return declared_paths

def collect_referenced_assets(project_root, include_tests=False):
    referenced = set()
    for path in list_source_files(project_root, SWIFT_EXT):
        if (not include_tests) and ("/Tests/" in path or path.endswith("Tests.swift")):
            continue
        c = slurp(path)
        for rx in (RE_IMAGE_SWIFTUI, RE_COLOR_SWIFTUI, RE_UIIMAGE_NAMED, RE_UICOLOR_NAMED):
            for m in rx.finditer(c):
                val = (m.group(1) or "").strip()
                if val:
                    referenced.add(val)
    for path in list_source_files(project_root, IB_EXT):
        c = slurp(path)
        for m in RE_XML_IMAGE_ATTR.finditer(c):
            referenced.add(m.group(1).strip())
        for m in RE_XML_COLOR_NODE.finditer(c):
            referenced.add(m.group(1).strip())
    for dirpath, _, filenames in os.walk(project_root):
        if is_hidden(dirpath):
            continue
        for f in filenames:
            if f == 'Info.plist':
                try:
                    with open(os.path.join(dirpath, f), 'rb') as fp:
                        pl = plistlib.load(fp)
                    for n in (pl.get('CFBundleIconFiles') or []):
                        if isinstance(n, str): referenced.add(n)
                    ls = pl.get('UILaunchStoryboardName')
                    if isinstance(ls, str): referenced.add(ls)
                except Exception:
                    pass
    return referenced

def collect_types_by_file(project_root, include_tests=False):
    types_by_file = {}
    for path in list_source_files(project_root, SWIFT_EXT):
        if (not include_tests) and ("/Tests/" in path or path.endswith("Tests.swift")):
            continue
        decls = [m.group(1) for m in RE_TYPE_DECL.finditer(slurp(path))]
        if decls:
            types_by_file[path] = decls
    return types_by_file

def collect_all_swift_contents(project_root, include_tests=False):
    contents = {}
    for path in list_source_files(project_root, SWIFT_EXT):
        if (not include_tests) and ("/Tests/" in path or path.endswith("Tests.swift")):
            continue
        contents[path] = slurp(path)
    return contents

def find_unused_swift_files(project_root, include_tests=False, keep_names=None, keep_regexes=None):
    keep_names = set(keep_names or [])
    keep_regexes = [re.compile(r) for r in (keep_regexes or [])]
    types_by_file = collect_types_by_file(project_root, include_tests)
    if not types_by_file:
        return []
    all_contents = collect_all_swift_contents(project_root, include_tests)
    files = list(all_contents.keys())
    unused = []
    for file_path, decls in types_by_file.items():
        if any(t in keep_names or any(rx.search(t) for rx in keep_regexes) for t in decls):
            continue
        referenced_somewhere = False
        for t in decls:
            rx = re.compile(r'\b' + re.escape(t) + r'\b')
            for other in files:
                if other == file_path:
                    continue
                if rx.search(all_contents.get(other, "")):
                    referenced_somewhere = True
                    break
            if referenced_somewhere:
                break
        if not referenced_somewhere:
            unused.append(file_path)
    return sorted(unused)

def main():
    ap = argparse.ArgumentParser(description="Scanner for unused assets and Swift files.")
    ap.add_argument("--path", default=".", help="Project root path")
    ap.add_argument("--output-dir", default="Reports", help="Directory for reports")
    ap.add_argument("--include-tests", action="store_true", help="Include test files")
    ap.add_argument("--protect", nargs='*', default=[], help="Assets to protect")
    ap.add_argument("--keep", nargs='*', default=[], help="Type names to keep")
    ap.add_argument("--keep-regex", nargs='*', default=[], help="Regex of types to keep")
    args = ap.parse_args()

    root = os.path.abspath(args.path)
    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)

    declared_paths = collect_declared_assets_with_paths(root)
    declared_names = set(declared_paths.keys())
    referenced = collect_referenced_assets(root, include_tests=args.include_tests)
    protected = set(PROTECTED_ASSETS) | set(args.protect)

    unused_asset_names = sorted(a for a in declared_names if a not in referenced and a not in protected)
    unused_assets_paths = []
    for name in unused_asset_names:
        for p in sorted(declared_paths.get(name, [])):
            unused_assets_paths.append(os.path.abspath(p))

    unused_swift = find_unused_swift_files(
        root,
        include_tests=args.include_tests,
        keep_names=args.keep,
        keep_regexes=args.keep_regex
    )

    ua_path = os.path.join(out_dir, "unused_assets.txt")
    us_path = os.path.join(out_dir, "unused_swift_files.txt")

    with open(ua_path, "w", encoding="utf-8") as f:
        for p in unused_assets_paths:
            f.write(p + "\n")

    with open(us_path, "w", encoding="utf-8") as f:
        for p in unused_swift:
            f.write(os.path.abspath(p) + "\n")

    print("Reports generated:")
    print(f"- Unused assets: {ua_path}")
    print(f"- Unused Swift files: {us_path}")

if __name__ == "__main__":
    main()