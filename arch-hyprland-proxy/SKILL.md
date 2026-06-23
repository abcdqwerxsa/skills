---
name: arch-hyprland-proxy
description: Use when on Arch Linux + Hyprland (or a minimal Wayland WM with wofi/rofi, no GNOME/KDE settings daemon) and any of these happen — installing clash-verge / clash-verge-rev / mihomo but GitHub or GitLab downloads fail mid-stream (curl 56 "unexpected eof while reading", git "RPC failed; curl 56", early EOF); enabling TUN mode / service mode that won't turn on; routing mainland-China traffic direct while the rest goes through the proxy (GEOIP CN / GEOSITE cn, 分流, 大陆直连); making a single app (Chrome/Chromium/Firefox) or the terminal use a SOCKS5/HTTP proxy when the "system proxy" toggle does nothing; launching a TUI app (yazi, btop, lazygit) from wofi and nothing happens; or Hyprland keybinds added to hyprland.conf silently don't take effect. Keywords: clash-verge, clash-verge-rev, mihomo, 7897, TUN, service mode, fake-ip, GEOIP CN, 分流, 系统代理无效, wofi 启动无反应, --proxy-server, hyprland.lua, xdg-terminal-exec, ghfast.top.
---

# Arch + Hyprland 代理工作流

## 核心认知(先记住这一条)

**Linux 没有统一的"系统代理"。** Windows 那种"拨一个开关,所有 App 自动走代理"在 Linux 上不存在。Clash 类客户端的"系统代理"开关,在纯 Wayland WM(Hyprland/Sway,没有 GNOME/KDE 设置守护进程)下基本是空操作。

所以要分场景各击破:

| 场景 | 走什么 | 本 skill 对应章节 |
|---|---|---|
| 装代理客户端本身 | GitHub/GitLab 被墙 → 镜像 | 一 |
| 全局无感(含 docker/系统服务) | TUN 模式 | 二 |
| 指定浏览器走代理 | 启动参数 `--proxy-server` | 三 |
| 指定终端走代理 | `http_proxy` 等环境变量 | 三 |
| TUI 程序从 wofi 启动没反应 | `Terminal=true` 桥接 | 四 |
| Hyprland 改快捷键不生效 | 权威配置是 `hyprland.lua` | 四 |

---

## 前提
- Arch Linux + Hyprland 0.55+(原生 Lua 配置);纯 Wayland WM(wofi/rofi 启动器,**无** GNOME/KDE 设置守护进程 → 没有"系统代理")。Sway 同理。
- 终端 `kitty`(脚本里写死了 kitty,用别的终端就相应替换)。
- AUR 助手 `yay` 或 `paru`。
- clash-verge-rev 已装或正要装,mixed-port 默认 **7897**。

## 一、GitHub/GitLab 被墙时装代理客户端

### 症状
`yay -S clash-verge-rev-bin` 报 `curl 56 OpenSSL SSL_read ... unexpected eof while reading` / `git RPC failed; curl 56` / `early EOF`,且**重试、改 git http 版本都没用**(因为连普通 `curl` 下载也在 17% 处断)。这是连接被中途重置,不是 git/HTTP2 问题。

### 解法:用国内镜像把文件先下好,再交给 makepkg

AUR 的 `-bin` 包本质就是"下载 deb/rpm → 重新打包成 pacman 包"。手动把那个 deb 用镜像下好放进去,makepkg 就不再联网:

```bash
# 1. 只拉 PKGBUILD,不构建
yay -G clash-verge-rev-bin
cd clash-verge-rev-bin

# 2. 从 PKGBUILD 读出准确的文件名和真实 URL
source ./PKGBUILD
name="${_pkgname}-${pkgver}-x86_64.deb"
realurl="${url}/releases/download/v${pkgver}/Clash.Verge_${pkgver}_amd64.deb"

# 3. 用镜像前缀下载,保存成 PKGBUILD 期望的名字(必须一字不差)
curl -L -o "$name" "https://ghfast.top/$realurl"

# 4. sha256 校验(对照官方 release 页给的哈希)
echo "<官方sha256>  $name" | sha256sum -c

# 5. 装运行依赖(从 Arch 官方源,快)
sudo pacman -S --needed webkit2gtk-4.1 gtk3

# 6. 构建+安装(本地已有文件,makepkg 不再下载)
makepkg -si
```

