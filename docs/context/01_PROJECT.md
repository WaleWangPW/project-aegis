# Project

Project Aegis 是单用户 AI 波段决策支持系统，不是选股器、预测器或真实交易系统。

## 目标

- 提高单一用户的投资决策质量
- 保持证据驱动、可复盘、可追踪
- 用最少上下文恢复当前工作状态

## 架构与流向

`Data Source -> Market Regime -> Universe/Candidates -> Expert Committee -> Decision Engine -> RecommendationRecord -> Dashboard JSON -> Paper Trading -> Review -> Investment Memory -> Time Travel Backtest`

## 禁止事项

- 不做真实下单
- 不做预测模型
- 不做综合评分
- 不编造缺失数据
- 不改 `dashboard/index.html`
- 不改 Pipeline 既有逻辑

## 固定结论

- Dashboard 只是 View
- `RecommendationRecord` 是核心对象
- Risk veto 优先于其他意见
- 空推荐是允许的
