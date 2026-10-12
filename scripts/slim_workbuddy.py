#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy Linux DEB 精简构建流水线 —— 版本无关 / 可 CI 复用版

设计目标：对官方任意新版本（5.5.x / 5.6.x / 5.7.x ...）无需改一行代码即可运行。
所有与版本相关的路径（cli/vendor/sandbox/<ver>/、better-sqlite3/bin/<abi>/ 等）
一律用「通配 + 白名单」匹配，不再写死版本号。

用法:
    python3 slim_workbuddy.py <input.deb> [output.deb] [options]

选项:
    --workdir DIR     解包工作目录（默认: 自动创建临时目录，结束后清理）
    --keep-workdir    保留工作目录（调试用）
    --compress ALG    dpkg-deb 压缩算法: xz(默认) | zstd | gzip | none
    --no-strip        跳过二进制 strip（不装 binutils 时可用）
    --self-contained  不做「软链系统运行时」替换，保持官方自带 node/python/rg/vulkan
                      （此时不会追加 nodejs/python3/ripgrep/libvulkan1 依赖）

示例:
    python3 slim_workbuddy.py WorkBuddy-linux-x64-deb-5.5.6.xxx.deb out-trimmed.deb
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------- 基础设施

def log(msg=""):
    print(msg, flush=True)


def run(cmd, check=True, cwd=None):
    """执行 shell 命令。check=True 时失败即退出。"""
    log(f"[CMD] {cmd}")
    res = subprocess.run(cmd, shell=True, text=True,
                         capture_output=True, cwd=cwd)
    if res.returncode != 0:
        log(f"  !! rc={res.returncode}")
        if res.stdout.strip():
            log(f"  stdout: {res.stdout.strip()[:2000]}")
        if res.stderr.strip():
            log(f"  stderr: {res.stderr.strip()[:2000]}")
        if check:
            sys.exit(f"命令失败: {cmd}")
    return res


def rm(path):
    """删除文件/目录/软链（不跟随软链）。"""
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
        return True
    if os.path.isdir(path):
        shutil.rmtree(path)
        return True
    return False


