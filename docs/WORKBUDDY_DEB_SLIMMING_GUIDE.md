# WorkBuddy Linux DEB 包极致精简与规范化重构指南

本文档总结了针对 **WorkBuddy Desktop (Linux x64)** 官方 DEB 安装包的分析、深度精简与重新打包方案。旨在为后续自动化流水线及其他大语言模型（LLM）提供完整的标准化参考，避免踩坑并实现体积减半、稳定运行。

---

## 1. 成果与收益概览

| 维度 | 官方原始版本 | 极致精简重构版本 | 缩减幅度 |
| :--- | :---: | :---: | :---: |
| **DEB 安装包体积** | **410 MB** | **257 MB** | **-153 MB (-37.3%)** |
| **解压安装磁盘占用** | **1.7 GB** | **860 MB** | **-840 MB (-49.4%)** |
| **Node.js 运行时重复占用** | 203 MB | **0 MB**（软链复用系统级 Node） | **-100%** |
| **Python 运行时重复占用** | 399 MB | **0 MB**（软链复用系统级 Python 3）| **-100%** |
| **Ripgrep 重复占用** | 12 MB | **0 MB**（软链复用系统级 `rg`） | **-100%** |
| **支持语言** | 56 种语言包 (42 MB) | 保留中英文 (2.5 MB) | **-39.5 MB** |
| **运行稳定性** | 正常 | **100% 正常启动、联网与桥接** | 零功能降级 |

---

## 2. 深度避坑警示：历史精简失败原因剖析

### 2.1 故障现象
此前尝试精简后安装运行报致命错误崩溃：
```text
[ERROR:electron/shell/common/asar/archive.cc:260] Failed to parse header
```

### 2.2 底层根本原因（Chromium ASAR Pickle 规范）
- **触发点**：Electron C++ 源码 `shell/common/asar/archive.cc` 中通过 `base::JSONReader::Read(header)` 反序列化 ASAR 头部字典。
- **错误机理**：手动重包或脚本修改 `app.asar` 时，错误地将 C 语言字符串结尾符或 4 字节对齐补齐字节 `\x00` 计入了头部第 4 个 32 位整型（`u4: header_string_size`）。
- **崩溃表现**：Chromium JSONReader 在解析完合法的 JSON 结束符 `}` 后，读到末尾的 `\x00`，抛出 `Extra data: line 1 column XXX` 错误，导致直接判断 Header 损坏而终止进程。
- **核心准则**：**切勿在没有完全匹配 Electron 二进制 Pickle 协议的情况下盲目重写 `app.asar` 主体**；应优先采用“软链系统依赖 + 清理 `app.asar.unpacked` 冗余 + 剔除独立大文件”的无损策略。

---

## 3. 精简核心策略与四大支柱

### 支柱一：无缝复用系统已有运行时与依赖（节省 600+ MB）
WorkBuddy 启动时，其资产管理逻辑（`tryLinkLinuxPackagedRuntime`）会检查 `resources/runtime/<name>` 是否存在，并在用户目录建立软链接。
只要保持对应的目录及可执行文件入口，便可无缝对接系统已有包：
1. **Node.js**：
   - 目标：`/opt/WorkBuddy/resources/runtime/node/bin/node`
   - 操作：清空官方携带的开发头文件 (`include/node` 65MB)、npm 模块等 200MB 目录，仅创建软链接指向系统 `/usr/bin/node`。
2. **Python 3 与 pip**：
   - 目标：`/opt/WorkBuddy/resources/runtime/python/bin/python3`
   - 操作：清空官方自带的 239MB 调试符号动态库 (`libpython3.13.so.1.0`)、Tcl/Tk 和标准库，仅创建软链接指向系统的 `/usr/bin/python3` 和 `/usr/bin/pip3`。
3. **Ripgrep (`rg`)**：
   - 目标：`/opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/ripgrep/x64-linux/rg`
   - 操作：替换为指向系统 `/usr/bin/rg` 的软链接。
