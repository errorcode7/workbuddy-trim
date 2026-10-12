#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess

SRC = "/home/debug/deb/extracted"
DST = "/home/debug/deb/extracted_trimmed"

def run_cmd(cmd, check=True):
    print(f"[CMD] {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if check and res.returncode != 0:
        print(f"Error executing: {cmd}\nStdout: {res.stdout}\nStderr: {res.stderr}")
        sys.exit(1)
    return res

def main():
    if os.path.exists(DST):
        print(f"Removing existing {DST}...")
        shutil.rmtree(DST)

    print("Copying extracted files to extracted_trimmed...")
    # Use cp -a to preserve permissions and symlinks
    run_cmd(f"cp -a {SRC} {DST}")

    print("\n--- 1. Slimming down Runtime: Node.js ---")
    node_dir = os.path.join(DST, "opt/WorkBuddy/resources/runtime/node")
    if os.path.exists(node_dir):
        shutil.rmtree(node_dir)
        os.makedirs(os.path.join(node_dir, "bin"), exist_ok=True)
        os.symlink("/usr/bin/node", os.path.join(node_dir, "bin/node"))
        os.symlink("/usr/bin/node", os.path.join(node_dir, "bin/nodejs"))
        print("Replaced bundled node with symlink to system /usr/bin/node")

    print("\n--- 2. Slimming down Runtime: Python 3 ---")
    python_dir = os.path.join(DST, "opt/WorkBuddy/resources/runtime/python")
    if os.path.exists(python_dir):
        shutil.rmtree(python_dir)
        os.makedirs(os.path.join(python_dir, "bin"), exist_ok=True)
        os.symlink("/usr/bin/python3", os.path.join(python_dir, "bin/python3"))
        os.symlink("python3", os.path.join(python_dir, "bin/python"))
        os.symlink("/usr/bin/pip3", os.path.join(python_dir, "bin/pip3"))
        os.symlink("pip3", os.path.join(python_dir, "bin/pip"))
        print("Replaced bundled python with symlink to system /usr/bin/python3 and pip3")

    print("\n--- 3. Slimming down ripgrep ---")
    rg_dir = os.path.join(DST, "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/ripgrep/x64-linux")
    if os.path.exists(rg_dir):
        rg_bin = os.path.join(rg_dir, "rg")
        if os.path.exists(rg_bin):
            os.remove(rg_bin)
        os.symlink("/usr/bin/rg", rg_bin)
        print("Replaced bundled ripgrep with symlink to system /usr/bin/rg")

    print("\n--- 4. Slimming down libvulkan.so.1 ---")
    vulkan_so = os.path.join(DST, "opt/WorkBuddy/libvulkan.so.1")
    if os.path.exists(vulkan_so):
        os.remove(vulkan_so)
        os.symlink("/usr/lib/x86_64-linux-gnu/libvulkan.so.1", vulkan_so)
        print("Replaced bundled libvulkan.so.1 with symlink to system libvulkan.so.1")

    print("\n--- 5. Removing redundant non-Linux-x64 platforms & dead files ---")
    remove_paths = [
        # koffi non-linux_x64 platforms
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/darwin_arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/darwin_x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/win32_arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/win32_ia32",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/win32_x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/freebsd_arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/freebsd_ia32",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/freebsd_x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/openbsd_ia32",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/openbsd_x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/linux_arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/linux_armhf",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/linux_ia32",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/linux_loong64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/linux_riscv64d",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/musl_arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/koffi/build/koffi/musl_x64",
        # node-pty non-linux_x64
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/node-pty/prebuilds/darwin-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/node-pty/prebuilds/darwin-x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/node-pty/prebuilds/win32-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/node-pty/prebuilds/win32-x64",
        # weixinpay non-linux_x64
        "opt/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/builtin-plugins/weixinpay/prebuilds/darwin-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/builtin-plugins/weixinpay/prebuilds/darwin-x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/builtin-plugins/weixinpay/prebuilds/win32-x64",
        # @lydell/node-pty redundant packages
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/@lydell/node-pty-linux-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/@lydell/node-pty-darwin-x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/@lydell/node-pty-darwin-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/@lydell/node-pty-win32-x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/@lydell/node-pty-win32-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/node_modules/@lydell/node-pty-linux-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/node_modules/@lydell/node-pty-darwin-x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/node_modules/@lydell/node-pty-darwin-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/node_modules/@lydell/node-pty-win32-x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/node_modules/@lydell/node-pty-win32-arm64",
        # cli binaries and macOS tools
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/bin/native/win32-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/bin/native/win32-x64",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/bin/windows-child-process-containment.bunfig.toml",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/bin/windows-child-process-containment.cjs",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/toybox-macos",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/zsh-macos",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/shim/native/darwin-arm64",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/shim/native/darwin-x64",
        # fsevents (macOS only)
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/fsevents",
        # qimei-node mac & win source code
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/@tencent/qimei-node/src/win",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/@tencent/qimei-node/src/mac",
        # better-sqlite3 build artifacts and intermediate files
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/better-sqlite3/build/Release/obj",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/better-sqlite3/build/Release/obj.target",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/better-sqlite3/build/Release/sqlite3.a",
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/better-sqlite3/deps/sqlite3/sqlite3.c",
    ]

    for rel in remove_paths:
        full = os.path.join(DST, rel)
        if os.path.exists(full):
            if os.path.isdir(full) and not os.path.islink(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
            print(f"Removed redundant: {rel}")

    print("\n--- 6. Stripping remaining Linux binaries and native .node modules ---")
    strip_targets = [
        "opt/WorkBuddy/resources/app.asar.unpacked/node_modules/@tencent/tencent-docs-ai-engine/bin/linux-x64/editor_sdk",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/sandbox/5.5.5/betterleaks",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/sandbox/5.5.5/sandbox-center",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/sandbox/5.5.5/sandbox-cli",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/sandbox/5.5.5/sandbox-cli-gc",
        "opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/sandbox/5.5.5/wb-bridge",
    ]
    # Also find all .node files in app.asar.unpacked
    for root, dirs, files in os.walk(os.path.join(DST, "opt/WorkBuddy/resources/app.asar.unpacked")):
        for f in files:
            if f.endswith(".node"):
                strip_targets.append(os.path.relpath(os.path.join(root, f), DST))

    for rel in strip_targets:
        full = os.path.join(DST, rel)
        if os.path.exists(full) and not os.path.islink(full):
            before = os.path.getsize(full)
            run_cmd(f"strip --strip-unneeded '{full}'", check=False)
            after = os.path.getsize(full)
            if before > after:
                print(f"Stripped {rel}: {before/1024/1024:.2f}MB -> {after/1024/1024:.2f}MB")

    print("\n--- 7. Updating DEBIAN/control ---")
    ctrl_path = os.path.join(DST, "DEBIAN/control")
    with open(ctrl_path, "r") as f:
        lines = f.readlines()

    # Calculate new installed size in KB
    res = run_cmd(f"du -sk {DST}/opt {DST}/usr")
    installed_size_kb = 0
    for line in res.stdout.strip().split("\n"):
        if line:
            installed_size_kb += int(line.split()[0])

    new_lines = []
    for line in lines:
        if line.startswith("Depends:"):
            deps = line.strip().split("Depends:")[1].strip()
            dep_list = [d.strip() for d in deps.split(",") if d.strip()]
            for needed in ["nodejs", "python3", "python3-pip", "ripgrep", "libvulkan1"]:
                if needed not in dep_list:
                    dep_list.append(needed)
            new_lines.append(f"Depends: {', '.join(dep_list)}\n")
        elif line.startswith("Installed-Size:"):
            new_lines.append(f"Installed-Size: {installed_size_kb}\n")
        else:
            new_lines.append(line)

    with open(ctrl_path, "w") as f:
        f.writelines(new_lines)
    print("Updated DEBIAN/control with new dependencies and Installed-Size.")

    print("\n--- 8. Regenerating DEBIAN/md5sums ---")
    md5sums_path = os.path.join(DST, "DEBIAN/md5sums")
    # Generate md5 for all files in opt and usr
    run_cmd(f"cd {DST} && find opt usr -type f ! -type l -exec md5sum {{}} + > DEBIAN/md5sums")
    print("Regenerated DEBIAN/md5sums.")

    print("\n--- 9. Building trimmed deb package ---")
    output_deb = "/home/debug/deb/WorkBuddy-linux-x64-deb-5.5.6-trimmed.deb"
    if os.path.exists(output_deb):
        os.remove(output_deb)
    # Use dpkg-deb -Zxz or -Zzstd for packaging
    run_cmd(f"dpkg-deb -b -Zxz {DST} {output_deb}")
    print(f"\nSuccessfully built trimmed deb package: {output_deb}")

if __name__ == "__main__":
    main()
