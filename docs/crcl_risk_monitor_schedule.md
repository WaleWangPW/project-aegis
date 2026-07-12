# CRCL Risk Monitor Daily Schedule

## 概述

本文档说明如何每日自动刷新 CRCL 风险监控报告，确保手机页面显示最新数据。

## 数据文件

### 输入文件（已存在）
- `data/reports/crcl_risk_monitor_latest.json` - JSON 格式风险监控报告
- `data/reports/crcl_risk_monitor_latest.md` - Markdown 格式风险监控报告
- `project-aegis/recommendation_details.json` - 推荐详情（Stock Agent 镜像）
- `data/records/signals.jsonl` - 信号记录
- `data/records/expert_opinions.jsonl` - 专家意见记录
- `data/records/decisions.jsonl` - 决策记录

### 输出文件
- `data/reports/crcl_risk_monitor_latest.json` - 风险监控 JSON 报告
- `data/reports/crcl_risk_monitor_latest.md` - 风险监控 Markdown 报告

## 刷新脚本

### 脚本路径
`scripts/update_crcl_risk_monitor.py`

### 运行命令
```bash
cd /Users/weihongwang/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo
python scripts/update_crcl_risk_monitor.py
```

### 脚本功能
1. 读取 recommendation_details.json 获取 CRCL 当前状态
2. 读取 signals.jsonl 获取最新风险指标
3. 读取 expert_opinions.jsonl 获取专家立场
4. 读取 decisions.jsonl 获取决策信息
5. 生成 crcl_risk_monitor_latest.json 报告
6. 生成 crcl_risk_monitor_latest.md 报告
7. 更新报告时间戳

## 调度方式

### 选项 1: Cron（推荐）
```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天上午 8:00 执行）
0 8 * * * cd /Users/weihongwang/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo && python scripts/update_crcl_risk_monitor.py >> /tmp/crcl_risk_monitor.log 2>&1
```

### 选项 2: Launchd（macOS）
创建 `~/Library/LaunchAgents/com.aegis.crcl-risk-monitor.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aegis.crcl-risk-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3</string>
        <string>/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo/scripts/update_crcl_risk_monitor.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/crcl_risk_monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/crcl_risk_monitor.err</string>
</dict>
</plist>
```

加载 Launchd：
```bash
launchctl load ~/Library/LaunchAgents/com.aegis.crcl-risk-monitor.plist
```

## 建议方式

**推荐使用 Cron**，因为：
- 配置简单，易于调试
- 不需要创建额外的 plist 文件
- 日志输出便于排查问题

## 数据更新依赖

CRCL 风险监控报告依赖于以下流程：
1. Project Aegis 主流程生成 recommendation_details.json
2. scripts/refresh_stock_agent_aegis_status.py 同步到 Stock Agent 工作区
3. scripts/update_crcl_risk_monitor.py 从推荐详情生成风险报告

建议调度顺序：
- 06:00 - Project Aegis 主流程（如果有定时任务）
- 06:30 - scripts/refresh_stock_agent_aegis_status.py
- 07:00 - scripts/update_crcl_risk_monitor.py

## 监控和调试

### 检查日志
```bash
tail -f /tmp/crcl_risk_monitor.log
```

### 手动测试
```bash
python scripts/update_crcl_risk_monitor.py --verbose
```

### 验证文件更新
```bash
ls -la data/reports/crcl_risk_monitor_latest.*
```

### 手机页面验证
访问 http://localhost:8080/dashboard/index.html 查看最新状态

## 手机页面读取

手机页面通过内嵌的 JSON 数据读取 CRCL 风险监控信息，不需要额外的 API 调用。当以下文件更新后：
- data/reports/crcl_risk_monitor_latest.json
- data/reports/crcl_risk_monitor_latest.md

手机页面刷新即可显示最新数据。

---

最后更新: 2026-07-09  
文档版本: 1.0  
维护者: Project Aegis Team

## 通用股票风险监控框架 (P7)

### 概述
从 CRCL 专用脚本抽象为通用股票风险监控框架，支持多股票监控。

### 脚本架构

#### 通用脚本
- `scripts/update_stock_risk_monitor.py` - 通用股票风险监控脚本
  - 支持任意股票代码
  - 动态生成报告文件名
  - 可扩展到多股票

#### 兼容脚本
- `scripts/update_crcl_risk_monitor.py` - CRCL 专用兼容包装器
  - 保持向后兼容
  - 调用通用脚本

### 使用方式

#### 通用脚本用法
```bash
# 为任意股票生成风险报告
python scripts/update_stock_risk_monitor.py --symbol CRCL --verbose
python scripts/update_stock_risk_monitor.py --symbol AAPL --verbose
```

#### 兼容脚本用法
```bash
# 原有命令继续有效
python scripts/update_crcl_risk_monitor.py --verbose
```

### 输出文件路径

#### 通用脚本输出
- `data/reports/{symbol_lower}_risk_monitor_latest.json`
- `data/reports/{symbol_lower}_risk_monitor_latest.md`

#### CRCL 专用输出
- `data/reports/crcl_risk_monitor_latest.json`
- `data/reports/crcl_risk_monitor_latest.md`

### Cron 调度

#### 现有 CRCL 任务（保持不变）
```bash
0 8 * * * cd "/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo" && /usr/bin/python3 scripts/update_crcl_risk_monitor.py --verbose >> /tmp/crcl_risk_monitor.log 2>&1
```

#### 多股票扩展示例
```bash
# 每天早上 8 点监控多只股票
0 8 * * * cd "/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo" && /usr/bin/python3 scripts/update_stock_risk_monitor.py --symbol CRCL --verbose >> /tmp/stock_risk_monitor.log 2>&1 && /usr/bin/python3 scripts/update_stock_risk_monitor.py --symbol AAPL --verbose >> /tmp/stock_risk_monitor.log 2>&1
```

### 向后兼容性

- ✅ 原有 `update_crcl_risk_monitor.py` 命令保持有效
- ✅ 现有 cron 任务无需修改
- ✅ CRCL 报告文件路径保持不变
- ✅ 手机页面无需更新

### 扩展性

要为其他股票添加监控：
1. 使用通用脚本：`python scripts/update_stock_risk_monitor.py --symbol NEWSTOCK --verbose`
2. 添加相应的 cron 任务
3. 更新手机页面（如需要显示新股票）

---

通用框架更新: 2026-07-09  
框架版本: 2.0  
维护者: Project Aegis Team