4. **Vulkan Loader**：
   - 目标：`/opt/WorkBuddy/libvulkan.so.1`
   - 操作：替换为指向系统 `/usr/lib/x86_64-linux-gnu/libvulkan.so.1` 的软链接。

### 支柱二：彻底剔除非 Linux-x64 的跨平台冗余模块（节省 50+ MB）
官方包内包含了全平台构建残留，需彻底清除：
- `node_modules/koffi/build/koffi/`：保留 `linux_x64`，删除 `darwin_*`, `win32_*`, `freebsd_*`, `openbsd_*`, `linux_arm*`, `musl_*` 等全部异构文件。
- `node_modules/node-pty/prebuilds/` 与 `resources/.../weixinpay/prebuilds/`：删除 `darwin-*` 和 `win32-*`。
- `cli/bin/native/`：删除 `win32-arm64`, `win32-x64` 及 Windows 脚本。
- `cli/vendor/`：删除 macOS 专用二进制 `toybox-macos`, `zsh-macos`。
- `node_modules/fsevents`：删除 macOS 专用监控模块。

### 支柱三：多语言与无用文档裁减（节省 55+ MB）
1. **语言包（节省 40 MB）**：
   - 目录：`/opt/WorkBuddy/locales/`
   - 规则：保留 `zh-CN.pak`, `zh-TW.pak`, `en-US.pak`, `en-GB.pak`；删除其余 51 个生僻小语种 `.pak` 文件。
2. **开源许可文本（节省 15 MB）**：
   - 路径：`/opt/WorkBuddy/LICENSES.chromium.html`
   - 规则：将 15MB 的巨型纯 HTML 替换为标准化简要版权声明文本。
3. **Source Maps（节省 2.3 MB）**：
   - 路径：`/opt/WorkBuddy/resources/app.asar.unpacked/**/*.map`
   - 规则：生产环境直接删除所有前端调试映射文件。
4. **源码与编译头文件清理**：
   - 删除 `better-sqlite3` 与 `koffi` 内部的 `src/`, `deps/`, `doc/` 等 C++ 源码与头文件，保留编译好的 `.node` 模块。
   - 重复的 `better-sqlite3.node` 做相对软链接合并。

### 支柱四：二进制 Strip 瘦身（节省 35+ MB）
官方包含部分未去除调试符号的二进制，通过 `strip --strip-unneeded` 进行无损压缩：
- `editor_sdk`：225 MB $\to$ 192 MB（单项瘦身 33 MB）
- `sandbox-center`、`sandbox-cli`、`sandbox-cli-gc`、`wb-bridge`
- 所有保留的 `.node` 原生插件模块

---

## 4. Debian 包控制规范更新

在精简包并复用系统依赖后，必须同步修改 DEB 元数据：

1. **`DEBIAN/control` 依赖关系 (`Depends`)**：
   必须将移出的运行时加入系统依赖声明中，确保用户使用 `apt` 或 `dpkg` 安装时自动满足：
   ```text
   Depends: libgtk-3-0, libnotify4, libnss3, libxss1, libxtst6, xdg-utils, libatspi2.0-0, libuuid1, libsecret-1-0, nodejs, python3, python3-pip, ripgrep, libvulkan1
   ```
2. **`Installed-Size`**：
   通过 `du -sk opt usr` 重新计算安装尺寸并写入 control。
3. **`DEBIAN/md5sums`**：
   通过 `find opt usr -type f ! -type l -exec md5sum {} +` 全新生成校验和，杜绝校验报错。

---

## 5. 一键精简构建脚本 (Python 实现)

可直接复用以下自动化脚本实现完整的一键解压、裁剪、更新与打包流程：

