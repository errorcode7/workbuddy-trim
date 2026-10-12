# 合规与免责声明 / Compliance & Disclaimer

> **本文件是 `README.md` 中「合规与免责声明」章节的完整版本。**
> 使用、克隆、分发或以任何方式利用本仓库及其产出物，即视为你已阅读、理解并同意以下全部条款。
> 若不同意任一条款，请立即停止使用并删除相关内容。
> 中文版本为原始文本；如有译文出入，以中文版本为准。

---

## 1. 项目性质

本仓库是**独立、非官方**的开源技术项目，与腾讯公司及其关联方**无任何隶属、合作、赞助或授权关系**。

仓库中**不包含、不托管、不分发**任何腾讯 WorkBuddy 官方安装包或其二进制文件。仓库提供的
**仅是一组体积优化脚本、构建配置与配套文档**。所有原始安装包均由使用者或自动化流水线在
运行时**自行从腾讯官方发布渠道下载**，相关文件的著作权及相关权利始终归
腾讯科技（深圳）有限公司及其许可方所有。

## 2. 产出物说明

本仓库的自动化流程会从官方渠道获取安装包，并对其进行**纯粹的体积优化处理**，包括：

| 处理方式 | 具体内容 |
| :--- | :--- |
| 依赖复用 | 将重复捆绑的运行时（Node.js / Python / ripgrep / Vulkan 库）替换为指向系统同级组件的软链接 |
| 冗余删除 | 删除与目标平台（Linux x64）无关的跨平台文件、多余语言包、sourcemap 与编译中间产物 |
| 符号剥离 | 对二进制文件执行 `strip`，移除调试符号 |

上述处理**不修改、不反编译、不逆向、不混淆、不破解**任何程序的业务逻辑、功能实现或
授权机制，不改变程序的运行行为与授权校验路径，亦不用于绕过任何技术保护措施或访问控制。
产出物与官方原版在**功能上完全一致**。

## 3. 免责声明

**本项目按「现状」（AS IS）提供，不附带任何形式的明示或默示担保**，包括但不限于对
适销性、特定用途适用性及不侵权的担保。

在法律允许的最大范围内，本项目的作者与贡献者**不对任何直接、间接、附带、特殊、
惩罚性或间接性损害承担责任**，包括但不限于数据丢失、设备损坏、业务中断、利润损失或
任何其他损害，无论其如何引起、基于何种责任理论，也无论是否已被告知此类损害的可能性。

具体而言（但不限于）：

- 不对产出物的**完整性、可用性、安全性或兼容性**作任何保证；
- 不对因使用产出物而导致的**任何系统故障、数据损坏或功能异常**承担责任；
- 不对使用者**违反任何第三方许可协议或服务条款**的行为承担责任；
- 不对上游接口、下载地址或版本信息的**可用性与准确性**作任何保证；
- **不承诺**持续维护、更新或修复本项目。

## 4. 使用者责任

使用者**须自行承担**使用本项目的全部风险，并**须自行确认**其行为符合以下全部要求：

1. 已获得腾讯 WorkBuddy 官方安装包的**合法来源与使用授权**；
2. 其对本仓库脚本的使用、对产出物的下载与安装，**不违反**腾讯的服务条款、
   最终用户许可协议（EULA）及任何其他适用协议；
3. 符合其所处**国家和地区的全部适用法律法规**；
4. 已充分理解**在公开仓库中重新分发官方专有软件可能构成侵权行为**，
   并自行决定是否以及如何分发产出物、独自承担由此产生的一切后果。

**特别提示**：将本仓库设为公开，会使他人能够获取由官方专有软件生成的产出物。
本仓库作者与贡献者不对任何使用者的分发行为承担责任，亦不构成对任何分发行为的
授权、认可或鼓励。

## 5. 权利主张与下架（Notice and Takedown）

我们**充分尊重知识产权**。若任何权利人认为本仓库的内容或产出物侵犯了其合法权益，
请通过仓库 Issue 或下述联系方式与我们沟通，并提供必要的权属证明。我们将在核实后
**立即采取删除、下架或停止分发等相应措施**，并配合权利人的合理要求。

我们无意侵犯任何人的权利。若本项目的任何部分存在权利瑕疵，请告知，我们会立即处理。

## 6. 无担保与责任限制的独立性

若本声明的任何条款被有管辖权的法院认定为无效或不可执行，该条款应在最小必要范围内
被限缩或删除，其余条款仍应保持完全效力。本声明中关于担保排除与责任限制的条款，
即使在本项目终止或你停止使用后，仍持续有效。

## 7. 条款变更

本声明可能随项目发展而不时更新，更新后的版本自发布于本仓库之日起生效。
使用者应自行留意最新版本。

---

## English Summary (for reference only)

This repository is an **independent, unofficial** project and is **not affiliated
with, endorsed by, or sponsored by Tencent**. It contains **no Tencent binaries** —
only scripts, build configuration and documentation. Official installers are
downloaded at runtime, directly from Tencent's own distribution channels, by the
user or the automation pipeline.

The scripts perform **size optimization only** (symlinking duplicated runtimes,
removing cross-platform/irrelevant files, and stripping debug symbols). They do
**not** modify, decompile, reverse-engineer, obfuscate, or circumvent the
functionality, logic, or licensing mechanisms of any software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. THE AUTHORS AND
CONTRIBUTORS SHALL NOT BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR ITS USE.

**Users are solely responsible** for ensuring that their use of this repository and
any artifacts it produces complies with all applicable third-party agreements
(including Tencent's terms of service and EULA) and all applicable laws.

We respect intellectual property rights. If you believe any content infringes your
rights, please contact us via the repository's Issue tracker and we will act
promptly.

*The Chinese version above is the authoritative text; this English summary is
provided for reference only.*