### 镜像前缀(随时可能失效,挨个试)
- 前缀型:`https://ghfast.top/`、`https://ghproxy.net/`、`https://mirror.ghproxy.com/` —— 用法 `https://ghfast.top/<原github链接>`(ghfast.top 偶尔回 403,换前缀即可)
- 换域名型:把 URL 里的 `github.com` 直接换成 `kkgithub.com`(不加前缀;只适合**手动改 URL**,不能用于下面的 insteadOf 重写)
- release tag 不确定时:去 release 页面右键 asset 复制真实链接,再套前缀

### 让 git clone 也走镜像(谨慎:全局且持久)
```bash
git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"
```
⚠️ 这是**全局、持久**的改写——代理关了或镜像挂了,所有 GitHub clone 会静默失败。用完还原:
```bash
git config --global --unset url."https://ghfast.top/https://github.com/".insteadOf
```
只想临时用一次(不动全局):
```bash
git -c url."https://ghfast.top/https://github.com/".insteadOf="https://github.com/" clone https://github.com/xxx/yyy.git
```

### ⚠️ 别装错包
`clash-verge-bin`(原版,2023 停更在 v1.3.8)会逼你从源码编译已废弃的 `webkit2gtk`/`libsoup`,巨坑。**装 `clash-verge-rev-bin`**(活跃维护的 fork,用官方仓库的 webkit2gtk-4.1/libsoup3)。

---

## 二、TUN 模式 + 大陆直连

### 2.1 装 Service(Linux 必踩坑)
TUN 需要 root 权限的 service。**点 GUI 里的"安装服务"没反应,是因为 sudo 密码框在桌面启动时弹不出来**。必须从终端启动客户端,再点安装:

```bash
pkill -f clash-verge       # 关掉已开的
clash-verge                # 从终端启动(不要 sudo)
# → GUI 里点"安装服务",切回终端输 [sudo] 密码
```

或手动(`clash-verge-rev-bin` 自带的安装命令,不是 /opt 下的脚本):
```bash
sudo clash-verge-service-install
sudo systemctl status clash-verge-service.service   # active (running) 即就位
```

### 2.2 大陆直连规则(等价 xray 的 geoip:cn direct)
绝大多数机场订阅**自带**大陆直连,先把模式设成"规则(Rule)"而非"全局",再去"连接"页看国内网站是不是 DIRECT。若要自己加,核心就两条:

```yaml
rules:
  - GEOSITE,private,DIRECT
  - GEOIP,private,DIRECT,no-resolve
  - GEOSITE,cn,DIRECT          # 大陆域名直连(放前面,先按域名过滤掉大部分)
  - GEOIP,CN,DIRECT            # 大陆 IP 直连(等价 xray geoip:cn)
  - MATCH,🚀 节点选择           # 其余全部走代理
```

**前提:`geoip.dat` / `geosite.dat` 必须存在**,否则 `GEOIP,CN` / `GEOSITE,cn` **静默失效**(规则看着在,实际不分流)。文件不在就去下(`find ~ -iname 'geoip.dat'`),或连上节点后让 app 自己拉。

### 2.3 TUN 要配 fake-ip DNS(IP 规则才生效)
TUN 开了但 DNS 不是 fake-ip,`GEOIP,CN` 这类 IP 规则匹配不准。标准配置:

```yaml
tun:
  enable: true
  stack: mixed                 # 不行换 system
  dns-hijack: [any:53]
  auto-route: true
  auto-detect-interface: true

dns:
  enable: true
  enhanced-mode: fake-ip       # 关键
  fake-ip-range: 198.18.0.1/16
  nameserver:
    - https://223.5.5.5/dns-query
    - https://1.12.12.12/dns-query
  fallback:
    - https://1.1.1.1/dns-query
    - https://8.8.8.8/dns-query
```

### 2.4 用 Merge 扩展配置,别直接改订阅
订阅每次更新会覆盖配置。正确做法:订阅页新建一个 **Merge** 类型配置,把上面的 `rules`/`tun`/`dns` 片段贴进去,关联到订阅(或设为全局扩展)。这样规则常驻、更新不丢。