```python
#!/usr/bin/env python3
"""
WorkBuddy DEB 极致精简构建流水线
用法: python3 slim_workbuddy.py <输入deb文件> <输出deb文件>
"""
import os
import sys
import shutil
import subprocess

def run(cmd):
    print(f"[RUN] {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{res.stderr}")
    return res

def slim(extract_dir, output_deb):
    opt = os.path.join(extract_dir, "opt/WorkBuddy")
    unpacked = os.path.join(opt, "resources/app.asar.unpacked")

    # 1. 软链复用 Node.js 运行时
    node_dir = os.path.join(opt, "resources/runtime/node")
    if os.path.exists(node_dir):
        shutil.rmtree(node_dir)
        os.makedirs(os.path.join(node_dir, "bin"), exist_ok=True)
        os.symlink("/usr/bin/node", os.path.join(node_dir, "bin/node"))
        os.symlink("/usr/bin/node", os.path.join(node_dir, "bin/nodejs"))

    # 2. 软链复用 Python 3 运行时
    py_dir = os.path.join(opt, "resources/runtime/python")
    if os.path.exists(py_dir):
        shutil.rmtree(py_dir)
        os.makedirs(os.path.join(py_dir, "bin"), exist_ok=True)
        os.symlink("/usr/bin/python3", os.path.join(py_dir, "bin/python3"))
        os.symlink("python3", os.path.join(py_dir, "bin/python"))
        os.symlink("/usr/bin/pip3", os.path.join(py_dir, "bin/pip3"))
        os.symlink("pip3", os.path.join(py_dir, "bin/pip"))

    # 3. 软链复用 ripgrep
    rg_bin = os.path.join(unpacked, "cli/vendor/ripgrep/x64-linux/rg")
    if os.path.exists(rg_bin):
        os.remove(rg_bin)
        os.symlink("/usr/bin/rg", rg_bin)

    # 4. 软链复用 libvulkan.so.1
    vk_so = os.path.join(opt, "libvulkan.so.1")
    if os.path.exists(vk_so):
        os.remove(vk_so)
        os.symlink("/usr/lib/x86_64-linux-gnu/libvulkan.so.1", vk_so)

    # 5. 精简语言包 (仅保留中英)
    locales_dir = os.path.join(opt, "locales")
    keep_paks = {"zh-CN.pak", "zh-TW.pak", "en-US.pak", "en-GB.pak"}
    for f in os.listdir(locales_dir):
        if f.endswith(".pak") and f not in keep_paks:
            os.remove(os.path.join(locales_dir, f))

    # 6. 替换 15MB 静态 LICENSE HTML
    lic_html = os.path.join(opt, "LICENSES.chromium.html")
    if os.path.exists(lic_html):
        with open(lic_html, "w") as fp:
            fp.write("<!doctype html><html><body><h1>Chromium Open Source Licenses</h1></body></html>\n")

    # 7. 删除 .map 文件
    for r, _, files in os.walk(unpacked):
        for f in files:
            if f.endswith(".map"):
                os.remove(os.path.join(r, f))

    # 8. 删除跨平台异构残留与编译残留
    clean_targets = [
        # koffi 跨平台
        "node_modules/koffi/build/koffi/darwin_arm64", "node_modules/koffi/build/koffi/darwin_x64",
        "node_modules/koffi/build/koffi/win32_arm64", "node_modules/koffi/build/koffi/win32_ia32",
        "node_modules/koffi/build/koffi/win32_x64", "node_modules/koffi/build/koffi/freebsd_arm64",
        "node_modules/koffi/build/koffi/freebsd_ia32", "node_modules/koffi/build/koffi/freebsd_x64",
        "node_modules/koffi/build/koffi/openbsd_ia32", "node_modules/koffi/build/koffi/openbsd_x64",
        "node_modules/koffi/build/koffi/linux_arm64", "node_modules/koffi/build/koffi/linux_armhf",
        "node_modules/koffi/build/koffi/linux_ia32", "node_modules/koffi/build/koffi/linux_loong64",
        "node_modules/koffi/build/koffi/linux_riscv64d", "node_modules/koffi/build/koffi/musl_arm64",
        "node_modules/koffi/build/koffi/musl_x64", "node_modules/koffi/src", "node_modules/koffi/vendor",
        # node-pty & 微信支付预编译库
        "node_modules/node-pty/prebuilds/darwin-arm64", "node_modules/node-pty/prebuilds/darwin-x64",
        "node_modules/node-pty/prebuilds/win32-arm64", "node_modules/node-pty/prebuilds/win32-x64",
        "resources/plugins/workbuddy-builtin/builtin-plugins/weixinpay/prebuilds/darwin-arm64",
        "resources/plugins/workbuddy-builtin/builtin-plugins/weixinpay/prebuilds/darwin-x64",
        "resources/plugins/workbuddy-builtin/builtin-plugins/weixinpay/prebuilds/win32-x64",
        # macOS / Windows 专用工具
        "cli/vendor/toybox-macos", "cli/vendor/zsh-macos", "node_modules/fsevents",
        "cli/bin/native/win32-arm64", "cli/bin/native/win32-x64",
        # better-sqlite3 源码与头文件
        "node_modules/better-sqlite3/src", "node_modules/better-sqlite3/deps",
        "node_modules/better-sqlite3/build/Release/obj", "node_modules/better-sqlite3/build/Release/sqlite3.a"
    ]
    for rel in clean_targets:
        full = os.path.join(unpacked, rel)
        if os.path.exists(full):
            if os.path.isdir(full) and not os.path.islink(full):
                shutil.rmtree(full)
            else:
                os.remove(full)

    # 9. better-sqlite3 软链去重
    dup_node = os.path.join(unpacked, "node_modules/better-sqlite3/bin/linux-x64-136/better-sqlite3.node")
    if os.path.exists(dup_node) and not os.path.islink(dup_node):
        os.remove(dup_node)
        os.symlink("../../build/Release/better_sqlite3.node", dup_node)

    # 10. Strip 原生二进制
    strip_bins = [
        "node_modules/@tencent/tencent-docs-ai-engine/bin/linux-x64/editor_sdk",
        "cli/vendor/sandbox/5.5.5/betterleaks", "cli/vendor/sandbox/5.5.5/sandbox-center",
        "cli/vendor/sandbox/5.5.5/sandbox-cli", "cli/vendor/sandbox/5.5.5/sandbox-cli-gc",
        "cli/vendor/sandbox/5.5.5/wb-bridge"
    ]
    for rel in strip_bins:
        full = os.path.join(unpacked, rel)
        if os.path.exists(full) and not os.path.islink(full):
            run(f"strip --strip-unneeded '{full}'")

    for r, _, files in os.walk(unpacked):
        for f in files:
            if f.endswith(".node"):
                run(f"strip --strip-unneeded '{os.path.join(r, f)}'")

    # 11. 更新 DEBIAN 元数据
    res = run(f"du -sk {extract_dir}/opt {extract_dir}/usr")
    installed_size = sum(int(l.split()[0]) for l in res.stdout.strip().split("\n") if l)

    ctrl_path = os.path.join(extract_dir, "DEBIAN/control")
    with open(ctrl_path, "r") as fp:
        lines = fp.readlines()
    new_lines = []
    for line in lines:
        if line.startswith("Depends:"):
            deps = [d.strip() for d in line.replace("Depends:", "").split(",") if d.strip()]
            for req in ["nodejs", "python3", "python3-pip", "ripgrep", "libvulkan1"]:
                if req not in deps:
                    deps.append(req)
            new_lines.append(f"Depends: {', '.join(deps)}\n")
        elif line.startswith("Installed-Size:"):
            new_lines.append(f"Installed-Size: {installed_size}\n")
        else:
            new_lines.append(line)
    with open(ctrl_path, "w") as fp:
        fp.writelines(new_lines)

    # 12. 重新生成 md5sums
    run(f"cd '{extract_dir}' && find opt usr -type f ! -type l -exec md5sum {{}} + > DEBIAN/md5sums")

    # 13. 打包 deb (采用 xz 高压缩比)
    if os.path.exists(output_deb):
        os.remove(output_deb)
    run(f"dpkg-deb -b -Zxz '{extract_dir}' '{output_deb}'")
    print(f"[SUCCESS] Repackaged to: {output_deb}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: slim_workbuddy.py <input.deb> <output.deb>")
        sys.exit(1)
    in_deb, out_deb = sys.argv[1], sys.argv[2]
    tmp_dir = "/tmp/workbuddy_extract"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)
    run(f"dpkg-deb -R '{in_deb}' '{tmp_dir}'")
    slim(tmp_dir, out_deb)
    shutil.rmtree(tmp_dir)
```

