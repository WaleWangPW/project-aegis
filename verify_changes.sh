#!/bin/bash

echo "=== Project Aegis P17 验证报告 ==="
echo ""
echo "1. 配置文件检查:"
if [ -f "./data/reports/risk_monitor_symbols.json" ]; then
    echo "   ✓ risk_monitor_symbols.json 已创建"
    echo "   内容:"
    cat ./data/reports/risk_monitor_symbols.json | sed 's/^/   /'
else
    echo "   ✗ risk_monitor_symbols.json 未找到"
fi

echo ""
echo "2. 数据文件检查:"
for file in $(jq -r '.[].report_file' ./data/reports/risk_monitor_symbols.json); do
    if [ -f "./data/reports/$file" ]; then
        echo "   ✓ ./data/reports/$file 存在 ($(stat -f%z "./data/reports/$file") bytes)"
    else
        echo "   ✗ ./data/reports/$file 不存在"
    fi
done

echo ""
echo "3. HTML 文件修改检查:"
if grep -q "loadStockConfigAndData" ./dashboard/index.html; then
    echo "   ✓ index.html 包含动态加载函数"
else
    echo "   ✗ index.html 缺少动态加载函数"
fi

if grep -q "risk_monitor_symbols.json" ./dashboard/index.html; then
    echo "   ✓ index.html 包含配置文件引用"
else
    echo "   ✗ index.html 缺少配置文件引用"
fi

echo ""
echo "4. 移动设备兼容性检查:"
if grep -q "monitored-stocks-display" ./dashboard/index.html; then
    echo "   ✓ index.html 包含动态股票显示元素"
else
    echo "   ✗ index.html 缺少动态股票显示元素"
fi

echo ""
echo "5. 验证完成!"
echo ""
echo "注意: 要实际运行页面，请使用命令:"
echo "cd /Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo && python3 -m http.server 8081"
echo ""
echo "然后访问 http://localhost:8081/dashboard/index.html 查看配置化的风险监控页面"