---

## 三、分应用代理(无系统代理)

### 3.1 终端:环境变量
终端只认 `http_proxy`/`https_proxy`/`all_proxy`,**不读** gsettings。写到 `~/.bashrc`(zsh 用 `~/.zshrc`)做成开关函数:

```bash
proxy_on() {
  local p=http://127.0.0.1:7897
  export http_proxy=$p https_proxy=$p HTTP_PROXY=$p HTTPS_PROXY=$p
  export all_proxy=socks5://127.0.0.1:7897 ALL_PROXY=socks5://127.0.0.1:7897
  export no_proxy="localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16" NO_PROXY="$no_proxy"
}
proxy_off() { unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY no_proxy NO_PROXY; }
```

> 端口换成你 mixed-port 的实际值(clash-verge-rev 默认 **7897**)。查实际端口:
> `grep -r mixed-port ~/.local/share/io.github.clash-verge-rev.clash-verge-rev/config.yaml`
> `sudo` 不继承环境变量,要让 sudo 命令走代理用 `sudo -E`。

### 3.2 浏览器:启动参数(不读环境变量!)
**Chromium/Chrome/Firefox 都不读 `http_proxy` 环境变量**,纯 WM 下也不读 gsettings。Chrome 用启动参数:

```bash
google-chrome-stable --proxy-server="socks5://127.0.0.1:7897"
```

### 3.3 一键带代理的终端(包装脚本)
做个脚本,启动时就注入环境变量,不用每次手动 `proxy_on`:

```bash
#!/bin/sh
# ~/.local/bin/kitty-proxy —— 启动默认走代理(7897)的 kitty
p=http://127.0.0.1:7897
export http_proxy=$p https_proxy=$p HTTP_PROXY=$p HTTPS_PROXY=$p
export all_proxy=socks5://127.0.0.1:7897 ALL_PROXY=socks5://127.0.0.1:7897
export no_proxy="localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16" NO_PROXY="$no_proxy"
exec kitty --title 'kitty (proxy)'
```
`chmod +x` 后,绑一个快捷键(见四章)或做个 wofi 入口(见四章)来调用它。

---

## 四、Hyprland + wofi 落地(最容易踩的坑都在这)

### ⚠️ 坑 1:权威配置是 `hyprland.lua`,不是 `hyprland.conf`
Hyprland 0.55+ 支持**原生 Lua 配置**。若 `~/.config/hypr/hyprland.lua` 存在,它就是按键的权威来源;**在 `hyprland.conf` 里加 `bind=` 静默不生效**。判断:`hyprctl binds` 里所有绑定的 dispatcher 都是 `__lua`(正常现象,不是插件)。

加快捷键去 `hyprland.lua` 的 `KEYBINDINGS` 段:
```lua
local mainMod = "SUPER"
hl.bind(mainMod .. " + W", hl.dsp.exec_cmd("/home/<user>/.local/bin/kitty-proxy"))
```
改完 `hyprctl reload`。

### ⚠️ 坑 2:`.conf` 的 exec **不展开 `~`**
`bind = $mainMod, W, exec, ~/.local/bin/x` 会去找字面名叫 `~/.local/...` 的文件,找不到静默失败。**统一用绝对路径**(`/home/<user>/...`)。(`hyprland.lua` 的 `exec_cmd` 倒是会展开 `~`,但绝对路径最稳。)

### 坑 3:给某 App 做带代理的 wofi 入口
复制系统的 `.desktop` 到 `~/.local/share/applications/`(用户目录同名覆盖系统那份),**只改 `Exec` 和 `Terminal`,其余字段(`Name[xx]` 本地化名、`MimeType`、`Actions` 等)原样保留**——否则会丢掉"默认浏览器"关联和右键动作。下面只列关键字段:
```ini
# ~/.local/share/applications/google-chrome.desktop
[Desktop Entry]
Type=Application
Name=Google Chrome (Proxy)
Exec=/usr/bin/google-chrome-stable --proxy-server="socks5://127.0.0.1:7897" %U
Icon=google-chrome
Terminal=false
Categories=Network;WebBrowser;
```
```bash
update-desktop-database ~/.local/share/applications
```
这样只影响这一个 App,其它软件不动。要可选(有时走有时不走)就做两个入口(Name 区分)。

