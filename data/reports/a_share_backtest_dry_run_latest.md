# A股 Watchlist 单次历史回测 Dry-run

## 口径
- backtest_type: static_snapshot_backtest
- dry_run: true
- sent: false
- trading_called: false
- allow_real_trade: false
- allow_short: false
- lookahead_bias_warning: true

说明：这是当前 Watchlist 静态快照回测，不是 point-in-time 历史选股回测，存在 lookahead bias。

## 输入
- selected_count: 20
- top5: 600519.SH, 600036.SH, 000858.SZ, 000001.SZ, 601398.SH
- valid_price_series_count: 20
- period: 2026-03-12 to 2026-07-09

## 组合指标
- total_return: -0.132762
- annualized_return: -0.361538
- max_drawdown: -0.157806
- volatility: 0.139429
- sharpe: -2.59298
- win_rate: 0.4875
- n_days: 81
- first_date: 2026-03-12
- last_date: 2026-07-09

## Benchmark
- benchmark: 000300.SH
- benchmark_total_return: 0.040267
- excess_return: -0.173029

## Warnings
- None