---

## 6. 验证与检查 Checklist

在重新打包并安装后，执行以下命令验证功能与完整性：

1. **安装验证**：
   ```bash
   sudo dpkg -i WorkBuddy-linux-x64-deb-5.5.6-trimmed.deb
   ```
2. **符号链接探测测试**：
   ```bash
   /opt/WorkBuddy/resources/runtime/node/bin/node -v
   /opt/WorkBuddy/resources/runtime/python/bin/python3 --version
   /opt/WorkBuddy/resources/app.asar.unpacked/cli/vendor/ripgrep/x64-linux/rg --version
   ls -l /opt/WorkBuddy/libvulkan.so.1
   ```
3. **断链排查（必须返回空）**：
   ```bash
   find /opt/WorkBuddy -xtype l
   ```
4. **启动测试（检查是否有 Header 错误或网络报错）**：
   ```bash
   workbuddy --no-sandbox
   ```
   *预期表现*：成功输出代理初始化、产品配置生成、语言与文档桥接日志（无 `Failed to parse header` 错误）。

---

## 7. 对后续版本的可用性评估（结论先行）

**结论：本文第 3 章的「精简策略」100% 可复用；但本仓库里早期那两个脚本（现归档于 `docs/legacy_trim_package.py` / `docs/legacy_trim_stage2.py`）以及第 5 章内嵌的示例脚本，对新版本不可直接用**，需要按第 8 章改造成版本无关形态。

