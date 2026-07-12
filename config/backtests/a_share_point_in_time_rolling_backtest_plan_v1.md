# A股 Point-in-Time 滚动回测计划 V1

## 概述
本计划定义了 A股市场的 point-in-time 滚动回测框架，旨在避免 P22 静态快照回测中存在的前瞻偏差（lookahead bias）。

## 与 P22 的区别
- P22 是 static snapshot backtest，有 lookahead bias
- P23 目标是 point-in-time rolling backtest
- 每期必须保存 signal snapshot
- 每期只能用 data_cutoff_date 之前的数据
- 不能用当前 Watchlist 倒推历史
- 不下单、不调用交易接口

## 实施计划
- P23.1：滚动历史选股回测设计与 schema
- P23.2：生成历史 signal snapshots
- P23.3：执行 point-in-time rolling backtest
- P23.4：回测结果接入 dashboard
- P23.5：保存最近 N 次 rolling backtest 历史
- P23.6：一键运行 数据→历史信号→滚动回测→dashboard

## 安全边界
- 不下单
- 不调用交易接口
- 不发送 webhook
- 不输出 secrets

## 注意事项
- P23.1 只做设计，不跑回测
- P23.2 才实现历史 signal snapshot 生成
- P23.3 才实现滚动回测计算
- P23.4 才接入 dashboard