### 坑 4:wofi 启动 TUI 程序没反应
yazi/btop 这类 TUI 的 `.desktop` 是 `Terminal=true` + `Exec=yazi`。wofi 要靠 **`xdg-terminal-exec`** 才知道用哪个终端,没装就静默失败。

- **一劳永逸(稍麻烦)**:`xdg-terminal-exec` **不在官方仓库**,要 AUR 装 `yay -S xdg-terminal-exec`,而且还得配置 `~/.config/xdg-terminals.list` 指定默认终端,它才知道用哪个。
- **单点修(推荐,省事)**:覆盖 `.desktop` 用 kitty 直接跑——
```ini
# ~/.local/share/applications/yazi.desktop
[Desktop Entry]
Type=Application
Name=Yazi File Manager
Icon=yazi
Terminal=false
Exec=kitty yazi %f
Categories=System;FileManager;FileTools;ConsoleOnly
```

### ⚠️ 坑 5:从 wofi/快捷键用 `kitty <tui>` 启动,退出 TUI 会**关掉整个窗口**
因为 TUI 是 kitty 当时唯一在跑的进程,底下没有 shell。想让退出后落回 shell,把 Exec 改成:
```
Exec=kitty sh -ic 'yazi; exec $SHELL'
```
(`.desktop` 的 `Exec=` 里若含字面 `%` 要写成 `%%`;本例没有,可直接用。)

---

## 速查表

| 想做什么 | 怎么做 |
|---|---|
| GitHub 下载断 | `curl -L -o "$name" "https://ghfast.top/$realurl"` |
| 装 clash-verge | 用 `clash-verge-rev-bin`,别用 `clash-verge-bin` |
| 开 TUN | 装 service(终端启动客户端→GUI 安装→输 sudo)+ fake-ip DNS |
| 大陆直连 | `GEOSITE,cn,DIRECT` + `GEOIP,CN,DIRECT`(需 geoip.dat/geosite.dat) |
| 终端走代理 | `proxy_on`(env 变量)或 kitty-proxy 脚本 |
| 浏览器走代理 | `--proxy-server="socks5://127.0.0.1:7897"` 启动参数 |
| 加 Hyprland 快捷键 | 改 `hyprland.lua`,不是 `.conf`;`hyprctl reload` |
| .desktop 路径 | `~` 在 `.conf` exec 不展开 → 用绝对路径 |
| wofi 开 TUI 没反应 | 装 `xdg-terminal-exec`,或 `.desktop` 改 `Exec=kitty <app>` |

## 关键文件/路径
- `~/.config/hypr/hyprland.lua` —— Hyprland 权威配置(若存在)
- `~/.config/hypr/hyprland.conf` —— 旧式,按键改了不生效时别在这改
- `~/.local/bin/kitty-proxy` —— 带代理的终端启动脚本
- `~/.local/share/applications/*.desktop` —— 分应用入口(覆盖系统同名)
- clash-verge mixed-port 默认 **7897**
- 镜像前缀:`ghfast.top` / `ghproxy.net` / `kkgithub.com`

## 常见错误对照
| 现象 | 原因 | 解法 |
|---|---|---|
| `curl 56 unexpected eof` | 连接被中途重置(GitHub 被墙) | 用镜像前缀下载 |
| 点"安装服务"无反应 | sudo 框在桌面启动时弹不出 | 终端启动客户端再点 |
| Hyprland 改快捷键没反应 | 改了 `.conf` 而非 `.lua` | 改 `hyprland.lua` |
| Super+X 按了没反应 | `.conf` exec 用了 `~` | 换绝对路径 |
| 系统代理开关没用 | 纯 WM 无系统代理 | 分应用配(三/四章) |
| wofi 启动 TUI 没反应 | 没装 xdg-terminal-exec | 装它,或 `.desktop` 用 `kitty <app>` |
| 挂了代理的 App 连不上网 | clash 没运行 | 先开 clash |
| 规则没分流 | geoip.dat/geosite.dat 缺失 | 下好放进数据目录 |
