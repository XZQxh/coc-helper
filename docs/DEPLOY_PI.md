# 树莓派 7×24 部署

## 前提

- Raspberry Pi 4/5，建议 4GB 内存以上
- **64 位系统**：`uname -m` 必须是 `aarch64`；32 位系统跑不了 QQ NT
- Python 3.11+
- 能访问 `api.clashofclans.com` 和腾讯 QQ 服务

### 最重要的一条：token 绑定公网 IP

Supercell 的 API token 绑定的是**公网 IP**，不是机器。你的 Pi 和当前电脑如果不在同一个网络，现有 token **不能直接用**。

在 Pi 上查公网 IP：

```bash
curl -s https://api.ipify.org
```

然后到 https://developer.clashofclans.com 用这个 IP 新建 key/token，填到 Pi 的 `.env`。

如果 Pi 的公网 IP 会变化，token 会 403；没有 VPS 的情况下只能手动重建。先确认这一点，再决定是否迁移。

检查 API 是否可达：

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.clashofclans.com/v1
```

返回 `403` 也算通（没有 token 时的正常响应）；连接超时/000 才是网络问题。

## 安装

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip fonts-noto-cjk
git clone <你的仓库地址> COC-helper
cd COC-helper
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[bot]"
cp .env.example .env
```

编辑 `.env`：

- `COC_API_TOKEN`：Pi 公网 IP 新建的 token
- `COC_CLAN_TAG`：部落标签
- `ONEBOT_ACCESS_TOKEN`：NapCat 与 NoneBot 共用
- `DRIVER=~fastapi`、`HOST=127.0.0.1`、`PORT=8080` 保持默认即可

先验证数据源：

```bash
python -m coc_helper.cli verify
python -m coc_helper.cli war
```

## 安装 NapCat（Linux ARM64）

> NapCat 是第三方协议端，建议只用小号。首次登录需要扫码/设备验证。

官方安装器（arm64，apt/dnf）：

```bash
curl -fL --connect-timeout 20 --max-time 1800 \
  -o napcat.sh https://raw.githubusercontent.com/NapNeko/NapCat-Installer/main/script/install.sh
bash napcat.sh --docker n --cli y --github-proxy 0
```

GitHub 访问不稳定时，把 `--github-proxy 0` 换成可用的加速地址。安装后按提示运行 `napcat` 管理服务，登录小号并打开 WebUI。

在 NapCat WebUI 的“网络配置”里新建：

- 类型：`WebSocket 客户端`（反向 WS）
- URL：`ws://127.0.0.1:8080/onebot/v11/ws`
- Token：与 `.env` 的 `ONEBOT_ACCESS_TOKEN` 一致

NapCat 与 NoneBot 在同一台 Pi 上，所以用 `127.0.0.1`；不需要公网入站端口。

## systemd 守护 bot

```bash
sudo cp deploy/coc-helper.service /etc/systemd/system/coc-helper.service
sudo nano /etc/systemd/system/coc-helper.service
```

把 `User`、`WorkingDirectory`、`ExecStart` 改成你的用户名和路径，然后：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now coc-helper
sudo systemctl status coc-helper
journalctl -u coc-helper -f
```

NapCat 安装器一般会生成自己的服务；如果没有，用 `systemd` 或 `screen` 让它常驻。NapCat 会每 30 秒重连 NoneBot，启动顺序不敏感。

## 7×24 注意事项

- **不要同时跑两个 bot**：8080 只能被一个进程监听
- **SQLite**：`data/coc.db` 是唯一数据源，定期备份；WAL 模式已开启
- **SD 卡**：长期写日志/数据库，建议用 USB SSD；至少限制 journald 大小
- **时间同步**：`timedatectl` 确认 NTP 正常；时间错会影响战争计时
- **内存**：QQ NT 约占 300–500MB，Pi 4GB 足够；2GB 建议开 zram/swap
- **QQ 账号**：首次登录可能触发设备验证；NapCat 被踢下线后需要重新扫码
- **token/IP**：IP 变化会 403；重建 key 后替换 `.env` 并重启 bot
- **升级**：`git pull && source .venv/bin/activate && pip install -e ".[bot]" && sudo systemctl restart coc-helper`

## 排错

| 现象 | 排查 |
|---|---|
| `403` / `accessDenied` | token 是否绑定 Pi 当前公网 IP；是否过期 |
| `Connection refused` | bot 没启动，或 URL 端口不是 8080 |
| `401` / `403` WebSocket | NapCat 与 `.env` 的 `ONEBOT_ACCESS_TOKEN` 不一致 |
| 字体方框 | 安装 `fonts-noto-cjk`，或设置 `COC_FONT=/path/to/font.ttc` |
| bot 不回消息 | 看 NapCat 控制台是否收到消息；`journalctl -u coc-helper -f` |