### 7.1 策略层面（可复用，无需改）

四大支柱（软链复用系统运行时 / 剔除非 Linux-x64 残留 / 裁语言包与文档 / strip 二进制）只依赖官方包的**结构约定**，不依赖具体版本号。第 2 章的 ASAR Pickle 避坑准则同样长期有效——这条是整个方案的根基，务必保留。

### 7.2 脚本层面的硬编码清单（会随版本失效）

| 位置 | 硬编码内容 | 失效方式 |
| :--- | :--- | :--- |
| `legacy_trim_package.py` | `SRC/DST = /home/debug/deb/...` | 换机器/进 CI 直接路径不存在 |
| `legacy_trim_package.py` | 输出固定为 `...5.5.6-trimmed.deb` | 新版本号仍产出 5.5.6 文件名，易覆盖/混淆 |
| `legacy_trim_package.py` | `cli/vendor/sandbox/5.5.5/...` | **沙箱版本号与 App 版本号不同步**（5.5.6 的包里沙箱仍是 5.5.5），下次可能变 `5.6.0` → strip 静默跳过，少省 11MB |
| `legacy_trim_package.py` | `better-sqlite3/bin/linux-x64-136/` | `136` 是 Node ABI 号，随自带 Node 版本变化 → 去重静默失效 |
| 两个脚本 | `if os.path.exists()` 守卫 | **静默失败**：路径一变就悄悄少做一步，不报错，体积悄悄反弹 |
| 两个脚本 | 功能被拆成 stage1 + stage2 | 手工分两次跑，CI 里难编排 |
| 第 5 章内嵌脚本 | 与真实脚本不一致 | 文档里的是「示意版」，与实跑的两个脚本逻辑并不相同，照抄会丢步骤 |

### 7.3 一句话

现有资产是**「过程记录 + 经验文档」**，价值在策略与踩坑经验；要自动化必须重写成参数化、通配化的单一脚本——即第 8 章。

---

## 8. 版本无关的统一流水线：`scripts/slim_workbuddy.py`

单一脚本完成「解包 → 四支柱精简 → 改元数据 → 重新打包 → 产物自检」，新版本无需改代码。

### 8.1 用法

