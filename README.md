# WorkBuddy Linux DEB 精简流水线

自动跟随上游版本，把腾讯官方 **WorkBuddy Desktop (Linux x64) DEB** 重新打包为精简版并发布到 GitHub Release。

| 维度 | 官方原始 | 精简后 | 变化 |
| :--- | ---: | ---: | ---: |
| DEB 体积 | 409.4 MB | **256.1 MB** | **-37.4%** |
| 解压安装占用 | 1.6 GB | **853.4 MB** | **-47.7%** |
| 语言包 | 55 个 | 4 个 | -51 |
| 断链 | — | 0 | ✅ |

## 工作原理

GitHub Actions 每天定时（UTC 03:00）调用上游更新接口：

```
GET https://copilot.tencent.com/v2/update?platform=workbuddy-linux-x64-deb
```

拿到最新版本的下载地址 → 校验 → 精简重打包 → 发布为 Release（tag = `v<version>`）。
已发布过的版本会跳过，不会重复构建。

## 精简范围与策略（四大支柱）

本项目遵循**“避免系统已有组件重复、剔除跨平台与构建残留、精简冗余语言与文档、去调试符号”**原则，在 100% 保持应用功能完整的前提下实现体积减半。

### 1. 精简范围与收益账单

| 精简维度 | 官方原版状态 | 精简处理方案 | 体积变化 / 收益 |
| :--- | :--- | :--- | :--- |
| **Node.js 运行时** | 自带 Node v22 运行时树与 65MB C++ 头文件 | 清空整目录，软链至系统 `/usr/bin/node` | **203 MB $\to$ 0 MB** |
| **Python 运行时** | 自带 Python 3.13 解释器、239MB 调试动态库与 Tcl/Tk | 清空整目录，软链至系统 `/usr/bin/python3` 与 `pip3` | **399 MB $\to$ 0 MB** |
| **Ripgrep 检索工具** | 自带独立 `rg` 二进制文件 | 软链至系统 `/usr/bin/rg` | **12 MB $\to$ 0 MB** |
| **Vulkan Loader** | 自带 `libvulkan.so.1` 动态库 | 软链至系统 `/usr/lib/x86_64-linux-gnu/libvulkan.so.1` | **2.2 MB $\to$ 0 MB** |
| **多语言本地化包** | 56 种语言 `.pak` 文件（含大量生僻小语种） | **仅保留中英文**（`zh-CN`, `zh-TW`, `en-US`, `en-GB`），移除其余 51 个小语种 | **42 MB $\to$ 2.5 MB**（省 ~39.5 MB） |
| **开源许可证网页** | 15.27 MB 静态纯 HTML 展示页 (`LICENSES.chromium.html`) | 替换为标准化简要版权声明 HTML（203 字节） | **15.3 MB $\to$ 203 B**（省 ~15.2 MB） |
| **源码映射 SourceMap** | 包含 379 个前端/Node 调试映射文件 (`*.map`) | 生产环境安全移除全部 `*.map` | **2.3 MB $\to$ 0 MB** |
| **异构跨平台残留** | 混入 Windows / macOS / ARM / BSD / musl 产物 | 彻底清除所有非 Linux-x64 平台文件与预编译库 | **节省 ~50 MB** |
| **源码与编译中间件** | 包含 C/C++ 源码（如 `sqlite3.c`）、头文件与 `.o` / `.a` 静态库 | 移除编译残留与开发源码，去重重复的原生 `.node` 副本 | **节省 ~7 MB** |
| **二进制调试符号** | `editor_sdk` 及原生模块未执行 strip | 执行 `strip --strip-unneeded` 去除符号表 | **节省 ~35 MB** |

---

### 2. 精简详细范围清单

