#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess

DIR = "/home/debug/deb/extracted_trimmed"

def run_cmd(cmd, check=True):
    print(f"[CMD] {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if check and res.returncode != 0:
        print(f"Error: {cmd}\nStdout: {res.stdout}\nStderr: {res.stderr}")
        sys.exit(1)
    return res

def main():
    print("=== Step 1: Slimming down Locales (keeping only zh and en) ===")
    locales_dir = os.path.join(DIR, "opt/WorkBuddy/locales")
    keep_locales = {"zh-CN.pak", "zh-TW.pak", "en-US.pak", "en-GB.pak"}
    removed_count = 0
    saved_bytes = 0
    for f in os.listdir(locales_dir):
        if f.endswith(".pak") and f not in keep_locales:
            p = os.path.join(locales_dir, f)
            saved_bytes += os.path.getsize(p)
            os.remove(p)
            removed_count += 1
    print(f"Removed {removed_count} non-zh/en locales, saved {saved_bytes / 1024 / 1024:.2f} MB")

    print("\n=== Step 2: Slimming LICENSES.chromium.html ===")
    lic_file = os.path.join(DIR, "opt/WorkBuddy/LICENSES.chromium.html")
    if os.path.exists(lic_file):
        orig_sz = os.path.getsize(lic_file)
        with open(lic_file, "w") as fp:
            fp.write("<!doctype html><html><head><meta charset='utf-8'><title>Licenses</title></head><body><h1>Chromium Open Source Licenses</h1><p>See https://www.chromium.org for full license disclosures.</p></body></html>\n")
        new_sz = os.path.getsize(lic_file)
        print(f"Reduced LICENSES.chromium.html: {orig_sz / 1024 / 1024:.2f} MB -> {new_sz} bytes")

    print("\n=== Step 3: Removing development Source Maps (*.map) ===")
    unpacked_dir = os.path.join(DIR, "opt/WorkBuddy/resources/app.asar.unpacked")
    map_count = 0
    map_bytes = 0
    for root, dirs, files in os.walk(unpacked_dir):
        for f in files:
            if f.endswith(".map"):
                p = os.path.join(root, f)
                map_bytes += os.path.getsize(p)
                os.remove(p)
                map_count += 1
    print(f"Removed {map_count} .map files, saved {map_bytes / 1024 / 1024:.2f} MB")

    print("\n=== Step 4: De-duplicating better-sqlite3 native addon ===")
    dup_node = os.path.join(DIR, "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/better-sqlite3/bin/linux-x64-136/better-sqlite3.node")
    target_node = "../../build/Release/better_sqlite3.node"
    if os.path.exists(dup_node) and not os.path.islink(dup_node):
        os.remove(dup_node)
        os.symlink(target_node, dup_node)
        print("Replaced duplicated better-sqlite3.node with relative symlink")

    print("\n=== Step 5: Removing unused C++ source and build headers in node_modules ===")
    clean_dirs = [
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/better-sqlite3/src",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/better-sqlite3/deps",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/src",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/vendor",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/doc",
    ]
    for rel in clean_dirs:
        p = os.path.join(DIR, rel)
        if os.path.exists(p):
            shutil.rmtree(p)
            print(f"Removed build source/header dir: {rel}")

    print("\n=== Step 6: Recalculating Installed-Size & Updating control ===")
    ctrl_path = os.path.join(DIR, "DEBIAN/control")
    res = run_cmd(f"du -sk {DIR}/opt {DIR}/usr")
    installed_size_kb = 0
    for line in res.stdout.strip().split("\n"):
        if line:
            installed_size_kb += int(line.split()[0])

    with open(ctrl_path, "r") as fp:
        lines = fp.readlines()
    new_lines = []
    for line in lines:
        if line.startswith("Installed-Size:"):
            new_lines.append(f"Installed-Size: {installed_size_kb}\n")
        else:
            new_lines.append(line)
    with open(ctrl_path, "w") as fp:
        fp.writelines(new_lines)
    print(f"Updated Installed-Size in control: {installed_size_kb} KB")

    print("\n=== Step 7: Regenerating DEBIAN/md5sums ===")
    run_cmd(f"cd {DIR} && find opt usr -type f ! -type l -exec md5sum {{}} + > DEBIAN/md5sums")
    print("Regenerated DEBIAN/md5sums.")

    print("\n=== Step 8: Building new trimmed deb ===")
    output_deb = "/home/debug/deb/WorkBuddy-linux-x64-deb-5.5.6-trimmed.deb"
    if os.path.exists(output_deb):
        os.remove(output_deb)
    run_cmd(f"dpkg-deb -b -Zxz {DIR} {output_deb}")
    print(f"Built trimmed deb: {output_deb}")

if __name__ == "__main__":
    main()