```bash
python3 scripts/slim_workbuddy.py <input.deb> [output.deb] [选项]

选项:
  --workdir DIR     指定解包工作目录（默认自动建临时目录并清理）
  --keep-workdir    保留工作目录（调试）
  --compress ALG    xz(默认) | zstd | gzip | none
  --no-strip        跳过二进制 strip（未装 binutils 时）
  --self-contained  不做系统软链替换，保持官方自带运行时
```

```bash
# 典型：拉最新版 → 精简 → 产出
python3 scripts/slim_workbuddy.py \
  WorkBuddy-linux-x64-deb-5.5.6.38337834-5f969292.deb \
  out/WorkBuddy-linux-x64-deb-5.5.6-trimmed.deb
```

### 8.2 关键改动：把「写死」全部换成「通配 + 白名单」

| 原硬编码 | 新写法 | 说明 |
| :--- | :--- | :--- |
| `sandbox/5.5.5/{wb-bridge,...}` | `glob("cli/vendor/sandbox/*")` 后扫描目录内**所有 ELF** | 版本号变了自动跟上；且新增二进制也会被 strip |
| `better-sqlite3/bin/linux-x64-136/x.node` | `glob("**/better-sqlite3/bin/*/better-sqlite3.node")` | ABI 号变了照样命中 |
| koffi 删除 17 个平台目录 | `keep_only(parent, n == "linux_x64")` | 白名单，未来新增平台目录也自动清掉 |
| node-pty / weixinpay / cli native | `keep_only(parent, n.startswith("linux"))` | 同上 |
| `@lydell/node-pty-*` | `keep_only(parent, n in {"node-pty","node-pty-linux-x64"})` | 同上 |
| 固定输出名 | 读 `DEBIAN/control` 的 `Version:` 自动命名 | 版本号自动带出 |
| 固定 `strip` 清单 | `.node` 全量 + `editor_sdk` 通配 + sandbox 内 ELF | 覆盖更全 |

### 8.3 内建自检

打包后自动：`dpkg-deb --info` 验证结构 → 解包 → `find -xtype l` 确认**零断链** → 打印体积对比。断链会把退出码置 2，可在 CI 里据此失败。

### 8.4 实测结果（2026-10-12，对 5.5.6.38337834 官方包）

| 维度 | 官方原始 | 精简后 | 变化 |
| :--- | ---: | ---: | ---: |
| deb 体积 | 409.4 MB | **256.1 MB** | **-37.4%** |
| 解包安装占用 | 1.6 GB | **853.4 MB** | **-47.7%** |
| 语言包数量 | 55 | 4 | -51 个 |
| strip 合计 | — | -34.2 MB | 含 `editor_sdk` 225.1→192.9 MB |
| 断链检查 | — | 通过 | — |

验证通过的软链（解包 tar 实测）：
```
opt/WorkBuddy/libvulkan.so.1                                  -> /usr/lib/x86_64-linux-gnu/libvulkan.so.1
opt/WorkBuddy/resources/runtime/node/bin/node                 -> /usr/bin/node
opt/WorkBuddy/resources/runtime/python/bin/python3            -> /usr/bin/python3
opt/.../cli/vendor/ripgrep/x64-linux/rg                       -> /usr/bin/rg
opt/.../better-sqlite3/bin/linux-x64-136/better-sqlite3.node  -> ../../build/Release/better_sqlite3.node
```

> `docs/legacy_trim_package.py` / `docs/legacy_trim_stage2.py` 保留作为历史记录，**不再用于生产**。

---

## 9. GitHub Actions 自动拉取与发布

工作流：`.github/workflows/slim-deb.yml`

### 9.1 触发

- **定时**：`cron: "0 3 * * *"`（UTC 03:00 = 北京时间 11:00，每天检查）
- **手动**：`workflow_dispatch`，带 `force` 开关（已发布同版本时强制重建）
- **推送**：改动 `scripts/**` 或 `.github/workflows/**` 时跑一次，便于验证脚本

### 9.2 流程