#### 模块一：复用系统运行时与基础依赖（杜绝 deb 内重复打包）
- **`resources/runtime/node/`**：官方打包了完整的 Node.js 安装树。精简流水线清空该目录（移除全部自带动态库、文档与 65MB 的 `include/node` 开发头文件），仅保留 `bin/node` 与 `bin/nodejs` 软链指向 `/usr/bin/node`。
- **`resources/runtime/python/`**：官方打包了全套 Python 3.13 解释器、未 strip 的 239MB `libpython3.13.so.1.0` 调试库、109MB `python3.13` 二进制以及 Tcl/Tk 依赖。精简流水线清空该目录，仅建立 `bin/python3` $\to$ `/usr/bin/python3`，`bin/python` $\to$ `python3`，`bin/pip3` $\to$ `/usr/bin/pip3`，`bin/pip` $\to$ `pip3` 软链接。
- **`cli/vendor/ripgrep/*/rg`**：替换为指向系统 `/usr/bin/rg` 的软链接。
- **`libvulkan.so.1`**：替换为指向系统 `/usr/lib/x86_64-linux-gnu/libvulkan.so.1` 的软链接。
- **DEB 依赖自动声明**：在 `DEBIAN/control` 的 `Depends` 字段自动追加 `nodejs, python3, python3-pip, ripgrep, libvulkan1`，由 APT 自动满足系统组件。

#### 模块二：剔除非 Linux-x64 的跨平台异构残留
- **`node_modules/koffi`**：官方打包了 18 种系统架构。精简后**仅保留 `build/koffi/linux_x64/`**，彻底删除其余 17 个异构平台（`darwin_arm64`, `darwin_x64`, `win32_arm64`, `win32_ia32`, `win32_x64`, `freebsd_arm64`, `freebsd_ia32`, `freebsd_x64`, `openbsd_ia32`, `openbsd_x64`, `linux_arm64`, `linux_armhf`, `linux_ia32`, `linux_loong64`, `linux_riscv64d`, `musl_arm64`, `musl_x64`）。
- **`node-pty` 与 `@lydell/node-pty-*`**：删除 `prebuilds/darwin-*`, `prebuilds/win32-*`, `prebuilds/linux-arm64`，仅保留 `linux-x64`。
- **`weixinpay` 插件**：删除 `prebuilds/darwin-*`, `prebuilds/win32-*`。
- **`cli/bin/native/`**：删除 `win32-arm64`, `win32-x64` 以及 Windows 进程抑制脚本（`*.bunfig.toml`, `*.cjs`）。
- **`cli/vendor/`**：删除 macOS 专用工具 `toybox-macos`, `zsh-macos`，删除 `shim/native/darwin-*`, `shim/native/win32-*`。
- **系统专属与源码**：删除 macOS 专用监控模块 `node_modules/fsevents`，删除 `qimei-node/src/win` 和 `src/mac`。

#### 模块三：多语言、无用文档与开发产物清理
- **本地化语言包 (`locales/`)**：
  - **保留白名单**：`zh-CN.pak`（简体中文）、`zh-TW.pak`（繁体中文）、`en-US.pak`（美式英文）、`en-GB.pak`（英式英文）。
  - **裁减清单**：删除泰米尔语、马拉雅拉姆语、卡纳达语、印地语、泰语、希腊语、波斯语、阿拉伯语等共计 51 个非中英小语种 `.pak` 文件（释放近 40 MB 空间）。
- **静态许可文档 (`LICENSES.chromium.html`)**：官方自带的纯展示 HTML 体积高达 15.27 MB，替换为合规简短声明，释放 15 MB 静态空间。
- **Source Map 映射**：删除 `app.asar.unpacked` 内所有 `*.map` 前端调试文件（379 个，2.32 MB）。
- **编译残留与开发源码**：
  - 删除 `better-sqlite3` 与 `koffi` 内部的 `src/`、`deps/`（包括 `sqlite3.c`, `sqlite3.h` 等编译源码/头文件）、`doc/`。
  - 删除构建目标中间件 `better-sqlite3/build/Release/obj/`, `obj.target/`, `sqlite3.a` 静态库（~20 MB 编译残留）。
- **原生模块副本去重**：`better-sqlite3` 在 `bin/linux-x64-136/` 与 `build/Release/` 打包了两份相同的 `better_sqlite3.node`，替换为相对软链接，消除一份副本（省 2 MB）。