def is_elf(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def human(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f}{unit}"
        nbytes /= 1024
    return f"{nbytes:.1f}TB"


def dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    return total


# ---------------------------------------------------------------- 精简动作

class Slimmer:
    def __init__(self, root, use_system_runtime=True, do_strip=True):
        self.root = root                       # 解包根目录（含 opt/ usr/ DEBIAN/）
        self.opt = os.path.join(root, "opt/WorkBuddy")
        self.unpacked = os.path.join(self.opt, "resources/app.asar.unpacked")
        self.use_system_runtime = use_system_runtime
        self.do_strip = do_strip
        self.added_deps = set()
        self.saved = 0
        self.notes = []

    # -- 工具 ---------------------------------------------------------
    def drop(self, path, reason=""):
        if not os.path.exists(path) and not os.path.islink(path):
            return 0
        before = 0
        if not os.path.isdir(path) or os.path.islink(path):
            try:
                before = os.path.getsize(path)
            except OSError:
                before = 0
        else:
            before = dir_size(path)
        if rm(path):
            self.saved += before
            if reason:
                log(f"  - {reason}: {os.path.relpath(path, self.root)}")
        return before

    def keep_only(self, parent, keep_pred, reason=""):
        """在 parent 下只保留 keep_pred(name) 为真的条目，其余删除。"""
        if not os.path.isdir(parent):
            return
        for entry in os.listdir(parent):
            if not keep_pred(entry):
                self.drop(os.path.join(parent, entry), reason)

    def link_system(self, rel_target, system_path, dep=None, label=""):
        """把包内某文件替换为指向系统文件的软链。"""
        full = os.path.join(self.root, rel_target)
        if not os.path.exists(system_path):
            self.notes.append(f"跳过软链 {rel_target}：系统缺少 {system_path}")
            return
        if os.path.islink(full):
            if os.readlink(full) == system_path:
                return
        if os.path.exists(full) or os.path.islink(full):
            self.drop(full, f"软链 {label or rel_target}")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        os.symlink(system_path, full)
        log(f"  -> {os.path.relpath(full, self.root)}  ==>  {system_path}")
        if dep:
            self.added_deps.add(dep)

    # -- 支柱一：复用系统运行时 ----------------------------------------
    def slim_runtimes(self):
        log("\n=== [1] 复用系统运行时（Node / Python / ripgrep / libvulkan）===")
        if not self.use_system_runtime:
            log("  (--self-contained 已启用，跳过本步骤)")
            return

        # Node.js：整目录删除后仅保留 bin/ 软链
        node_dir = os.path.join(self.opt, "resources/runtime/node")
        if os.path.isdir(node_dir) and os.path.exists("/usr/bin/node"):
            self.drop(node_dir, "移除自带 node")
            self.link_system("opt/WorkBuddy/resources/runtime/node/bin/node",
                             "/usr/bin/node", dep="nodejs", label="node")
            self.link_system("opt/WorkBuddy/resources/runtime/node/bin/nodejs",
                             "/usr/bin/node", dep="nodejs")

        # Python 3：同上
        py_dir = os.path.join(self.opt, "resources/runtime/python")
        if os.path.isdir(py_dir) and os.path.exists("/usr/bin/python3"):
            self.drop(py_dir, "移除自带 python")
            self.link_system("opt/WorkBuddy/resources/runtime/python/bin/python3",
                             "/usr/bin/python3", dep="python3", label="python3")
            for name in ("python",):
                tgt = os.path.join(self.root, f"opt/WorkBuddy/resources/runtime/python/bin/{name}")
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                if not os.path.islink(tgt):
                    os.symlink("python3", tgt)
            if os.path.exists("/usr/bin/pip3"):
                self.link_system("opt/WorkBuddy/resources/runtime/python/bin/pip3",
                                 "/usr/bin/pip3", dep="python3-pip", label="pip3")
                tgt = os.path.join(self.root, "opt/WorkBuddy/resources/runtime/python/bin/pip")
                if not os.path.islink(tgt):
                    os.symlink("pip3", tgt)

        # ripgrep：通配所有 <arch>/rg
        for rg in glob.glob(os.path.join(self.unpacked, "cli/vendor/ripgrep/*/rg")):
            if os.path.exists("/usr/bin/rg"):
                self.drop(rg, "软链 ripgrep")
                os.symlink("/usr/bin/rg", rg)
                log(f"  -> {os.path.relpath(rg, self.root)}  ==>  /usr/bin/rg")
                self.added_deps.add("ripgrep")

        # libvulkan
        for vk in glob.glob(os.path.join(self.opt, "libvulkan.so.1*")):
            sys_vk = "/usr/lib/x86_64-linux-gnu/libvulkan.so.1"
            if os.path.exists(sys_vk):
                self.drop(vk, "软链 libvulkan")
                os.symlink(sys_vk, vk)
                log(f"  -> {os.path.relpath(vk, self.root)}  ==>  {sys_vk}")
                self.added_deps.add("libvulkan1")

    # -- 支柱二：剔除非 Linux-x64 的跨平台残留 --------------------------
    def prune_cross_platform(self):
        log("\n=== [2] 剔除非 Linux-x64 跨平台残留 ===")
        u = self.unpacked
        keep_linux = lambda n: n.startswith("linux")

        self.keep_only(os.path.join(u, "node_modules/koffi/build/koffi"),
                       lambda n: n == "linux_x64", "koffi 非 linux_x64")
        self.keep_only(os.path.join(u, "node_modules/node-pty/prebuilds"),
                       keep_linux, "node-pty 非 linux")
        self.keep_only(os.path.join(u, "resources/plugins/workbuddy-builtin/builtin-plugins/weixinpay/prebuilds"),
                       keep_linux, "weixinpay 非 linux")
        self.keep_only(os.path.join(u, "cli/bin/native"),
                       keep_linux, "cli/bin/native 非 linux")

        # @lydell/node-pty-<platform>：只保留 node-pty 与 node-pty-linux-x64
        keep_lydell = lambda n: n in ("node-pty", "node-pty-linux-x64")
        for p in glob.glob(os.path.join(u, "**/@lydell"), recursive=True):
            self.keep_only(p, keep_lydell, "@lydell 非 linux-x64")

        # 单独散落的跨平台文件 / macOS 专用工具
        for pat, reason in [
            ("cli/vendor/*-macos", "macOS 专用工具"),
            ("cli/vendor/shim/native/darwin-*", "shim darwin"),
            ("cli/vendor/shim/native/win32-*", "shim win32"),
            ("cli/bin/windows-child-process-containment.*", "Windows 专用脚本"),
            ("node_modules/fsevents", "fsevents(macOS)"),
            ("**/node_modules/fsevents", "fsevents(macOS)"),
            ("node_modules/@tencent/qimei-node/src/win", "qimei win 源码"),
            ("node_modules/@tencent/qimei-node/src/mac", "qimei mac 源码"),
        ]:
            for full in glob.glob(os.path.join(u, pat), recursive=True):
                self.drop(full, reason)

    # -- 支柱三：多语言 / 文档 / sourcemap / 源码头文件 -----------------
    def prune_docs_and_locales(self):
        log("\n=== [3] 语言包 / 许可文本 / sourcemap / 源码头文件 ===")

        # 语言包：仅保留中英
        keep_locales = {"zh-CN.pak", "zh-TW.pak", "en-US.pak", "en-GB.pak"}
        loc_dir = os.path.join(self.opt, "locales")
        if os.path.isdir(loc_dir):
            n = 0
            for f in sorted(os.listdir(loc_dir)):
                if f.endswith(".pak") and f not in keep_locales:
                    self.drop(os.path.join(loc_dir, f)); n += 1
            log(f"  - 移除 {n} 个非中英语言包")

        # 15MB 巨型 LICENSE HTML -> 精简占位
        lic = os.path.join(self.opt, "LICENSES.chromium.html")
        if os.path.isfile(lic):
            before = os.path.getsize(lic)
            with open(lic, "w", encoding="utf-8") as fp:
                fp.write("<!doctype html><html><head><meta charset='utf-8'>"
                         "<title>Licenses</title></head><body>"
                         "<h1>Chromium Open Source Licenses</h1>"
                         "<p>See https://www.chromium.org for full license disclosures.</p>"
                         "</body></html>\n")
            self.saved += before - os.path.getsize(lic)
            log(f"  - LICENSES.chromium.html: {human(before)} -> "
                f"{human(os.path.getsize(lic))}")

        # sourcemap
        n, b = 0, 0
        for root, _, files in os.walk(self.unpacked):
            for f in files:
                if f.endswith(".map"):
                    p = os.path.join(root, f)
                    try:
                        b += os.path.getsize(p)
                    except OSError:
                        pass
                    os.remove(p); n += 1
        self.saved += b
        log(f"  - 移除 {n} 个 *.map（{human(b)}）")

        # C++ 源码 / 编译中间产物（保留编译好的 .node）
        for rel in [
            "node_modules/better-sqlite3/src",
            "node_modules/better-sqlite3/deps",
            "node_modules/better-sqlite3/build/Release/obj",
            "node_modules/better-sqlite3/build/Release/obj.target",
            "node_modules/better-sqlite3/build/Release/sqlite3.a",
            "node_modules/koffi/src",
            "node_modules/koffi/vendor",
            "node_modules/koffi/doc",
        ]:
            for full in glob.glob(os.path.join(self.unpacked, rel)):
                self.drop(full, "源码/编译残留")

        # better-sqlite3 原生模块去重（<abi> 目录名随 Node 版本变化 -> 通配）
        src = os.path.join(self.unpacked, "node_modules/better-sqlite3/build/Release/better_sqlite3.node")
        if os.path.exists(src):
            for dup in glob.glob(os.path.join(self.unpacked, "**/better-sqlite3/bin/*/better-sqlite3.node"),
                                 recursive=True):
                if os.path.islink(dup) or os.path.samefile(dup, src):
                    continue
                rel_link = os.path.relpath(src, os.path.dirname(dup))
                self.drop(dup, "better-sqlite3 去重")
                os.symlink(rel_link, dup)
                log(f"  -> {os.path.relpath(dup, self.root)}  ==>  {rel_link}")

    # -- 支柱四：strip --------------------------------------------------
    def strip_binaries(self):
        log("\n=== [4] strip 原生二进制 ===")
        if not self.do_strip:
            log("  (--no-strip 已启用，跳过)")
            return
        if not shutil.which("strip"):
            self.notes.append("系统缺少 strip(binutils)，已跳过二进制瘦身")
            log("  !! 未找到 strip，跳过")
            return

        targets = []

        # (a) 所有 .node 原生插件
        for root, _, files in os.walk(self.unpacked):
            for f in files:
                if f.endswith(".node") and not os.path.islink(os.path.join(root, f)):
                    targets.append(os.path.join(root, f))

        # (b) 大体积引擎（通配版本相关路径）
        for pat in [
            "**/tencent-docs-ai-engine/bin/linux-x64/editor_sdk",
            "**/bin/linux-x64/editor_sdk",
        ]:
            targets += glob.glob(os.path.join(self.unpacked, pat), recursive=True)

        # (c) sandbox 目录下所有 ELF（目录名 = sandbox 版本号，会随版本变化）
        for sd in glob.glob(os.path.join(self.unpacked, "cli/vendor/sandbox/*")):
            if os.path.isdir(sd):
                for root, _, files in os.walk(sd):
                    for f in files:
                        fp = os.path.join(root, f)
                        if not os.path.islink(fp) and is_elf(fp):
                            targets.append(fp)

        # (d) cli 下的原生工具
        for pat in ["cli/bin/native/linux*", "cli/vendor/shim/native/linux*"]:
            for d in glob.glob(os.path.join(self.unpacked, pat)):
                for root, _, files in os.walk(d) if os.path.isdir(d) else []:
                    for f in files:
                        fp = os.path.join(root, f)
                        if not os.path.islink(fp) and is_elf(fp):
                            targets.append(fp)

        seen, saved_total = set(), 0
        for full in sorted(set(targets)):
            real = os.path.realpath(full)
            if real in seen:
                continue
            seen.add(real)
            if not os.path.isfile(full) or os.path.islink(full) or not is_elf(full):
                continue
            before = os.path.getsize(full)
            res = run(f"strip --strip-unneeded '{full}'", check=False)
            after = os.path.getsize(full) if os.path.exists(full) else before
            if res.returncode == 0 and before > after:
                saved_total += before - after
                log(f"  - strip {os.path.relpath(full, self.root)}: "
                    f"{human(before)} -> {human(after)}")
        self.saved += saved_total
        log(f"  = strip 合计节省 {human(saved_total)}")

    # -- DEBIAN 元数据 --------------------------------------------------
    def update_metadata(self, version):
        log("\n=== [5] 更新 DEBIAN 元数据 ===")
        ctrl = os.path.join(self.root, "DEBIAN/control")
        with open(ctrl, "r", encoding="utf-8") as f:
            lines = f.readlines()

        installed_kb = 0
        for sub in ("opt", "usr"):
            p = os.path.join(self.root, sub)
            if os.path.isdir(p):
                out = run(f"du -sk '{p}'").stdout.split()
                if out:
                    installed_kb += int(out[0])

        want = ["nodejs", "python3", "python3-pip", "ripgrep", "libvulkan1"]
        new_lines = []
        for line in lines:
            if line.startswith("Depends:"):
                deps = [d.strip() for d in line.split(":", 1)[1].split(",") if d.strip()]
                for d in want:
                    if d in self.added_deps and d not in deps:
                        deps.append(d)
                new_lines.append("Depends: " + ", ".join(deps) + "\n")
            elif line.startswith("Installed-Size:"):
                new_lines.append(f"Installed-Size: {installed_kb}\n")
            else:
                new_lines.append(line)
        with open(ctrl, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        log(f"  - Installed-Size = {installed_kb} KB")
        log(f"  - 追加依赖 = {sorted(self.added_deps) or '无'}")

        log("  重新生成 DEBIAN/md5sums ...")
        run("find opt usr -type f ! -type l -exec md5sum {} + > DEBIAN/md5sums",
            cwd=self.root)


# ---------------------------------------------------------------- 主流程

def read_version(root):
    ctrl = os.path.join(root, "DEBIAN/control")
    with open(ctrl, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    return "unknown"


def verify(out_deb, tmp):
    """构建后校验：结构、断链、可选的可解包性。"""
    log("\n=== [6] 产物校验 ===")
    info = run(f"dpkg-deb --info '{out_deb}'", check=False)
    if info.returncode != 0:
        sys.exit("产物不是合法 deb！")
    for line in info.stdout.splitlines():
        if line.strip():
            log("  " + line.strip())

    vdir = os.path.join(tmp, "_verify")
    if os.path.exists(vdir):
        shutil.rmtree(vdir)
    run(f"dpkg-deb -R '{out_deb}' '{vdir}'")
    broken = run(f"find '{vdir}' -xtype l").stdout.strip()
    if broken:
        log("  !! 发现断链:")
        for b in broken.splitlines():
            log("     " + b)
    else:
        log("  OK 无断链（-xtype l 为空）")
    shutil.rmtree(vdir, ignore_errors=True)
    return not broken


def main():
    ap = argparse.ArgumentParser(description="WorkBuddy DEB 精简流水线（版本无关）")
    ap.add_argument("input")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--workdir")
    ap.add_argument("--keep-workdir", action="store_true")
    ap.add_argument("--compress", default="xz", choices=["xz", "zstd", "gzip", "none"])
    ap.add_argument("--no-strip", action="store_true")
    ap.add_argument("--self-contained", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"输入文件不存在: {args.input}")
    if not shutil.which("dpkg-deb"):
        sys.exit("未找到 dpkg-deb（需要 dpkg / dpkg-dev）")

    in_deb = os.path.abspath(args.input)
    orig_size = os.path.getsize(in_deb)

    tmp = args.workdir or tempfile.mkdtemp(prefix="wb-slim-")
    root = os.path.join(tmp, "root")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)

    log("=" * 72)
    log("WorkBuddy DEB 精简流水线")
    log(f"  输入: {in_deb}  ({human(orig_size)})")
    log("=" * 72)

    log("\n=== [0] 解包 ===")
    run(f"dpkg-deb -R '{in_deb}' '{root}'")
    version = read_version(root)
    log(f"  包内版本: {version}")
    unpacked_size = dir_size(os.path.join(root, "opt")) + dir_size(os.path.join(root, "usr"))
    log(f"  解包后占用: {human(unpacked_size)}")

    out_deb = args.output or os.path.join(
        os.path.dirname(in_deb), f"WorkBuddy-linux-x64-deb-{version}-trimmed.deb")
    out_deb = os.path.abspath(out_deb)

    sl = Slimmer(root,
                 use_system_runtime=not args.self_contained,
                 do_strip=not args.no_strip)
    sl.slim_runtimes()
    sl.prune_cross_platform()
    sl.prune_docs_and_locales()
    sl.strip_binaries()
    sl.update_metadata(version)

    if sl.notes:
        log("\n提示:")
        for n in sl.notes:
            log("  * " + n)

    log(f"\n=== [5b] 重新打包（-Z{args.compress}）===")
    if os.path.exists(out_deb):
        os.remove(out_deb)
    os.makedirs(os.path.dirname(out_deb), exist_ok=True)
    run(f"dpkg-deb -b -Z{args.compress} '{root}' '{out_deb}'")

    ok = verify(out_deb, tmp)

    new_size = os.path.getsize(out_deb)
    new_unpacked = dir_size(os.path.join(root, "opt")) + dir_size(os.path.join(root, "usr"))

    log("\n" + "=" * 72)
    log("结果")
    log("=" * 72)
    log(f"  包体积   : {human(orig_size)}  ->  {human(new_size)}"
        f"   ({(new_size - orig_size) / orig_size * 100:+.1f}%)")
    log(f"  安装占用 : {human(unpacked_size)}  ->  {human(new_unpacked)}"
        f"   ({(new_unpacked - unpacked_size) / unpacked_size * 100:+.1f}%)")
    log(f"  输出文件 : {out_deb}")
    log(f"  断链检查 : {'通过' if ok else '存在断链!'}")

    if not args.keep_workdir and not args.workdir:
        shutil.rmtree(tmp, ignore_errors=True)
        log("  工作目录已清理")
    else:
        log(f"  工作目录保留: {tmp}")

    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