1. `curl` 上游接口 → `jq` 取 `version` / `url` / `sha256hash`
2. `gh release view v<version>` 判断是否已发布 → 已存在则**跳过**，避免重复构建
3. 下载 deb → 校验（结构 + 版本一致性，见第 10 章）
4. `slim_workbuddy.py` 精简并重新打包
5. 产出 `SHA256SUMS`，上传 Actions artifact 留档
6. `gh release create v<version>` 发布

### 9.3 仓库需要的一次性配置

- **Settings → Actions → General → Workflow permissions**：选 **Read and write**（工作流已声明 `permissions: contents: write`，但组织级策略可能仍限制）
- 首次发布后，如需精简包在别人机器上可用，请确保对方已装 `nodejs python3 python3-pip ripgrep libvulkan1`（deb 的 `Depends` 已声明，apt 会自动装）
- 运行器 `ubuntu-latest` 是 x86_64，与 `Architecture: amd64` 匹配；`strip` 目标一致

### 9.4 合规提示

本仓库为**独立、非官方**项目，与腾讯公司无任何隶属或授权关系，**仓库本身不托管任何官方二进制**：
原始 deb 由工作流在运行时从腾讯官方渠道下载，处理后仅做体积优化（软链、删冗余、strip），
不修改、不逆向、不绕过任何功能或授权逻辑。

**使用者须自行确认**其下载、安装与分发行为符合腾讯的服务条款、EULA 及当地法律法规。
完整的免责与责任限制条款见仓库根目录 `DISCLAIMER.md` 与 `README.md` 的「合规与免责声明」章节。
工作流文件顶部已写入对应提示注释。

---

## 10. 上游更新接口的坑（实测）

### 10.1 接口

```
GET https://copilot.tencent.com/v2/update?platform=workbuddy-linux-x64-deb
```

返回（2026-10-12 实测）：

```json
{
  "version": "5.5.6.38337834",
  "url": "https://download.codebuddy.cn/workbuddy/saas/linux-x64-deb/WorkBuddy-linux-x64-deb-5.5.6.38337834-5f969292.deb",
  "productVersion": "5.5.6.38337834",
  "sha256hash": "03d756b259d7086c22098fa077589a032d60948d1de7313473360eefe11e240f",
  "timestamp": 1789061034,
  "supportsFastUpdate": false
}
```

`platform` 参数有效（换成 `workbuddy-darwin-arm64` 会返回 5.7.7 的 macOS 包），无效值返回空。

### 10.2 ⚠️ `sha256hash` 字段不可信

实测证据：

| 来源 | 值 |
| :--- | :--- |
| 接口 `sha256hash` | `03d756b2…e240f` |
| 实际下载文件 `sha256sum` | `2ef1bca2…df721` |
| 实际下载文件 `md5sum` | `a0ff5b3f…59828` |
| 对象存储元数据 `x-cos-meta-md5` | `a0ff5b3f…59828` ✅ 一致 |

即：**下载文件本身完整无误（大小 429302312 字节、md5 与 COS 元数据完全吻合、CDN 与回源一致），但接口给的 `sha256hash` 并不是这个文件的 sha256。**

→ **不要在 CI 里用 `sha256hash` 做硬校验，否则每次都会失败。** 本工作流的做法是：

1. 把不一致降级为 `::warning::`（不阻断，但留痕）
2. 用 **`dpkg-deb --info` 验证 ar 结构合法**
3. 用 **`DEBIAN/control` 的 `Version` 与接口 `version` 做交叉校验**（接口是 `5.5.6.38337834`，deb 内是 `5.5.6`，判据为「接口版本以 deb 版本开头」）

### 10.3 版本号的两套体系

- 接口 `version` / `productVersion`：**四段**，如 `5.5.6.38337834`
- deb `DEBIAN/control` 里的 `Version`：**三段**，如 `5.5.6`
- 包内还有个**第三套**：`cli/vendor/sandbox/5.5.5/` —— 与 App 版本**不同步**（5.5.6 的包里沙箱还是 5.5.5）

**任何写死这三者中任意一个的脚本，都会在某个版本失效。** 第 8 章的通配方案正是为此。