#### 模块四：二进制与原生模块 Strip（去符号表）
对保留的 ELF 可执行文件与所有 `.node` 原生插件执行 `strip --strip-unneeded`：
- `editor_sdk`（文档 AI 引擎核心）：从 225.15 MB $\to$ 192.93 MB（**单项缩减 32.2 MB**）；
- `betterleaks`、`sandbox-center`、`sandbox-cli`、`sandbox-cli-gc`、`wb-bridge`；
- 所有 `.node` 原生模块插件。

---

### 3. 安全边界与保留原则（不精简项）

为了保证应用在各种运行场景下的健壮性与功能 100% 完整，以下内容**明确保持原样，绝不裁减**：

1. **绝对不篡改 `app.asar` 主体**：
   - 历史踩坑教训表明，手动解包并重构 `app.asar` 极易破坏 Chromium Pickle 二进制 Header 规范（例如末尾多写入补齐字节 `\x00`），触发 Electron 原生崩溃：
     `[ERROR:electron/shell/common/asar/archive.cc:260] Failed to parse header`。
   - 所有精简均在 `resources/runtime/`、`resources/app.asar.unpacked/`、`locales/` 和顶层二进制中进行，严禁破坏 ASAR 归档。
2. **不全局粗暴删除 `*.md` 文档**：
   - WorkBuddy 的插件与内置 Agent Skills（如 `skill-creator`, `tencent-docx`, `sheetagent` 等）包含大量供 AI 智能体工作流执行读取的 system prompt 与操作规约（Markdown 格式），误删将导致智能体工作流异常，因此脚本仅清理开发包源码目录的文档，完整保留业务 Skills Markdown。
3. **保留底层图形与音视频兼容库**：
   - `libvk_swiftshader.so`（软件 Vulkan 渲染，纯无头服务器或虚拟机保底兼容必需）；
   - `libffmpeg.so`（Chromium 定制流媒体解复用库）；
   - `icudtl.dat`（Unicode 国际化数据资产包）。

## 本地使用

```bash
# 依赖：dpkg-deb / xz-utils / binutils(strip) / python3
python3 scripts/slim_workbuddy.py \
  WorkBuddy-linux-x64-deb-5.5.6.38337834-5f969292.deb \
  out/WorkBuddy-linux-x64-deb-5.5.6-trimmed.deb
```

常用参数：

| 参数 | 说明 |
| :--- | :--- |
| `--compress xz\|zstd\|gzip\|none` | 打包压缩算法，默认 `xz` |
| `--self-contained` | 不软链系统运行时，保持官方自带（此时不追加系统依赖） |
| `--no-strip` | 跳过二进制 strip（未装 binutils 时） |
| `--workdir DIR` / `--keep-workdir` | 指定/保留解包工作目录（调试） |

脚本会**自动从 `DEBIAN/control` 读取版本号**来命名产物，并对所有与版本相关的路径使用通配匹配，
因此新版本无需改代码。

## 安装精简包

```bash
sudo apt install ./WorkBuddy-linux-x64-deb-<version>-trimmed.deb
```

用 `apt` 而非 `dpkg -i`，以便自动安装 `nodejs python3 python3-pip ripgrep libvulkan1` 依赖。

## 仓库结构

```
.
├── .github/workflows/slim-deb.yml   # 定时拉取 → 精简 → 发布 Release
├── scripts/slim_workbuddy.py        # 版本无关的精简流水线（核心）
├── docs/
│   ├── WORKBUDDY_DEB_SLIMMING_GUIDE.md   # 完整策略、避坑、接口坑说明
│   ├── legacy_trim_package.py            # 历史脚本（阶段一，已弃用）
│   └── legacy_trim_stage2.py             # 历史脚本（阶段二，已弃用）
├── README.md        # 本文件
├── DISCLAIMER.md    # 合规与免责声明（完整版）
├── LICENSE          # MIT（仅覆盖本仓库原创脚本与文档）
└── .gitignore
```

## 合规与免责声明

> 使用、克隆、分发或以任何方式利用本仓库及其产出物，即视为你已阅读、理解并同意以下全部条款。
> 若不同意任一条款，请立即停止使用并删除相关内容。
>
> 📄 **完整版本（含英文摘要）见 [`DISCLAIMER.md`](DISCLAIMER.md)。**

### 1. 项目性质

本仓库是**独立、非官方**的开源技术项目，与腾讯公司及其关联方**无任何隶属、合作、赞助或授权关系**。
仓库中不包含、不托管、不分发任何腾讯 WorkBuddy 官方安装包或其二进制文件。

仓库提供的**仅是一组体积优化脚本、构建配置与配套文档**。所有原始安装包均由使用者或
自动化流水线在运行时**自行从腾讯官方发布渠道下载**，相关文件的著作权及相关权利始终归
腾讯科技（深圳）有限公司及其许可方所有。

### 2. 产出物说明

本仓库的自动化流程会从官方渠道获取安装包，并对其进行**纯粹的体积优化处理**，包括：

- 将重复捆绑的运行时（Node.js / Python / ripgrep / Vulkan 库）替换为指向系统同级组件的软链接；
- 删除与目标平台（Linux x64）无关的跨平台冗余文件、多余语言包、sourcemap 与编译中间产物；
- 对二进制文件执行 `strip` 以移除调试符号。

上述处理**不修改、不反编译、不逆向、不混淆、不破解**任何程序的业务逻辑、功能实现或授权机制，
不改变程序的任何运行行为与授权校验路径，亦不用于绕过任何技术保护措施或访问控制。
产出物与官方原版在**功能上完全一致**。

### 3. 免责声明

**本项目按「现状」提供，不附带任何形式的明示或默示担保**，包括但不限于对适销性、
特定用途适用性及不侵权的担保。

在法律允许的最大范围内，本项目的作者与贡献者**不对任何直接、间接、附带、特殊、
惩罚性或间接性损害承担责任**，包括但不限于数据丢失、设备损坏、业务中断、利润损失或
任何其他损害，无论其如何引起、基于何种责任理论，也无论是否已被告知此类损害的可能性。

具体而言（但不限于）：

- 不对产出物的**完整性、可用性、安全性或兼容性**作任何保证；
- 不对因使用产出物而导致的**任何系统故障、数据损坏或功能异常**承担责任；
- 不对使用者**违反任何第三方许可协议或服务条款**的行为承担责任；
- 不对上游接口、下载地址或版本信息的**可用性与准确性**作任何保证；
- **不承诺**持续维护、更新或修复本项目。

### 4. 使用者责任

使用者**须自行承担**使用本项目的全部风险，并**须自行确认**其行为符合以下全部要求：

1. 已获得腾讯 WorkBuddy 官方安装包的**合法来源与使用授权**；
2. 其对本仓库脚本的使用、对产出物的下载与安装，**不违反**腾讯的服务条款、
   最终用户许可协议（EULA）及任何其他适用协议；
3. 符合其所处**国家和地区的全部适用法律法规**；
4. 已充分理解**在公开仓库中重新分发官方专有软件可能构成侵权行为**，
   并自行决定是否以及如何分发产出物、独自承担由此产生的一切后果。

**特别提示**：将本仓库设为公开，会使他人能够获取由官方专有软件生成的产出物。
本仓库作者不对任何使用者的分发行为承担责任，亦不构成对任何分发行为的授权、认可或鼓励。

### 5. 权利主张与下架

我们**充分尊重知识产权**。若任何权利人认为本仓库的内容或产出物侵犯了其合法权益，
请通过仓库 Issue 或下述联系方式与我们沟通。我们将在核实后**立即采取删除、下架或
停止分发等相应措施**，并配合权利人的合理要求。

### 6. 条款变更

本声明可能随项目发展而不时更新，更新后的版本自发布于本仓库之日起生效。
使用者应自行留意最新版本。

## 许可

本项目自身的脚本与文档采用 **MIT 许可**（见 [`LICENSE`](LICENSE)）。

该许可**仅覆盖本仓库原创的脚本与文档**，**不包含、不授予**任何腾讯 WorkBuddy 官方二进制
或其衍生产物的任何权利。官方二进制的著作权及相关权利归
腾讯科技（深圳）有限公司及其许可方所有，并受其自身服务条款与许可协议约束。
