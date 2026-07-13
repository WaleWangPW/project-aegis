const reportBase = '../data/reports/';
const sources = {health:'aegis_health_status_latest.json',gate:'aegis_evidence_gate_latest.json',daily:'aegis_daily_dry_run_hardened_latest.json',history:'aegis_pipeline_history_latest.json',watchlist:'a_share_watchlist_latest.json',crcl:'crcl_risk_monitor_latest.json',vanke:'000002.sz_risk_monitor_latest.json',digest:'feishu_daily_digest_dry_run.json',rolling:'a_share_point_in_time_rolling_backtest_latest.json',rollingHistory:'a_share_rolling_backtest_history_latest.json',audit:'a_share_rolling_backtest_raw_price_audit_latest.json',simulationBrief:'v2_14_e_refreshed_candidate_simulation_brief_latest.json',stockSelection:'stock_selection_workbench_latest.json',strategySandbox:'aegis_strategy_sandbox_validation_latest.json',strategyCases:'aegis_strategy_specific_historical_cases_latest.json',strategyCaseEvaluation:'aegis_strategy_specific_case_evaluation_latest.json',strategySourceProbe:'a_share_tushare_strategy_source_probe_latest.json',sourceHypotheses:'a_share_tushare_source_hypothesis_queue_latest.json',sourceHypothesisEvaluation:'a_share_tushare_source_hypothesis_evaluation_latest.json',sourceFeatureCoverage:'a_share_tushare_source_feature_coverage_latest.json',sourceDeepSandbox:'a_share_tushare_source_deep_sandbox_latest.json',refinedSandbox:'a_share_tushare_refined_strategy_sandbox_latest.json',rankingGate:'a_share_refined_strategy_ranking_gate_latest.json',sampleExpansion:'a_share_strategy_sample_expansion_plan_latest.json',strategyDiagnostics:'a_share_tushare_strategy_diagnostics_latest.json',fullYearCoverage:'a_share_full_year_coverage_plan_latest.json',dragonTiger:'a_share_dragon_tiger_research_samples_latest.json',stockAgentCycle:'stock_agent_a_share_strategy_cycle_latest.json',dashboardIntent:'aegis_dashboard_local_intent_ingest_latest.json',feedback:'aegis_stock_feedback_latest.json',pilot:'aegis_daily_real_scene_pilot_latest.json'};
const byId = id => document.getElementById(id);
const esc = value => String(value ?? '数据未提供').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmtPct = value => typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '数据未提供';
const stateLabel = value => ({NORMAL:'正常',PASS:'正常',WARNING:'注意',FAIL:'失败',BLOCKED:'已阻止','Risk / Exit':'风险与退出',UNKNOWN:'数据不足',MISSING:'数据不足',Exit:'退出复核',Action:'可执行',Ready:'等待确认',Watch:'观察',Review:'观察'}[value] || '数据不足');
const tone = value => ['NORMAL','PASS','Action'].includes(value) ? 'good' : ['FAIL','BLOCKED','Exit'].includes(value) ? 'risk' : 'warn';
const tag = value => `<span class="tag ${tone(value)}">${esc(stateLabel(value))}</span>`;

function deriveDailyDecision(viewModel) {
  const reasons = [];
  const gate = viewModel.gate?.overall_verdict;
  const health = viewModel.health?.health_status;
  const latestRun = viewModel.daily?.overall_verdict;
  if (gate !== 'PASS') reasons.push('证据检查异常');
  if (health === 'FAIL' || health === 'BLOCKED') reasons.push('系统状态异常');
  if (latestRun === 'FAIL') reasons.push('最近自动检查失败');
  if (viewModel.invalidSources.length) reasons.push('关键数据不可读取');
  const risks = viewModel.positions.filter(p => p.riskVeto || p.status === 'Exit');
  if (risks.some(p => p.riskVeto)) reasons.push('风险否决生效');
  const actions = viewModel.watchlist.filter(x => x.status === 'Action');
  const ready = viewModel.watchlist.filter(x => x.status === 'Ready');
  const watch = viewModel.watchlist.filter(x => ['Watch','Review'].includes(x.status));
  const counts = {risk_count:risks.length,action_count:actions.length,ready_count:ready.length,watch_count:watch.length};
  if (reasons.length) return {state:'BLOCKED',title:'系统阻止行动',summary:'关键证据或自动检查异常。',allowed:'检查系统与数据',forbidden:'任何投资动作',next_check:'修复异常后重新检查',blocking_reasons:reasons,...counts};
  if (risks.length) return {state:'Risk / Exit',title:'今天优先处理风险',summary:`当前有 ${risks.length} 项持仓风险需要复核。`,allowed:'复核退出条件、核对持仓数据',forbidden:'新增仓位',next_check:'每日 08:00 自动检查',blocking_reasons:[],...counts};
  if (actions.length) return {state:'Action',title:'今天存在可执行候选',summary:`当前有 ${actions.length} 个候选满足条件。`,allowed:'查看证据和失效条件',forbidden:'系统自动下单',next_check:'下一次自动检查',blocking_reasons:[],...counts};
  if (ready.length) return {state:'Ready',title:'今天等待确认',summary:`当前有 ${ready.length} 个候选等待确认。`,allowed:'复核候选条件',forbidden:'未经复核新增仓位',next_check:'下一次自动检查',blocking_reasons:[],...counts};
  if (watch.length) return {state:'Watch / Review',title:'今天无需操作',summary:'当前没有可执行候选，继续观察，等待条件变化。',allowed:'复核风险和市场状态',forbidden:'因无新证据而强行交易',next_check:'下一次自动检查',blocking_reasons:[],...counts};
  return {state:'No Data',title:'数据不足',summary:'数据不足，禁止行动。',allowed:'等待数据生成',forbidden:'任何投资动作',next_check:'数据生成后重新检查',blocking_reasons:[],...counts};
}

async function read(name, invalid) { try { const response = await fetch(reportBase + name,{cache:'no-store'}); if (!response.ok) throw new Error(String(response.status)); return await response.json(); } catch { invalid.push(name); return null; } }
function humanRisk(value) { const text=String(value||''); if (/max_drawdown/.test(text)) return '最大回撤超过风险阈值'; if (/volatility/.test(text)) return '波动率超过风险阈值'; if (/liquidity_not_ok/.test(text)) return '流动性不足'; if (/high_volatility/.test(text)) return '高波动风险触发'; if (/severe_drawdown/.test(text)) return '严重回撤风险触发'; return '风险条件需要复核'; }
function positionFromRisk(report, fallback) { if (!report) return {...fallback,missing:true,status:'UNKNOWN',riskVeto:false,risks:[]}; const meta=report.report_metadata||{},current=report.current_status||{},exit=report.exit_watch_eligibility||{}; return {symbol:meta.symbol||fallback.symbol,name:meta.stock_name||fallback.name,market:meta.market||fallback.market,status:current.recommendation||'UNKNOWN',riskVeto:report.risk_veto===true,risks:exit.blocking_conditions||[],updated:meta.generated_at||current.last_updated,nextCheck:report.next_check,source:meta.report_type||fallback.source,missing:false}; }
function holdingCard(p) { const onlyMonitor=p.symbol==='00700.HK'; const risk=p.risks[0] ? humanRisk(p.risks[0]) : '当前风险数据未提供'; const action=p.status==='Exit' ? '复核退出条件' : p.missing ? '等待监控数据更新' : '继续观察'; const position=onlyMonitor?'仅有监控状态，未确认实际持仓':'持仓数量：持仓数据未提供；成本价：数据未提供'; return `<article class="card holding-card"><h3>${esc(p.symbol)} · ${esc(p.name)}</h3><p>${tag(p.status)} ${esc(p.market)}</p><p>${esc(position)}</p><p><b>当前价：</b>数据未提供　<b>浮动收益：</b>数据未提供</p><p><b>风险提示：</b>${esc(risk)}</p><p><b>失效条件：</b>${esc(risk)}</p><p><b>下一步动作：</b>${esc(action)}</p><p class="muted">下次检查：每日 08:00 或风险条件变化时</p></article>`; }
function riskCard(p) { const first=p.risks[0] ? humanRisk(p.risks[0]) : '风险原因数据未提供'; return `<article class="card"><h3>${esc(p.symbol)} · ${esc(p.name)}</h3><p>${tag(p.status)}</p><p class="risk-line">${esc(first)}</p><p><b>建议动作：</b>复核退出条件</p><p class="muted">最近更新：${esc(p.updated)}</p><details><summary>查看原因</summary><ul class="detail-list">${p.risks.length?p.risks.map(x=>`<li>${esc(humanRisk(x))}</li>`).join(''):'<li>数据未提供</li>'}</ul><p class="muted">数据来源：${esc(p.source)}<br>原始更新时间：${esc(p.updated)}</p></details></article>`; }
function candidateCard(stock) { const note=stock.status==='Action'?'满足可执行状态，仍须人工复核。':stock.status==='Ready'?'等待条件确认。':'继续观察，等待条件变化。'; return `<article class="card watch-card"><h3>${esc(stock.symbol)} · ${esc(stock.name)}</h3><p>${tag(stock.status)}</p><p><b>支持证据：</b>数据未提供</p><p><b>反对证据：</b>数据未提供</p><p><b>风险阻塞：</b>数据未提供</p><p><b>失效条件：</b>数据未提供</p><p class="muted">${note}　下次检查：每日自动检查</p></article>`; }
function simulationCandidateCard(item) { const metrics=item.sandbox_metrics||{}; return `<article class="card simulation-card"><div class="sim-label">模拟观察</div><h3>${esc(item.symbol)} · ${esc(item.market)}</h3><p>${tag('Watch')} <span class="sim-boundary">仅模拟，不下单</span></p><p><b>今天怎么用：</b>${esc(item.user_action)}</p><p><b>沙盘状态：</b>${esc(metrics.sandbox_status)}　<b>样本数：</b>${esc(metrics.sample_count)}</p><p><b>历史结果：</b>win_rate ${esc(metrics.win_rate)}，average_return ${esc(metrics.average_return)}，max_drawdown ${esc(metrics.max_drawdown)}</p><p><b>你需要回传：</b>截图、外部看到的价格、时间、watch/ignore/manual external 判断。</p><p class="muted">Aegis 不给实时价格、不算仓位、不接券商、不调用 webhook、不下单。</p></article>`; }
function blockedSimulationList(items) { const blocked=items.filter(x=>x.brief_status==='blocked'); if(!blocked.length) return ''; return `<details class="blocked-sim"><summary>查看 ${blocked.length} 个今日不可用标的</summary><div class="blocked-grid">${blocked.map(item=>`<article class="blocked-chip"><b>${esc(item.symbol)}</b><span>${esc((item.blocked_reason_labels||[]).join('、')||'证据不足')}</span></article>`).join('')}</div></details>`; }
function shortNum(value, prefix='') { return typeof value==='number' ? `${prefix}${value.toFixed(value>100?2:2)}` : 'N/A'; }
function statusIcon(status) { return status==='research_candidate'?'✅':status==='high_risk_watch'?'⚠️':'⬜'; }
function newsText(n) { const raw=String(n.display_summary||n.summary||n.title||'公司动态'); return raw.length>108?`${raw.slice(0,107)}…`:raw; }
function shortText(value, limit=64) { const raw=String(value||'').trim(); return raw.length>limit?`${raw.slice(0,limit-1)}…`:raw; }
function marketName(value) { return ({A:'A股',HK:'港股',US:'美股'}[value]||value||'市场'); }
function pendingIntent(symbol) { try { return JSON.parse(localStorage.getItem(`aegis_intent_${symbol}`) || 'null'); } catch { return null; } }
function actionLabel(action) { return ({aegis_watch:'加入模拟研究',aegis_more_news:'要更多资讯',aegis_ignore:'暂不关注'}[action] || action); }
function localIntentLog() { try { const rows=JSON.parse(localStorage.getItem('aegis_intent_log') || '[]'); return Array.isArray(rows) ? rows : []; } catch { return []; } }
function writeLocalIntent(payload) { const rows=[payload,...localIntentLog().filter(x=>`${x.symbol}:${x.action}:${x.time}`!==`${payload.symbol}:${payload.action}:${payload.time}`)].slice(0,20); localStorage.setItem('aegis_intent_log', JSON.stringify(rows)); }
function intentExportText(rows) { if(!rows.length) return 'Aegis 本机暂无待确认操作。'; return rows.slice(0,8).map((x,i)=>`${i+1}. ${x.symbol}｜${actionLabel(x.action)}｜${x.time}｜仅模拟研究，不下单`).join('\n'); }
function intentExportPayload(rows) { return JSON.stringify({type:'aegis_dashboard_local_intents', exported_at:new Date().toISOString(), source:'dashboard-local', intents:rows.slice(0,8)}, null, 2); }
function intentSubmitStatus(symbol) { try { return JSON.parse(localStorage.getItem(`aegis_intent_submit_${symbol}`) || 'null'); } catch { return null; } }
async function submitDashboardIntent(payload) { try { const response=await fetch('/api/dashboard-intents',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'aegis_dashboard_local_intents',source:'dashboard-local',intents:[payload]})}); if(!response.ok) throw new Error(String(response.status)); const result=await response.json(); localStorage.setItem(`aegis_intent_submit_${payload.symbol}`, JSON.stringify({status:'RECORDED',time:new Date().toLocaleString('zh-CN',{hour12:false}), event_count:result.event_count||0})); return result; } catch (error) { localStorage.setItem(`aegis_intent_submit_${payload.symbol}`, JSON.stringify({status:'LOCAL_ONLY',time:new Date().toLocaleString('zh-CN',{hour12:false}), reason:String(error?.message||error)})); return null; } }
function localIntentBoard(feedback, dashboardIntent, compact=false) { const rows=localIntentLog(); const ingest=dashboardIntent?.latest_event; const backend=ingest||feedback?.event; const effects=ingest?.effects||dashboardIntent?.safety||backend?.effects||{}; const safeEffects=['recommendation_mutated','paper_trade_created','holding_mutated','broker_called','order_placed','trading_webhook_called'].every(key=>effects[key]===false); const backendText=backend?`${backend.symbol} · ${actionLabel(backend.action)} · ${backend.received_at}`:'后台暂未收到回传'; const latest=rows[0]; const submitted=latest?intentSubmitStatus(latest.symbol):null; const submitText=submitted?.status==='RECORDED'?'本地桥已写入':submitted?.status==='LOCAL_ONLY'?'仅本机记录':'等待点击'; const ingestStatus=dashboardIntent?.status==='RECORDED'?'已入库':backend?'已收到':'未收到'; const safetyLine=`交易副作用 ${safeEffects?'0':'需复核'}：不改推荐 / 不建交易 / 不接券商 / 不下单 / 不调 webhook`; return `<section class="intent-board ${compact?'compact':''}" aria-label="本机操作记录"><div class="intent-board-head"><div><span>操作记录</span><h3>${backend?`${esc(backend.symbol)} · ${esc(actionLabel(backend.action))}`:latest?`${esc(latest.symbol)} · ${esc(actionLabel(latest.action))}`:'还没有本机点击记录'}</h3><p>${backend?`后台 evidence 已记录：${esc(backend.feedback_type||dashboardIntent?.latest_feedback_type||'feedback')}。` : latest?`本机已记录 ${esc(latest.time)}；${submitText==='本地桥已写入'?'后台 evidence 已自动写入。':'如果本地桥服务开启，会自动写入后台 evidence。'}`:'点击候选卡按钮后，这里会立刻显示本机记录。'}</p></div><div class="intent-buttons"><button class="copy-intents" type="button" data-copy-intents="${esc(intentExportText(rows))}">复制摘要</button><button class="copy-intents machine" type="button" data-copy-intents-json="${esc(intentExportPayload(rows))}">复制后台JSON</button></div></div><p class="intent-safe-line">${esc(safetyLine)}</p><div class="intent-board-grid"><article><span>本机待确认</span><b>${esc(rows.length)}</b><small>localStorage</small></article><article><span>本地桥</span><b>${esc(submitText)}</b><small>${esc(submitted?.time||'serve-dashboard-intent-bridge')}</small></article><article><span>后台最新</span><b>${esc(ingestStatus)}</b><small>${esc(backendText)}</small></article><article class="${safeEffects?'ok':'hold'}"><span>交易副作用</span><b>${safeEffects?'0':'复核'}</b><small>不改推荐/不建交易/不接券商/不下单/不调 webhook</small></article></div>${rows.length?`<ol class="intent-log">${rows.slice(0,5).map(x=>`<li><b>${esc(x.symbol)}</b><span>${esc(actionLabel(x.action))}</span><small>${esc(x.time)}</small></li>`).join('')}</ol>`:'<p class="empty intent-empty">暂无本机记录。你可以在选股页点“加入模拟研究 / 要更多资讯 / 暂不关注”。</p>'}</section>`; }
function localIntentNotice(item) { const intent=pendingIntent(item.symbol); const submitted=intentSubmitStatus(item.symbol); if(!intent) return `<div class="intent-status"><b>本页提示</b><span>这里先记本地选择；本地桥服务开启时会自动写入后台 evidence。</span></div>`; if(submitted?.status==='RECORDED') return `<div class="intent-status selected"><b>后台已记录</b><span>${esc(actionLabel(intent.action))} · ${esc(intent.time)}；已通过本地桥写入 feedback evidence。</span></div>`; if(submitted?.status==='LOCAL_ONLY') return `<div class="intent-status selected"><b>本机已选</b><span>${esc(actionLabel(intent.action))} · ${esc(intent.time)}；本地桥未开启，仍保留本机回执。</span></div>`; return `<div class="intent-status selected"><b>本页已选</b><span>${esc(actionLabel(intent.action))} · ${esc(intent.time)}；正在尝试写入后台 evidence。</span></div>`; }
function markSelectedActionButtons() {
  document.querySelectorAll('[data-card-action]').forEach(button => {
    const symbol = button.dataset.symbol || '';
    const intent = pendingIntent(symbol);
    button.classList.toggle('selected', intent?.action === button.dataset.cardAction);
    if (intent?.action === button.dataset.cardAction) {
      button.textContent = `已记录：${actionLabel(intent.action)}`;
      button.setAttribute('aria-pressed', 'true');
    } else {
      button.setAttribute('aria-pressed', 'false');
    }
  });
}
function selectionCard(item) { const hot=item.status==='research_candidate'; const flags=item.risk_flags||[]; const matches=item.strategy_matches||[]; const news=(item.news_items||[]).slice(0,1); const year=typeof item.price_1y_pct==='number'?`1年 ${(item.price_1y_pct*100).toFixed(0)}%`:'1年 N/A'; const change=typeof item.daily_change_pct==='number'?`${item.daily_change_pct>0?'+':''}${item.daily_change_pct.toFixed(1)}%`:'N/A'; const cur=item.market==='US'?'$':item.market==='HK'?'HK$':'¥'; const riskText=flags.slice(0,2).join(' | ')||'需人工核对'; const company=shortText(item.industry_or_description||'公司信息待补',86); const why=shortText(matches.slice(0,2).join(' | ')||'策略信号不足',74); const newsLine=news.length?`${news[0].date?`${String(news[0].date).slice(5,10)}｜`:''}${newsText(news[0])}`:(item.news_summary||'未找到近期公司动态'); const plainNext=hot?'先核对外部实时价格、公告、新闻；满意再点股票助手按钮记录模拟观察。':'暂时不要模拟，只观察风险是否改善。'; const dataAttrs=`data-symbol="${esc(item.symbol)}" data-name="${esc(item.name)}" data-market="${esc(item.market)}" data-status="${esc(item.status)}" data-score="${esc(item.score)}"`; return `<article class="selection-shell ${hot?'selection-hot':''} ${item.status==='blocked'?'selection-blocked':''}" data-symbol="${esc(item.symbol)}"><div class="selection-card"><div class="selection-main"><div><div class="selection-top"><span class="market-pill">${esc(marketName(item.market))}</span><span class="selection-status">${statusIcon(item.status)} ${esc(item.status_label)}</span></div><h3>${esc(item.symbol)} · ${esc(item.name)}</h3><div class="quote-line"><b>${shortNum(item.price,cur)}</b><span>${esc(change)}</span><span>${esc(year)}</span><span>分 ${esc(item.score)}</span></div></div><div class="plain-verdict"><b>${hot?'可以研究，不等于买入':'先观察，不要追'}</b><span>${esc(plainNext)}</span></div></div><div class="decision-brief"><p><b>这家公司</b>${esc(company)}</p><p><b>入选原因</b>${esc(why)}</p><p><b>最新资讯</b>${esc(shortText(newsLine,120))}</p><p class="risk-copy"><b>先看风险</b>${esc(shortText(riskText,84))}</p></div><div class="levels"><span>参考买点 ${esc(shortNum(item.buy_point,cur))}</span><span>失效/止损 ${esc(shortNum(item.stop_loss,cur))}</span><span>${item.trend_up?'趋势向上':'趋势待确认'}</span></div><div class="action-dock"><div class="action-dock-head"><b>你现在可以点</b><span>只记录研究意图，不创建交易</span></div><div class="card-actions" aria-label="${esc(item.symbol)} 操作"><button class="candidate-action primary" type="button" data-card-action="aegis_watch" ${dataAttrs}>加入模拟研究</button><button class="candidate-action" type="button" data-card-action="aegis_more_news" ${dataAttrs}>要更多资讯</button><button class="candidate-action quiet" type="button" data-card-action="aegis_ignore" ${dataAttrs}>暂不关注</button></div>${localIntentNotice(item)}</div><details class="card-more"><summary>为什么不是直接买？</summary><div class="reason-stack"><div><span>边界</span><p>这只是模拟研究候选。Aegis 不接券商、不下单，真实交易只能由你在外部软件手动决定。</p></div><div><span>完整风险</span><p class="risk-copy">${esc(flags.slice(0,3).join(' | ')||'核对实时行情、公告、新闻、持仓冲突')}</p></div><div><span>系统建议</span><p>${esc(item.user_action)}</p></div></div></details></div></article>`; }
function strategyCard(s) { return `<article><b>${esc(s.name)}</b><span>${esc(shortText(s.use_for,44))}</span><small>${esc((s.signals||[]).slice(0,3).join(' / '))}</small></article>`; }
function strategyPanel(report) { const list=(report?.strategy_blueprints||[]).slice(0,6); if(!list.length) return ''; const focus=list.slice(0,3); const more=list.slice(3); return `<div class="strategy-panel slim"><div><p class="eyebrow">策略雷达</p><h4>今日只展示核心策略，其余展开看。</h4></div><div class="strategy-strip">${focus.map(strategyCard).join('')}</div>${more.length?`<details class="strategy-more"><summary>查看全部 ${list.length} 个策略</summary><div class="strategy-strip more-strip">${more.map(strategyCard).join('')}</div></details>`:''}</div>`; }
function feedbackPanel(feedback) { const event=feedback?.event; if(!event) return `<div class="feedback-panel"><b>按钮回传状态</b><span>后台记录器已就绪。你在飞书点“加入模拟观察 / 暂不关注 / 要更多资讯”后，这里应该显示最新记录。</span><small>如果你点了但这里没变，说明飞书按钮尚未自动回传到 Aegis。</small></div>`; const actionLabel={aegis_watch:'加入模拟观察',aegis_ignore:'暂不关注',aegis_more_news:'要更多资讯',aegis_manual_external:'外部手动处理'}[event.action]||event.action; return `<div class="feedback-panel good-feedback"><b>后台目前只收到这一条反馈</b><span>${esc(event.symbol)} · ${esc(actionLabel)} · ${esc(event.received_at)}</span><small>如果你刚刚点的是别的股票或“加入模拟观察”，这里还没收到那次点击。后台确认：不创建纸面交易、不改持仓、不调用券商、不下单。</small></div>`; }
function dailyUsePanel(summary, feedback, pilot) { const event=feedback?.event; const send=pilot?.summary||{}; const last=event?`${event.symbol} · ${({aegis_watch:'加入模拟观察',aegis_ignore:'暂不关注',aegis_more_news:'要更多资讯',aegis_manual_external:'外部手动处理'}[event.action]||event.action)}`:'还没有读到最新反馈'; return `<div class="daily-use-panel"><div><span>1</span><b>先看风险</b><p>如果上方写“今天优先处理风险”，今天不要新增仓位。</p></div><div><span>2</span><b>只看 Top 3</b><p>${esc(summary.research_candidate_count)} 只可研究里，先只看下面 3 只，别被列表淹没。</p></div><div><span>3</span><b>点按钮回传</b><p>最近记录：${esc(last)}。发送状态：${esc(send.send_status||'未知')}。</p></div></div>`; }
function minuteBrief(decision) { const riskMode=decision?.state==='Risk / Exit'||decision?.state==='BLOCKED'; const answer=riskMode?'今天不新增仓位，先处理风险。':'今天可以看候选，但仍只做模拟研究。'; return `<section class="minute-brief"><div><span>一句话</span><b>${esc(answer)}</b><p>当前风险 ${esc(decision?.risk_count ?? 0)} 项，可执行候选 ${esc(decision?.action_count ?? 0)} 个；Aegis 只负责筛选、解释和记录。</p></div><div><span>如果只看 1 分钟</span><b>看下面 3 张卡</b><p>不要全读报表。先看公司、资讯、风险；感兴趣再去外部软件核对。</p></div><div><span>安全边界</span><b>模拟研究，不下单</b><p>不接券商、不调用交易 webhook、不自动生成真实交易动作。</p></div></section>`; }
function activateSelectionPane(tab) {
  document.querySelectorAll('[data-selection-tab]').forEach(button => button.classList.toggle('active', button.dataset.selectionTab === tab));
  document.querySelectorAll('[data-selection-pane]').forEach(pane => pane.classList.toggle('active', pane.dataset.selectionPane === tab));
}
function secondaryActionPanel(report, researchMore, watch, blocked, failed) {
  const summary = report?.summary || {};
  const tabs = [
    {id:'more', label:'更多候选', count:researchMore.length, hint:'Top 3 看完再打开'},
    {id:'risk', label:'高风险观察', count:watch.length, hint:'默认不碰'},
    {id:'blocked', label:'暂不碰', count:blocked.length, hint:'已被压下去'},
    {id:'evidence', label:'策略证据', count:summary.strategy_count ?? '看', hint:'不当买入理由'}
  ];
  if (failed.length) tabs.push({id:'data', label:'数据问题', count:failed.length, hint:'待补数据'});
  return `<section class="secondary-action-panel" aria-label="更多研究入口"><div class="secondary-panel-head"><div><p class="eyebrow">二级研究区</p><h4>Top 3 看完先停一下，再决定要不要展开。</h4><p>默认不继续铺卡片，避免你被列表淹没。只有点下面入口时，才打开更多候选、高风险、暂不碰或策略证据。</p></div><div class="secondary-panel-score"><span>扫描</span><b>${esc(summary.total_candidates ?? 'N/A')}</b><small>可研究 ${esc(summary.research_candidate_count ?? 0)} · 资讯 ${esc(summary.news_enriched_count ?? 0)}</small></div></div><div class="selection-subnav" role="tablist" aria-label="选股二级视图">${tabs.map(tab=>`<button type="button" role="tab" data-selection-tab="${esc(tab.id)}"><b>${esc(tab.label)}</b><span>${esc(tab.count)}</span><small>${esc(tab.hint)}</small></button>`).join('')}</div><div class="selection-pane-stack"><section class="selection-pane active focus-stop" data-selection-pane="focus"><div class="pane-head"><b>默认只到这里</b><span>Top 3 看完后，先去外部软件核对；不要自动继续翻更多股票。</span></div><div class="focus-stop-grid"><article><span>最推荐下一步</span><b>选 0-1 只点按钮回传</b><p>如果没有把握，就点“要更多资讯”或“暂不关注”。</p></article><article><span>还想继续看</span><b>再打开一个二级入口</b><p>一次只展开一个面板，避免把研究变成刷列表。</p></article><article><span>交易边界</span><b>只模拟，不下单</b><p>Aegis 不接券商、不调用交易 webhook。</p></article></div></section><section class="selection-pane" data-selection-pane="more"><div class="pane-head"><b>更多候选</b><span>还有 ${esc(researchMore.length)} 只可研究；只在 Top 3 看完后再看。</span></div>${researchMore.length?`<div class="selection-grid compact-grid">${researchMore.map(selectionCard).join('')}</div>`:'<p class="empty">暂无更多候选。</p>'}</section><section class="selection-pane" data-selection-pane="risk"><div class="pane-head"><b>高风险观察</b><span>${esc(watch.length)} 只默认不碰；只看为什么没放行。</span></div>${watch.length?`<div class="selection-grid compact-grid">${watch.map(selectionCard).join('')}</div>`:'<p class="empty">暂无高风险观察。</p>'}</section><section class="selection-pane" data-selection-pane="blocked"><div class="pane-head"><b>暂不碰标的</b><span>${esc(blocked.length)} 只已被系统压下去，避免误点。</span></div>${blocked.length?`<div class="blocked-grid">${blocked.map(x=>`<article class="blocked-chip"><b>${esc(x.symbol)} · ${esc(x.name)}</b><span>${esc((x.risk_flags||[]).slice(0,2).join('、')||'基础筛选未通过')}</span></article>`).join('')}</div>`:'<p class="empty">暂无暂不碰标的。</p>'}</section><section class="selection-pane" data-selection-pane="evidence"><div class="pane-head"><b>策略与证据</b><span>只解释研究排序，不代表可以买。</span></div>${strategyPanel(report)}<p class="muted evidence-explain">策略、历史 case 和胜率只用来排序研究优先级，不代表可以买。真实交易必须由你在外部软件手动判断。</p></section>${failed.length?`<section class="selection-pane" data-selection-pane="data"><div class="pane-head"><b>数据源问题</b><span>${failed.length} 项需要后台补数据。</span></div><ul class="detail-list">${failed.map(x=>`<li>${esc(x.market)}：${esc(x.raw_text_excerpt||x.error||x.status)}</li>`).join('')}</ul></section>`:''}</div><p class="secondary-boundary">所有入口都只进入模拟研究和证据记录；Aegis 不接券商、不下单、不调用交易 webhook。</p></section>`;
}
function selectionWorkbenchPanel(report, feedback, pilot, decision) { if(!report) return ''; const items=report.candidates||[]; const researchAll=items.filter(x=>x.status==='research_candidate'); const research=researchAll.slice(0,3); const researchMore=researchAll.slice(3,9); const watch=items.filter(x=>x.status==='high_risk_watch').slice(0,3); const blocked=items.filter(x=>x.status==='blocked').slice(0,5); const failed=(report.market_runs||[]).filter(x=>x.status!=='PASS'); const summary=report.summary||{}; return `<div class="selection-workbench"><div class="workbench-head"><div><p class="eyebrow">今日怎么用</p><h3>不用读完整报表：先看结论，再看 3 张卡</h3><p>系统扫了 ${esc(summary.total_candidates)} 只，留下 ${esc(summary.research_candidate_count)} 只可研究，资讯覆盖 ${esc(summary.news_enriched_count)} 只。这里不是买入清单，是今天的研究顺序。</p></div><div class="safe-stamp">模拟<br>研究</div></div>${selectionWayfinder(summary)}${minuteBrief(decision)}${dailyUsePanel(summary,feedback,pilot)}${feedbackPanel(feedback)}${research.length?`<section class="candidate-section primary-section"><div class="candidate-section-head"><div><span>第一屏</span><h4>今天优先研究：只看这 3 张</h4></div><p>看公司、资讯、风险，再决定是否加入模拟研究。</p></div><div class="selection-grid focus-grid">${research.map(selectionCard).join('')}</div></section>`:'<p class="empty">今天没有可研究候选。</p>'}${secondaryActionPanel(report,researchMore,watch,blocked,failed)}</div>`; }
function dispositionLabel(value) { return ({simulation_research_candidate:'继续模拟研究',watch_only:'只观察',downgraded:'降级'}[value]||value||'未评估'); }
function strategySandboxPanel(report, cases, evaluation) { if(!report) return ''; const s=report.summary||{}; const cs=cases?.summary||{}; const es=evaluation?.summary||{}; const proxy=(report.items||[]).filter(x=>x.coverage_tier==='point_in_time_proxy').slice(0,5); const pending=(report.items||[]).filter(x=>x.coverage_tier!=='point_in_time_proxy').slice(0,5); const evalItems=evaluation?.items||[]; const keep=evalItems.filter(x=>x.disposition==='simulation_research_candidate').slice(0,6); const watch=evalItems.filter(x=>x.disposition==='watch_only').slice(0,4); const down=evalItems.filter(x=>x.disposition==='downgraded').slice(0,4); const caseResults=(cases?.candidate_results||[]).filter(x=>x.case_count>0).slice(0,5); const gaps=(cases?.data_gaps||[]).slice(0,5); const evalLine=x=>`<li><b>${esc(x.symbol)}</b> ${esc(x.name)}：${esc(dispositionLabel(x.disposition))}，胜率 ${fmtPct(x.summary?.win_rate)}，均值 ${fmtPct(x.summary?.average_return)}，原因 ${esc((x.reasons||[]).join(' / '))}</li>`; return `<div class="strategy-coverage"><p class="eyebrow">策略沙盘验证</p><h3>当前候选先看历史证据，不把入选当成买入结论。</h3><div class="coverage-grid"><div><span>候选</span><b>${esc(s.candidate_count)}</b></div><div><span>逐标的 case</span><b>${esc(cs.historical_case_count ?? s.direct_candidate_backtest_count)}</b></div><div><span>数据缺口</span><b>${esc(cs.data_gap_count ?? s.pending_case_count)}</b></div><div><span>降级</span><b>${esc(es.downgraded_count ?? 'N/A')}</b></div></div><div class="coverage-grid eval-grid"><div><span>继续模拟研究</span><b>${esc(es.simulation_research_candidate_count ?? 'N/A')}</b></div><div><span>只观察</span><b>${esc(es.watch_only_count ?? 'N/A')}</b></div><div><span>已评估</span><b>${esc(es.candidate_count ?? 'N/A')}</b></div><div><span>真实交易</span><b>禁止</b></div></div><p class="muted">历史时点回测：${s.point_in_time_backtest_available?'已接入':'未接入'}；前视偏差控制：${s.lookahead_bias_control_passed?'通过':'未确认'}；真实交易信号：禁止。</p><details open><summary>查看 case 评估结论</summary><div class="coverage-lists"><div><b>继续模拟研究</b><ul>${keep.length?keep.map(evalLine).join(''):'<li>暂无</li>'}</ul></div><div><b>只观察 / 降级</b><ul>${watch.concat(down).length?watch.concat(down).map(evalLine).join(''):'<li>暂无</li>'}</ul></div></div></details><details><summary>查看策略覆盖明细</summary><div class="coverage-lists"><div><b>已有逐标的 case</b><ul>${caseResults.length?caseResults.map(x=>`<li>${esc(x.symbol)} ${esc(x.name)}：${esc(x.case_count)} 例，胜率 ${fmtPct(x.summary?.win_rate)}，均值 ${fmtPct(x.summary?.average_return)}</li>`).join(''):'<li>暂无</li>'}</ul></div><div><b>待补数据</b><ul>${gaps.length?gaps.map(x=>`<li>${esc(x.symbol)} ${esc(x.name)}：${esc(x.gap_reason||x.status)}</li>`).join(''):'<li>暂无</li>'}</ul></div></div><div class="coverage-lists"><div><b>策略族代理证据</b><ul>${proxy.length?proxy.map(x=>`<li>${esc(x.symbol)} ${esc(x.name)}：${esc(x.coverage_tier)}</li>`).join(''):'<li>暂无</li>'}</ul></div><div><b>仍待验证</b><ul>${pending.length?pending.map(x=>`<li>${esc(x.symbol)} ${esc(x.name)}：${esc(x.strategy_validation_status)}</li>`).join(''):'<li>暂无</li>'}</ul></div></div></details></div>`; }
function stage(daily,name,label) { const row=(daily?.stages||[]).find(x=>x.name===name); return `<li>${label}：${esc(stateLabel(row?.result))}</li>`; }
function reportLink(label,name) { return `<li><a href="${reportBase}${esc(name)}" target="_blank" rel="noopener">${esc(label)}</a></li>`; }
function activatePage(page) {
  document.querySelectorAll('[data-page-view]').forEach(view => view.classList.toggle('active', view.dataset.pageView === page));
  document.querySelectorAll('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.page === page));
  document.body.dataset.activePage = page;
  history.replaceState(null, '', `#${page}`);
  window.scrollTo({top: 0, behavior: 'smooth'});
}
function setupNavigation() {
  document.addEventListener('click', event => {
    const actionButton = event.target.closest('[data-card-action]');
    if (actionButton) {
      const symbol = actionButton.dataset.symbol || '';
      const action = actionButton.dataset.cardAction || '';
      const payload = {symbol, action, time: new Date().toLocaleString('zh-CN', {hour12:false}), source:'dashboard-local', name:actionButton.dataset.name||'', market:actionButton.dataset.market||'', status:actionButton.dataset.status||'', score:actionButton.dataset.score||''};
      localStorage.setItem(`aegis_intent_${symbol}`, JSON.stringify(payload));
      writeLocalIntent(payload);
      localStorage.removeItem(`aegis_intent_submit_${symbol}`);
      const card = actionButton.closest('.selection-shell');
      const status = card?.querySelector('.intent-status');
      if (status) {
        status.className = 'intent-status selected';
        status.textContent = `本页已选择：${actionLabel(action)} · ${payload.time}。正在尝试写入本地后台 evidence。`;
      }
      submitDashboardIntent(payload).then(()=>render());
      render();
      return;
    }
    const jsonButton = event.target.closest('[data-copy-intents-json]');
    if (jsonButton) {
      const text = jsonButton.dataset.copyIntentsJson || '';
      navigator.clipboard?.writeText(text).then(()=>{ jsonButton.textContent='JSON已复制'; setTimeout(()=>{ jsonButton.textContent='复制后台JSON'; },1400); }).catch(()=>{ jsonButton.textContent='复制失败'; setTimeout(()=>{ jsonButton.textContent='复制后台JSON'; },1400); });
      return;
    }
    const copyButton = event.target.closest('[data-copy-intents]');
    if (copyButton) {
      const text = copyButton.dataset.copyIntents || '';
      navigator.clipboard?.writeText(text).then(()=>{ copyButton.textContent='已复制'; setTimeout(()=>{ copyButton.textContent='复制回传摘要'; },1400); }).catch(()=>{ copyButton.textContent='复制失败'; setTimeout(()=>{ copyButton.textContent='复制回传摘要'; },1400); });
      return;
    }
    const stockAgentButton = event.target.closest('[data-copy-stock-agent-task]');
    if (stockAgentButton) {
      const text = stockAgentButton.dataset.copyStockAgentTask || '';
      navigator.clipboard?.writeText(text).then(()=>{ stockAgentButton.textContent='任务已复制'; setTimeout(()=>{ stockAgentButton.textContent='复制 stock-agent 任务'; },1800); }).catch(()=>{ stockAgentButton.textContent='复制失败'; setTimeout(()=>{ stockAgentButton.textContent='复制 stock-agent 任务'; },1800); });
      return;
    }
    const copyTextButton = event.target.closest('[data-copy-text]');
    if (copyTextButton) {
      const text = copyTextButton.dataset.copyText || '';
      const label = copyTextButton.dataset.copyLabel || copyTextButton.textContent || '复制';
      navigator.clipboard?.writeText(text).then(()=>{ copyTextButton.textContent='已复制'; setTimeout(()=>{ copyTextButton.textContent=label; },1400); }).catch(()=>{ copyTextButton.textContent='复制失败'; setTimeout(()=>{ copyTextButton.textContent=label; },1400); });
      return;
    }
    const selectionTab = event.target.closest('[data-selection-tab]');
    if (selectionTab) {
      activateSelectionPane(selectionTab.dataset.selectionTab);
      return;
    }
    const target = event.target.closest('[data-page],[data-page-jump]');
    if (!target) return;
    activatePage(target.dataset.page || target.dataset.pageJump);
  });
  window.addEventListener('hashchange', () => {
    const page = (location.hash || '#today').replace('#','');
    if (document.querySelector(`[data-page-view="${page}"]`)) activatePage(page);
  });
}
function actionHub(decision, feedback, dashboardIntent) {
  const latestEvent = dashboardIntent?.latest_event || feedback?.event;
  const latest = latestEvent ? `${latestEvent.symbol} · ${actionLabel(latestEvent.action)}` : '暂无新反馈';
  const riskFirst = decision.risk_count > 0;
  const primary = riskFirst ? {page:'risk',title:'先处理风险',body:`有 ${decision.risk_count} 项风险/退出复核，今天不要新增仓位。`,tone:'danger',cta:'处理风险'} : {page:'selection',title:'看 Top 3 候选',body:'没有紧急风险时，只看 3 张候选卡，点按钮记录你的研究意图。',tone:'primary',cta:'开始选股'};
  const steps = [
    primary,
    {page:'strategy',title:'确认策略 Gate',body:`A股 ranking gate 仍需放行；Gate=0 时不进入用户推荐。`,tone:'secondary',cta:'看策略'},
    {page:'evidence',title:'确认回传记录',body:`最近记录：${latest}。点击候选卡后会进入本机记录和后台 evidence。`,tone:'secondary',cta:'看回执'}
  ];
  const manualSteps = [
    {title:'外部核对',body:'在券商/行情软件核对实时价格、公告、新闻和持仓冲突。'},
    {title:'点按钮回传',body:'回到选股页点“加入模拟研究 / 要更多资讯 / 暂不关注”。'},
    {title:'看证据回执',body:'证据页确认后台已记录；交易副作用必须是 0。'}
  ];
  return `${localIntentBoard(feedback,dashboardIntent,true)}<section class="daily-command-panel" aria-label="今日操作面板"><div class="daily-command-head"><span>今日操作面板</span><b>${riskFirst?'先止血，再研究':'先研究，不交易'}</b><p>${riskFirst?'风险页是今天的第一入口；选股只作为研究参考。':'选股页只负责模拟研究记录，真实下单只能在外部软件手动完成。'}</p></div><div class="manual-loop" aria-label="手动使用闭环"><b>今天真实怎么用</b>${manualSteps.map((item,index)=>`<p><span>${index+1}</span><strong>${esc(item.title)}</strong>${esc(item.body)}</p>`).join('')}</div><div class="daily-command-steps">${steps.map((item,index)=>`<article class="hub-card ${item.tone}"><div><em>${index+1}</em><b>${esc(item.title)}</b><p>${esc(item.body)}</p></div><button type="button" data-page-jump="${esc(item.page)}"><span>${esc(item.cta)}</span><i>↗</i></button></article>`).join('')}</div></section>${accessPanel()}`;
}
function commandStrip(decision, stockSelection, fullYearCoverage, rankingGate, feedback) {
  const researchCount = stockSelection?.summary?.research_candidate_count ?? 0;
  const newsCount = stockSelection?.summary?.news_enriched_count ?? 0;
  const gateApproved = rankingGate?.summary?.ranking_gate_approved_count ?? 0;
  const coverage = coverageShortLabel(fullYearCoverage);
  const latest = feedback?.event ? `${feedback.event.symbol} · ${actionLabel(feedback.event.action)}` : '暂无回传';
  const firstPage = decision.risk_count > 0 ? 'risk' : 'selection';
  const firstLabel = decision.risk_count > 0 ? '先处理风险' : '看 Top 候选';
  return `<div class="command-copy"><span>今日路径</span><b>${esc(firstLabel)}</b><small>${decision.risk_count > 0 ? `风险 ${decision.risk_count} 项，今天不要新增仓位` : `可研究 ${researchCount} 只，资讯 ${newsCount} 只`}</small></div><div class="command-pills"><button class="command-pill primary" type="button" data-page-jump="${esc(firstPage)}"><span>1</span>${esc(firstLabel)}</button><button class="command-pill" type="button" data-page-jump="strategy"><span>2</span>策略状态：Gate ${esc(gateApproved)}</button><button class="command-pill" type="button" data-page-jump="evidence"><span>3</span>回传：${esc(latest)}</button><button class="command-pill ghost" type="button" data-page-jump="evidence"><span>安全</span>一年覆盖 ${esc(coverage)} · 只模拟</button></div>`;
}
function accessPanel() {
  const localUrl = 'http://127.0.0.1:8080/dashboard/index.html';
  const lanCommand = 'make dashboard-start-lan && make dashboard-status-lan';
  return `<section class="access-panel" aria-label="访问方式"><div><span>访问方式</span><b>电脑本机稳定，手机需显式开启</b><p>默认只监听 127.0.0.1，所以外面的手机打不开是安全设计，不是数据坏了。</p></div><div class="access-grid"><article class="ok"><strong>电脑本机</strong><code>${esc(localUrl)}</code><button type="button" data-copy-text="${esc(localUrl)}" data-copy-label="复制本机链接">复制本机链接</button></article><article class="warn"><strong>同 Wi-Fi 手机</strong><code>${esc(lanCommand)}</code><button type="button" data-copy-text="${esc(lanCommand)}" data-copy-label="复制 LAN 命令">复制 LAN 命令</button></article><article><strong>人在外面</strong><p>用 Tailscale/私有隧道；不要直接把 8080 暴露公网。</p></article></div><small>LAN 模式仍只记录模拟研究按钮回传；不接券商、不下单、不调用交易 webhook。</small></section>`;
}
function isWaitingCurrentDayDaily(report) {
  return report?.coverage_status === 'WAITING_CURRENT_TRADING_DAY_DAILY'
    || (report?.blockers || []).includes('current_trading_day_daily_not_yet_available');
}
function coverageShortLabel(report) {
  if (isWaitingCurrentDayDaily(report)) return '等今日日线';
  return report?.answer_label || 'NO';
}
function coverageHeadline(report) {
  if (report?.answer_label === 'YES') return 'YES';
  if (isWaitingCurrentDayDaily(report)) return '等待收盘';
  return 'NO';
}
function coverageHint(report) {
  if (!report) return '等待报告';
  if (isWaitingCurrentDayDaily(report)) return `缓存已到前一交易日，${report.current_day_retry?.retry_not_before_local_time || '收盘后'} 后重试`;
  return report.coverage_status || '等待报告';
}
function parseIsoDate(value) {
  if (!value) return null;
  const normalized = String(value).replace(/(\.\d{3})\d+/, '$1');
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}
function localDayKey(date) {
  return date ? new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Shanghai'}).format(date) : null;
}
function candidateFreshness(report) {
  const generated = parseIsoDate(report?.generated_at);
  if (!generated) return {label:'未知', detail:'候选更新时间缺失'};
  const nowKey = localDayKey(new Date());
  const generatedKey = localDayKey(generated);
  const ageMs = Date.now() - generated.getTime();
  const hours = Math.max(0, Math.round(ageMs / 36e5));
  if (generatedKey === nowKey) return {label:'今日刷新', detail:`${generatedKey} · 约 ${hours} 小时前`};
  if (hours <= 36) return {label:'昨日缓存', detail:`${generatedKey} · 可研究，需核对实时行情`};
  return {label:'需刷新', detail:`${generatedKey} · 已超过 36 小时`};
}
function retryWindowStatus(report) {
  if (!isWaitingCurrentDayDaily(report)) return {label:'无需重试', detail:'等待覆盖报告状态变化'};
  const raw = report?.current_day_retry?.retry_not_before_local_time || '';
  const match = raw.match(/(\d{1,2}):(\d{2})/);
  if (!match) return {label:'等收盘后', detail:raw || '收盘后再重试'};
  const now = new Date();
  const target = new Date(now);
  target.setHours(Number(match[1]), Number(match[2]), 0, 0);
  if (now >= target) return {label:'可以重试', detail:'让 stock-agent 执行今日日线缓存补全'};
  const mins = Math.max(0, Math.ceil((target - now) / 60000));
  return {label:'未到窗口', detail:`约 ${mins} 分钟后到 ${raw}`};
}
function selectionWayfinder(summary) {
  return `<section class="selection-wayfinder" aria-label="选股页阅读顺序"><div><span>01</span><b>只看 Top 3</b><p>先不展开更多候选，避免被列表淹没。</p></div><div><span>02</span><b>点一个明确按钮</b><p>加入模拟研究、要资讯、暂不关注，都会记录意图。</p></div><div><span>03</span><b>再看策略证据</b><p>扫描 ${esc(summary.total_candidates ?? 'N/A')} 只；可研究 ${esc(summary.research_candidate_count ?? 0)} 只。</p></div><button type="button" data-page-jump="strategy">打开策略页</button></section>`;
}
function morningReadinessPanel(decision, stockSelection, fullYearCoverage, stockAgentCycle, rankingGate) {
  const coverageOk = fullYearCoverage?.answer_label === 'YES';
  const coverageWaiting = isWaitingCurrentDayDaily(fullYearCoverage);
  const rankingApproved = Number(rankingGate?.summary?.ranking_gate_approved_count || 0);
  const researchCount = Number(stockSelection?.summary?.research_candidate_count || 0);
  const newsCount = Number(stockSelection?.summary?.news_enriched_count || 0);
  const commandCount = stockAgentCycle?.summary?.command_count ?? 'N/A';
  const failedCount = stockAgentCycle?.summary?.failed_command_count ?? 'N/A';
  const freshness = candidateFreshness(stockSelection);
  const retryStatus = retryWindowStatus(fullYearCoverage);
  const status = decision.risk_count > 0 ? '先处理风险' : researchCount > 0 ? '可以开始研究' : '等待数据';
  const statusTone = decision.risk_count > 0 ? 'risk' : researchCount > 0 ? 'good' : 'warn';
  return `<section class="morning-readiness ${statusTone}" aria-label="明早可用状态">
    <div class="morning-topline">
      <span>明早打开先看这里</span>
      <b>${esc(status)}</b>
      <p>${decision.risk_count > 0 ? '今天第一动作不是选股，是复核风险；选股页仍可作为研究参考。' : '今天可以看 Top 3 候选，但只能加入模拟研究，不能自动交易。'}</p>
    </div>
    <div class="morning-grid">
      <article><span>Top 候选</span><b>${esc(researchCount)}</b><small>已补资讯 ${esc(newsCount)}</small></article>
      <article class="${freshness.label==='需刷新'?'hold':'ok'}"><span>候选数据</span><b>${esc(freshness.label)}</b><small>${esc(freshness.detail)}</small></article>
      <article class="${coverageOk ? 'ok' : 'hold'}"><span>全A股一年</span><b>${esc(coverageHeadline(fullYearCoverage))}</b><small>${esc(coverageHint(fullYearCoverage))}</small></article>
      <article class="${rankingApproved > 0 ? 'ok' : 'hold'}"><span>策略放行</span><b>${esc(rankingApproved)}</b><small>ranking gate</small></article>
      <article><span>stock-agent</span><b>${esc(commandCount)}</b><small>失败 ${esc(failedCount)}</small></article>
      <article class="${retryStatus.label==='可以重试'?'ok':'hold'}"><span>重试窗口</span><b>${esc(retryStatus.label)}</b><small>${esc(retryStatus.detail)}</small></article>
    </div>
    <div class="morning-next">
      <b>${coverageOk ? '下一步：继续验证策略稳定性' : coverageWaiting ? `下一步：${esc(fullYearCoverage?.current_day_retry?.retry_not_before_local_time || '收盘后')} 后重试今日日线` : '醒来后可批准：补当前过去一年全A股缓存'}</b>
      <span>${coverageOk ? '仍需 ranking gate 放行后才允许影响排序。' : coverageWaiting ? `${retryStatus.detail}；这不是历史缺口，不会因此放松 Gate。` : '未批准前不会消耗大量 Tushare API，也不会写入大缓存。'}</span>
    </div>
  </section>`;
}
function compactCandidate(item) {
  const news=(item.news_items||[])[0];
  const newsLine=news ? `${news.date ? `${String(news.date).slice(5,10)}｜` : ''}${newsText(news)}` : '暂无近期资讯摘要';
  const cur=item.market==='US'?'$':item.market==='HK'?'HK$':'¥';
  return `<article class="mini-candidate"><div><span>${esc(marketName(item.market))}</span><b>${esc(item.symbol)} · ${esc(item.name)}</b></div><p>${esc(shortText(item.industry_or_description||'公司信息待补',72))}</p><p><strong>资讯</strong>${esc(shortText(newsLine,86))}</p><footer><span>${esc(shortNum(item.price,cur))}</span><span>${item.trend_up?'趋势向上':'趋势待确认'}</span><button type="button" data-page-jump="selection">看详情</button></footer></article>`;
}
function overviewCandidates(report) {
  const items=(report?.candidates||[]).filter(x=>x.status==='research_candidate').slice(0,3);
  if (!items.length) return '<p class="empty">今天没有可研究候选。</p>';
  return `<div class="mini-candidate-grid">${items.map(compactCandidate).join('')}</div><button class="wide-action" type="button" data-page-jump="selection"><span>进入选股页，看完整 Top 候选</span><i>→</i></button>`;
}
function probeByModule(probe) {
  const grouped = {};
  for (const item of probe?.modules || []) {
    const key = item.module_id || item.module_name;
    grouped[key] = grouped[key] || [];
    grouped[key].push(item);
  }
  return grouped;
}
function enrichModule(item, grouped) {
  const endpoints = grouped[item.moduleId] || [];
  if (!endpoints.length) return item;
  const pass = endpoints.filter(x=>x.status==='PASS');
  const blocked = endpoints.filter(x=>x.status==='ERROR'||x.status==='PERMISSION_BLOCKED');
  const rows = endpoints.reduce((sum,x)=>sum + (Number(x.row_count)||0),0);
  return {...item,status:pass.length?`PASS · ${pass.length}/${endpoints.length} 接口`:blocked.length?`阻塞 · ${blocked.length}/${endpoints.length}`:`空数据 · 0/${endpoints.length}`,rows,endpoints:endpoints.map(x=>`${x.endpoint}:${x.status}(${x.row_count})`)};
}
function tushareStrategyModules(probe) {
  const grouped = probeByModule(probe);
  return [
    {moduleId:'capital_flow',name:'主力资金流向',kind:'资金',source:'Tushare moneyflow',status:'待探测',use:'识别大单/中单/小单资金结构，避免只看价格追涨。',signals:['大单净流入连续性','中单/游资参与强度','小单追高风险','资金流与价格背离']},
    {moduleId:'dragon_tiger_hot_money',name:'龙虎榜 / 游资席位',kind:'席位',source:'Tushare top_list / top_inst',status:'待探测',use:'识别短线异动、游资接力和机构席位参与，不把涨停当成买点。',signals:['上榜原因','买卖席位结构','机构净买入','游资高换手风险']},
    {moduleId:'institutional_ownership',name:'机构持仓与股东变化',kind:'筹码',source:'Tushare top10_holders / top10_floatholders',status:'待探测',use:'观察长期资金是否稳定进入，过滤筹码过度分散或异常拥挤。',signals:['十大股东变化','流通股东集中度','披露日护栏','机构持仓稳定性']},
    {moduleId:'holder_concentration',name:'股东人数 / 筹码集中',kind:'筹码',source:'Tushare stk_holdernumber',status:'待探测',use:'用股东人数变化观察筹码集中或扩散，必须按披露日做防前视。',signals:['股东人数变化','集中度改善','拥挤风险','披露日期']},
    {moduleId:'factor_base',name:'因子与日线基础池',kind:'基础',source:'Tushare stk_factor / daily_basic',status:'待探测',use:'作为 A 股基础筛选、价格动量、估值和流动性输入。',signals:['成交额','换手率','估值热度','短中期动量']},
    {moduleId:'institutional_research',name:'机构调研热度',kind:'调研',source:'Tushare stk_survey 或等价数据',status:'待权限确认',use:'把调研热度当线索，不当买入理由，必须叠加基本面和价格验证。',signals:['调研频次','参与机构质量','问题主题','调研后业绩兑现']}
  ].map(item=>enrichModule(item, grouped));
}
function strategyRoadmapCard(item, index) {
  const level = item.level || '待验证';
  const endpointLine = (item.endpoints || []).join(' / ');
  const sample = item.sample || '先补历史样本，再进沙盘';
  return `<article class="roadmap-card ${item.tone||''}"><div class="roadmap-index">${String(index + 1).padStart(2,'0')}</div><div><span>${esc(item.theme)}</span><h3>${esc(item.title)}</h3><p>${esc(item.why)}</p><small>${esc(endpointLine)}</small></div><footer><b>${esc(level)}</b><em>${esc(sample)}</em></footer></article>`;
}
function strategyRoadmapPanel() {
  const items = [
    {theme:'资金',title:'主力资金流向',why:'看大单/中单资金是否连续进入，但必须叠加趋势和风险否决，避免追涨。',endpoints:['moneyflow'],level:'已深测：未通过',sample:'扩大命中样本 + 加风险否决',tone:'caution'},
    {theme:'游资',title:'龙虎榜 / 游资席位',why:'识别短线异动、机构席位和游资接力，不把上榜本身当买点。',endpoints:['top_list','top_inst'],level:'数据缺口',sample:'先补 top_list/top_inst 历史 case',tone:'gap'},
    {theme:'筹码',title:'机构持仓与股东变化',why:'看长期资金是否稳定进入，过滤筹码过度分散或异常拥挤。',endpoints:['top10_holders','top10_floatholders'],level:'已深测：未通过',sample:'收紧信号定义后重测'},
    {theme:'筹码',title:'股东人数 / 集中度',why:'股东人数下降可能代表筹码集中，但必须防前视并验证后验收益。',endpoints:['stk_holdernumber'],level:'已深测：未通过',sample:'只作辅助，不进排序'},
    {theme:'基础',title:'因子 + 流动性质量',why:'用成交额、换手率、估值热度和动量做基础护栏，避免只凭题材入选。',endpoints:['stk_factor','daily_basic'],level:'已深测：未通过',sample:'重写阈值后再测'},
    {theme:'调研',title:'机构调研热度',why:'调研只能当线索，要和业绩兑现、价格趋势、估值风险一起看。',endpoints:['stk_survey'],level:'权限待确认',sample:'先确认接口权限'}
  ];
  return `<section class="strategy-roadmap"><div class="roadmap-head"><div><p class="eyebrow">A股策略路线图</p><h3>先把 Tushare 的主力、游资、筹码数据变成可验证策略。</h3><p>每条线都必须走：数据覆盖 → historical case → deep sandbox → ranking gate。没有通过前，只能研究，不能推荐。</p></div><button class="page-jump" type="button" data-page-jump="evidence">看证据</button></div><div class="roadmap-grid">${items.map(strategyRoadmapCard).join('')}</div></section>`;
}
function strategyModuleCard(item, index) { const rows=Number.isFinite(item.rows)?` · ${item.rows} 行`:''; const signals=item.endpoints?.length?item.endpoints:item.signals; return `<article class="strategy-module-card ${String(item.status).startsWith('PASS')?'module-pass':String(item.status).startsWith('阻塞')?'module-blocked':''}"><div class="strategy-module-top"><span>${String(index + 1).padStart(2,'0')} · ${esc(item.kind)}</span><small>${esc(item.status)}${esc(rows)}</small></div><h3>${esc(item.name)}</h3><p>${esc(item.use)}</p><div class="strategy-source">${esc(item.source)}</div><ul>${(signals||[]).slice(0,4).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></article>`; }
function currentStrategyCard(item, index) { return `<article class="strategy-current-card"><span>当前 ${String(index + 1).padStart(2,'0')}</span><h3>${esc(item.name)}</h3><p>${esc(item.use_for)}</p><div>${(item.signals||[]).slice(0,4).map(x=>`<small>${esc(x)}</small>`).join('')}</div></article>`; }
function sourceHypothesisEvaluationMap(evaluation) { const map={}; for (const item of evaluation?.items || []) map[item.hypothesis_id]=item; return map; }
function sourceDeepSandboxMap(report) { const map={}; for (const item of report?.items || []) map[item.hypothesis_id]=item; return map; }
function tushareStrategyMatrix(sourceProbe, sourceDeepSandbox, rankingGate, sampleExpansion, strategyCases, dragonTiger) {
  const probe = sourceProbe?.summary || {};
  const deep = sourceDeepSandbox?.summary || {};
  const gate = rankingGate?.summary || {};
  const expansion = sampleExpansion?.summary || {};
  const cases = strategyCases?.summary || {};
  const tiger = dragonTiger?.summary || {};
  const rows = [
    {name:'主力资金流向',source:'moneyflow',stage:'已深测，未放行',now:`源特征 case ${esc(deep.case_feature_count ?? 0)}；ranking gate 放行 ${esc(gate.ranking_gate_approved_count ?? 0)}`,next:'与筹码集中组合后继续扩样本，先看是否降低单股集中度。',tone:'warn'},
    {name:'龙虎榜 / 游资席位',source:'top_list / top_inst',stage:'研究样本扩展中',now:`样本 ${esc(tiger.sample_count ?? 0)}；事件对齐 case ${esc(cases.a_share_dragon_tiger_research_sample_case_count ?? 0)}`,next:`stock-agent 下一轮 lookback ${esc(expansion.next_lookback_dates ?? 'N/A')}、股票上限 ${esc(expansion.next_max_symbols ?? 'N/A')}。`,tone:'active'},
    {name:'机构持仓 / 前十大流通股东',source:'top10_holders / top10_floatholders',stage:'已纳入假设队列',now:'用于判断长期资金和筹码稳定性，但当前不能单独提升推荐。',next:'收紧信号定义：连续变化、拥挤度、价格位置一起验证。',tone:'neutral'},
    {name:'股东人数 / 筹码集中',source:'stk_holdernumber',stage:'辅助信号',now:'可辅助解释筹码集中，但必须防止前视和过拟合。',next:'只与主力资金、趋势、风险否决组合后进入 ranking gate。',tone:'neutral'},
    {name:'调研 / 治理 / 高管激励',source:'stk_survey / management compensation',stage:'权限与覆盖待确认',now:`Tushare 探测 endpoint ${esc(probe.endpoint_count ?? 0)} 个，部分源仍需补覆盖。`,next:'先补数据覆盖，再做后验 case，不直接影响今日候选。',tone:'gap'}
  ];
  return `<section class="strategy-matrix"><div class="matrix-head"><div><p class="eyebrow">你要看的主力 / 游资策略</p><h3>Tushare 增强策略现在处在“验证中”，不是推荐中。</h3><p>这张表专门回答：哪些数据源会用于选股、现在能不能用、下一步由 stock-agent 做什么。</p></div><div class="matrix-policy"><b>放行条件</b><span>historical case → deep sandbox → ranking gate → 风险否决，全部通过后才影响排序。</span></div></div><div class="matrix-grid">${rows.map(row=>`<article class="matrix-card matrix-${esc(row.tone)}"><span>${esc(row.source)}</span><h4>${esc(row.name)}</h4><strong>${esc(row.stage)}</strong><p>${esc(row.now)}</p><small>${esc(row.next)}</small></article>`).join('')}</div></section>`;
}
function sourceDispositionText(value) { return ({proxy_pass:'代理通过',needs_more_a_share_cases:'样本不足',proxy_fail:'代理失败'}[value]||'待评估'); }
function sourceDeepText(value) { return ({DEEP_SANDBOX_PASS_CANDIDATE:'深测候选',DEEP_SANDBOX_FAIL:'深测失败'}[value]||'待深测'); }
function sourceHypothesisCard(item, index, evaluationMap={}, deepMap={}) { const families=(item.strategy_families||[]).slice(0,4); const metrics=(item.proposed_metrics||[]).slice(0,3); const ev=evaluationMap[item.hypothesis_id]||{}; const deep=deepMap[item.hypothesis_id]||{}; const disposition=ev.disposition||'pending'; const deepDisposition=deep.disposition||'pending'; const count=ev.metrics?.proxy_case_count; const signalCases=deep.metrics?.source_signal_case_count; return `<article class="source-hypothesis-card ${deepDisposition==='DEEP_SANDBOX_PASS_CANDIDATE'?'source-pass':disposition==='proxy_fail'||deepDisposition==='DEEP_SANDBOX_FAIL'?'source-fail':disposition==='needs_more_a_share_cases'?'source-watch':''}"><div class="source-hypothesis-top"><span>${String(index + 1).padStart(2,'0')} · ${esc(sourceDispositionText(disposition))}</span><small>A股${count?` · ${esc(count)} cases`:''}</small></div><h3>${esc(item.title)}</h3><p>${esc(shortText(item.thesis,118))}</p><div class="deep-status-row"><span>${esc(sourceDeepText(deepDisposition))}</span><small>${signalCases!==undefined?`${esc(signalCases)} 个源信号 case`:deepDisposition==='pending'?'等待 deep sandbox':'源特征已评估'}</small></div><div class="hypothesis-tags">${families.map(x=>`<small>${esc(x)}</small>`).join('')}</div><ul>${metrics.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><b>${deepDisposition==='DEEP_SANDBOX_PASS_CANDIDATE'?'可进入下一道 ranking gate 审核；仍不直接推荐':ev.confidence?`${esc(ev.confidence)} · 不直接推荐，只进入历史验证队列`:'不直接推荐，只进入历史验证队列'}</b></article>`; }
function deepSandboxBoard(report) { const summary=report?.summary||{}; const items=report?.items||[]; if(!report) return `<div class="deep-board pending"><b>A股 source deep sandbox</b><span>等待运行 deep sandbox。先完成特征覆盖，再验证主力资金/机构持仓/股东人数/因子等源特征是否真的改善历史 case。</span></div>`; return `<div class="deep-board"><div><b>A股 source deep sandbox</b><span>只保存派生特征和 hash，不保存原始 payload，不参与当前推荐排序。</span></div><div class="deep-board-metrics"><span>通过候选 <strong>${esc(summary.deep_sandbox_pass_candidate_count ?? 0)}</strong></span><span>深测失败 <strong>${esc(summary.deep_sandbox_fail_count ?? 0)}</strong></span><span>特征缺口 <strong>${esc(summary.blocked_feature_gap_count ?? 0)}</strong></span><span>源特征 case <strong>${esc(summary.case_feature_count ?? 0)}</strong></span></div>${items.length?`<div class="deep-result-strip">${items.slice(0,5).map(x=>`<small class="${x.disposition==='DEEP_SANDBOX_PASS_CANDIDATE'?'pass':'fail'}">${esc(x.title||x.hypothesis_id)} · ${esc(sourceDeepText(x.disposition))}</small>`).join('')}</div>`:''}</div>`; }
function diagnosticsActionText(value) { return ({collect_endpoint_history:'补历史样本',tighten_signal_definition:'收紧信号定义',add_risk_veto_before_retest:'先加风险否决再重测',collect_more_signal_cases:'扩大命中样本',rework_hypothesis:'重写假设'}[value]||value||'等待诊断'); }
function strategyDiagnosticsPanel(report) { if(!report) return `<div class="diagnostics-board pending"><b>策略诊断</b><span>等待 stock-agent 生成诊断报告。</span></div>`; const summary=report.summary||{}; const actions=(report.priority_actions||[]).slice(0,4); return `<div class="diagnostics-board"><div class="diagnostics-head"><div><p class="eyebrow">下一步不是加功能，是修策略</p><h3>当前没有任何 Tushare 源策略可以进入推荐排序。</h3><p>诊断会把“缺数据”和“历史表现差”分开处理，避免把主力/机构/游资线索误当成买点。</p></div><div class="diagnostics-metrics"><span>可进 ranking <strong>${esc(summary.rankable_strategy_count ?? 0)}</strong></span><span>优先动作 <strong>${esc(summary.priority_action_count ?? 0)}</strong></span><span>特征缺口 <strong>${esc(summary.feature_gap_count ?? 0)}</strong></span></div></div>${actions.length?`<div class="diagnostics-actions">${actions.map(item=>`<article><span>${esc(diagnosticsActionText(item.recommended_action))}</span><h4>${esc(item.label||item.hypothesis_id)}</h4><p>${esc(item.why||item.stock_agent_task||'等待下一轮验证')}</p></article>`).join('')}</div>`:''}<p class="diagnostics-boundary">这些动作只进入 stock-agent 沙盘队列，不生成真实交易、不影响当前候选排序。</p></div>`; }
function strategyEvidenceSnapshot(cases, dragonTiger, managedCycle, refinedSandbox, rankingGate) { const cs=cases?.summary||{}; const ds=dragonTiger?.summary||{}; const ms=managedCycle?.summary||{}; const rs=refinedSandbox?.summary||{}; const gs=rankingGate?.summary||{}; return `<section class="strategy-evidence-snapshot"><div><p class="eyebrow">本轮 stock-agent 证据快照</p><h3>组合策略出现 1 个可复核候选，但 ranking gate 仍未放行。</h3><p>这一步解决的是“哪些组合值得进入排序审查”，不是“策略可以买”。当前 gate 会检查样本数、股票分散度、月份覆盖和单股集中度。</p></div><div class="snapshot-metrics"><article><span>龙虎榜样本</span><b>${esc(ds.sample_count ?? ms.dragon_tiger_sample_count ?? 0)}</b><small>research-only</small></article><article><span>事件对齐 case</span><b>${esc(cs.a_share_dragon_tiger_research_sample_case_count ?? ms.a_share_dragon_tiger_research_sample_case_count ?? 0)}</b><small>20日后验</small></article><article><span>A股总 case</span><b>${esc(cs.a_share_case_count ?? ms.a_share_case_count ?? 0)}</b><small>当前样本池</small></article><article class="snapshot-pass"><span>组合候选</span><b>${esc(rs.refined_sandbox_pass_candidate_count ?? ms.refined_sandbox_pass_candidate_count ?? 0)}</b><small>仅供 gate review</small></article><article class="snapshot-veto"><span>Gate 放行</span><b>${esc(gs.ranking_gate_approved_count ?? ms.ranking_gate_approved_count ?? 0)}</b><small>样本不足</small></article><article class="snapshot-veto"><span>可进推荐排序</span><b>${esc(ms.rankable_strategy_count ?? 0)}</b><small>未过 gate</small></article></div><p class="snapshot-boundary">只做模拟研究；不接券商、不下单、不调用交易 webhook。</p></section>`; }
function refinedSandboxBoard(report) { if(!report) return `<div class="deep-board pending"><b>组合策略重测</b><span>等待 refined strategy sandbox。</span></div>`; const summary=report.summary||{}; const items=report.items||[]; return `<div class="deep-board refined-board"><div><b>组合策略重测</b><span>把失败的单信号加上风险否决后再测；通过只代表可进入 ranking gate review。</span></div><div class="deep-board-metrics"><span>组合数 <strong>${esc(summary.refined_strategy_count ?? 0)}</strong></span><span>可复核候选 <strong>${esc(summary.refined_sandbox_pass_candidate_count ?? 0)}</strong></span><span>失败 <strong>${esc(summary.refined_sandbox_fail_count ?? 0)}</strong></span><span>推荐排序 <strong>0</strong></span></div>${items.length?`<div class="deep-result-strip">${items.slice(0,5).map(x=>`<small class="${x.disposition==='REFINED_SANDBOX_PASS_CANDIDATE'?'pass':'fail'}">${esc(x.label||x.refined_strategy_id)} · ${esc(x.disposition==='REFINED_SANDBOX_PASS_CANDIDATE'?'可复核':'失败')}</small>`).join('')}</div>`:''}</div>`; }
function rankingGateBoard(report) { if(!report) return `<div class="deep-board pending"><b>Ranking gate</b><span>等待组合策略排序审查。</span></div>`; const summary=report.summary||{}; const items=report.items||[]; const first=items[0]||{}; const obs=first.observations||{}; return `<div class="deep-board ranking-gate-board"><div><b>Ranking gate：为什么还不能推荐？</b><span>当前组合策略已经被审查，但样本数和分散度还不够，不能进入选股排序。</span></div><div class="deep-board-metrics"><span>审查 <strong>${esc(summary.ranking_gate_reviewed_count ?? 0)}</strong></span><span>放行 <strong>${esc(summary.ranking_gate_approved_count ?? 0)}</strong></span><span>阻断 <strong>${esc(summary.ranking_gate_blocked_count ?? 0)}</strong></span><span>推荐排序 <strong>${summary.ranking_impact_allowed?'允许':'0'}</strong></span></div>${items.length?`<div class="ranking-gate-detail"><h4>${esc(first.label||first.refined_strategy_id)} · ${esc(first.ranking_gate_disposition==='RANKING_GATE_APPROVED_FOR_SIMULATION_SORT'?'可进入模拟排序':'仍需更多证据')}</h4><p>case ${esc(obs.case_count ?? 0)} 个，股票 ${esc(obs.unique_symbol_count ?? 0)} 只，月份 ${esc(obs.entry_month_count ?? 0)} 个，最大单股占比 ${obs.max_single_symbol_case_share!==undefined && obs.max_single_symbol_case_share!==null ? esc((obs.max_single_symbol_case_share*100).toFixed(0)+'%') : 'N/A'}。</p><div class="deep-result-strip">${(first.ranking_gate_blockers||[]).slice(0,5).map(x=>`<small class="fail">${esc(x)}</small>`).join('')||'<small class="pass">ranking gate approved</small>'}</div></div>`:''}</div>`; }
function sampleExpansionBoard(report) { if(!report) return `<div class="deep-board pending"><b>stock-agent 下一轮扩样本</b><span>等待样本扩展计划。</span></div>`; const s=report.summary||{}; const task=(report.tasks||[])[0]||{}; const shortfalls=task.shortfalls||[]; return `<div class="deep-board sample-expansion-board"><div><b>stock-agent 下一轮扩样本</b><span>把 gate blocker 自动翻译成后台任务：更多月份、更多股票、降低单股集中度。</span></div><div class="deep-board-metrics"><span>任务 <strong>${esc(s.expansion_task_count ?? 0)}</strong></span><span>Lookback <strong>${esc(s.next_lookback_dates ?? 'N/A')}</strong></span><span>股票上限 <strong>${esc(s.next_max_symbols ?? 'N/A')}</strong></span><span>每股事件 <strong>${esc(s.next_max_events_per_symbol ?? 'N/A')}</strong></span></div>${task.recommended_collect_command?`<div class="ranking-gate-detail"><h4>建议 stock-agent 执行</h4><p>${esc(task.recommended_collect_command)}</p><div class="deep-result-strip">${shortfalls.slice(0,5).map(x=>`<small class="fail">${esc(x.task)}</small>`).join('')}</div></div>`:''}</div>`; }
function stockAgentTaskText(latestRun, latestExit, refinedPass, reviewed, gateApproved, canRecommend, cycle) {
  return [
    'Project Aegis / OpenClaw stock-agent 任务',
    '',
    '目标：继续改进 A股 Tushare 策略上游验证，不生成用户推荐。',
    `最近运行：${latestRun}`,
    `最近 exit_code=${latestExit}`,
    `当前证据：refined_sandbox_pass_candidate_count=${refinedPass}`,
    `ranking_gate_reviewed_count=${reviewed}`,
    `ranking_gate_approved_count=${gateApproved}`,
    `user_facing_suggestion_allowed=${canRecommend ? 'true' : 'false'}`,
    `deep_sandbox_fail_count=${cycle.deep_sandbox_fail_count ?? 'N/A'}`,
    `tuned_fail_count=${cycle.tuned_fail_count ?? 'N/A'}`,
    '',
    '允许执行：make stock-agent-a-share-strategy-cycle-managed-expanded',
    '允许写入：本地 strategy sandbox/report/cache 派生产物。',
    '禁止：读取或打印密钥、真实交易、券商 API、webhook、下单、修改 Dashboard Contract、绕过 Evidence Gate。',
    'Gate 规则：ranking_gate_approved_count=0 或 user_facing_suggestion_allowed=false 时，不能进入 Dashboard 推荐排序。',
    '',
    '返回格式：命令、exit code、报告路径、sha256、关键计数、阻塞点、下一步。'
  ].join('\n');
}
function strategyCommandCenter(refinedSandbox, rankingGate, diagnostics, managedCycle, fullYearCoverage, strategyCases, dragonTiger) {
  const refined = refinedSandbox?.summary || {};
  const gate = rankingGate?.summary || {};
  const diag = diagnostics?.summary || {};
  const cycle = managedCycle?.summary || {};
  const refinedPass = Number(refined.refined_sandbox_pass_candidate_count ?? cycle.refined_sandbox_pass_candidate_count ?? 0);
  const gateApproved = Number(gate.ranking_gate_approved_count ?? cycle.ranking_gate_approved_count ?? 0);
  const reviewed = Number(gate.ranking_gate_reviewed_count ?? cycle.ranking_gate_reviewed_count ?? 0);
  const canRecommend = gateApproved > 0;
  const latestRun = managedCycle?.generated_at || '数据未提供';
  const latestExit = managedCycle?.overall_exit_code ?? 'N/A';
  const taskText = stockAgentTaskText(latestRun, latestExit, refinedPass, reviewed, gateApproved, canRecommend, cycle);
  const gateReason = canRecommend ? '已有策略通过 ranking gate，可进入模拟排序。' : refinedPass === 0 ? 'refined sandbox 通过数为 0，ranking gate 没有可审查对象。' : `已有 ${refinedPass} 个 refined 候选，但 ranking gate 放行仍为 0。`;
  const nextCommand = 'make stock-agent-a-share-strategy-cycle-managed-expanded';
  return `<section class="strategy-command-center ${canRecommend?'ready':'hold'}" aria-label="策略指挥台"><div class="strategy-command-head"><span>策略指挥台</span><h3>${canRecommend?'A股策略可进入模拟排序':'A股策略还不能推荐'}</h3><p>这里先给结论：OpenClaw 已跑、Gate 没放行、下一步继续让 stock-agent 做历史沙盘和证据收集。</p></div><div class="strategy-command-grid"><article><small>1 · OpenClaw 最近运行</small><b>${esc(latestExit===0?'PASS':'待复核')}</b><p>${esc(latestRun)} · exit ${esc(latestExit)} · 命令 ${esc(cycle.command_count ?? 'N/A')} 条，失败 ${esc(cycle.failed_command_count ?? 'N/A')} 条。</p></article><article class="gate-card"><small>2 · Gate 原因</small><b>${canRecommend?'已放行':'未放行'}</b><p>${esc(gateReason)} 推荐排序权限：${canRecommend?'允许':'禁止'}。</p></article><article><small>3 · 下一步命令</small><b>继续验证</b><p>${esc(nextCommand)}</p><button type="button" data-copy-stock-agent-task="${esc(taskText)}">复制给 stock-agent</button></article></div><div class="strategy-command-facts"><span>A股 case ${esc(strategyCases?.summary?.a_share_case_count ?? cycle.a_share_case_count ?? 'N/A')}</span><span>龙虎榜样本 ${esc(dragonTiger?.summary?.sample_count ?? cycle.dragon_tiger_sample_count ?? 'N/A')}</span><span>全A股一年 ${esc(coverageShortLabel(fullYearCoverage) || cycle.full_year_coverage_answer || 'NO')}</span><span>诊断动作 ${esc(diag.priority_action_count ?? cycle.strategy_priority_action_count ?? 0)}</span></div><p class="strategy-command-boundary">只做模拟研究；不接券商、不下单、不调用交易 webhook；Gate=0 时不进入用户建议。</p></section>`;
}
function strategyGateSummary(refinedSandbox, rankingGate, sampleExpansion, diagnostics, managedCycle) {
  const refined = refinedSandbox?.summary || {};
  const gate = rankingGate?.summary || {};
  const expansion = sampleExpansion?.summary || {};
  const diag = diagnostics?.summary || {};
  const cycle = managedCycle?.summary || {};
  const refinedPass = Number(refined.refined_sandbox_pass_candidate_count ?? cycle.refined_sandbox_pass_candidate_count ?? 0);
  const gateApproved = Number(gate.ranking_gate_approved_count ?? cycle.ranking_gate_approved_count ?? 0);
  const reviewed = Number(gate.ranking_gate_reviewed_count ?? cycle.ranking_gate_reviewed_count ?? 0);
  const canRecommend = gateApproved > 0;
  const reason = canRecommend ? '已有策略通过 gate，可进入模拟排序。' : refinedPass === 0 ? '上游 refined sandbox 还没有候选，所以 ranking gate 没有可审查对象。' : `已有 ${refinedPass} 个 refined 候选，但 ranking gate 仍未放行。`;
  const nextAction = refinedPass === 0 ? '让 stock-agent 先修策略上游：风险否决前置、扩样本、重测主力/龙虎榜/筹码组合。' : expansion.expansion_task_count ? `按扩样本计划继续：lookback ${expansion.next_lookback_dates ?? 'N/A'}，股票上限 ${expansion.next_max_symbols ?? 'N/A'}。` : '继续补样本与月份覆盖，再进入 ranking gate。';
  const command = 'make stock-agent-a-share-strategy-cycle-managed-expanded';
  const latestRun = managedCycle?.generated_at || '数据未提供';
  const latestExit = managedCycle?.overall_exit_code ?? 'N/A';
  const taskText = stockAgentTaskText(latestRun, latestExit, refinedPass, reviewed, gateApproved, canRecommend, cycle);
  return `<section class="gate-command ${canRecommend?'gate-ok':'gate-hold'}" aria-label="策略 Gate 摘要"><div class="gate-command-copy"><p class="eyebrow">策略页先看这里</p><h3>${canRecommend?'有策略可进入模拟排序':'今天没有任何 A 股策略可推荐'}</h3><p>${esc(reason)} 这不是“没看懂策略”，而是证据链还没允许它进入用户建议。</p></div><div class="gate-command-metrics"><article><span>Refined 通过</span><b>${esc(refinedPass)}</b><small>上游候选</small></article><article><span>Gate 审查</span><b>${esc(reviewed)}</b><small>ranking gate</small></article><article><span>Gate 放行</span><b>${esc(gateApproved)}</b><small>可影响排序</small></article><article><span>推荐权限</span><b>${canRecommend?'允许':'禁止'}</b><small>simulation-only</small></article></div><div class="gate-next"><b>OpenClaw 下一步</b><span>${esc(nextAction)}</span><small>最近运行 ${esc(latestRun)} · exit ${esc(latestExit)} · 诊断动作 ${esc(diag.priority_action_count ?? cycle.strategy_priority_action_count ?? 0)} · deep fail ${esc(cycle.deep_sandbox_fail_count ?? 'N/A')} · tuned fail ${esc(cycle.tuned_fail_count ?? 'N/A')}</small></div><div class="stock-agent-task-card"><div><b>可复制给 stock-agent 的下一步任务</b><span>${esc(command)}</span><small>最近 exit ${esc(latestExit)}；只做历史沙盘和证据收集；Gate=0 时不推荐、不排序。</small></div><button type="button" data-copy-stock-agent-task="${esc(taskText)}">复制 stock-agent 任务</button></div><button class="page-jump" type="button" data-page-jump="evidence">看证据文件</button></section>`;
}
function fullYearCoverageBoard(report) { if(!report) return `<div class="deep-board pending"><b>全A股一年覆盖</b><span>等待覆盖计划报告。当前不能声称已有过去一年全A股历史记录。</span></div>`; const cache=report.current_cache||{}; const target=report.target||{}; const plan=report.overnight_openclaw_plan||{}; const retry=report.current_day_retry||{}; const ok=report.answer_label==='YES'; const waiting=isWaitingCurrentDayDaily(report); const blockers=report.blockers||[]; const retryTime=retry.retry_not_before_local_time||'收盘后'; const retryCommand=retry.command||'make build-p23-2-historical-market-cache START_DATE=20250713 END_DATE=20260713'; const headline=ok?'已具备当前一年全市场候选缓存':waiting?'已覆盖到上一交易日，等待今日日线':'当前还不能说已有过去一年全A股记录'; const explanation=waiting?`目标区间 ${esc(target.target_start)} 到 ${esc(target.target_end)}。本地缓存已到 ${esc(cache.daily_end)}；${esc(target.target_end)} 的 Tushare 日线暂未发布，${esc(retryTime)} 后重试即可。`:`目标区间 ${esc(target.target_start)} 到 ${esc(target.target_end)}。本地缓存区间 ${esc(cache.daily_start)} 到 ${esc(cache.daily_end)}，因此当前只能作为历史样本/旧缓存证据，不能冒充最新一年全市场验证。`; return `<section class="strategy-evidence-snapshot full-year-board"><div><p class="eyebrow">全A股一年数据覆盖</p><h3>${headline}</h3><p>${explanation}</p></div><div class="snapshot-metrics"><article class="${ok?'snapshot-pass':'snapshot-veto'}"><span>结论</span><b>${esc(coverageHeadline(report))}</b><small>${esc(coverageHint(report))}</small></article><article><span>缓存交易日</span><b>${esc(cache.daily_file_count ?? 0)}</b><small>daily_by_trade_date</small></article><article><span>股票基础表</span><b>${esc(cache.stock_basic_row_count ?? 0)}</b><small>stock_basic rows</small></article><article><span>缓存日线行</span><b>${esc(cache.total_daily_rows ?? 0)}</b><small>历史横截面</small></article><article><span>建议批次</span><b>${esc(waiting?retryTime:plan.estimated_batch_count ?? 0)}</b><small>${esc(waiting?'不放松 Gate':`${plan.recommended_batch_size_trade_dates ?? 0} 日/批`)}</small></article><article class="snapshot-veto"><span>推荐影响</span><b>0</b><small>需 gate 放行</small></article></div>${waiting?`<div class="stock-agent-task-card"><div><b>收盘后重试命令</b><span>${esc(retryCommand)}</span><small>成功后再跑 coverage plan 和 stock-agent strategy cycle；Gate=0 不推荐。</small></div></div>`:''}${blockers.length?`<div class="ranking-gate-detail"><h4>${waiting?'当前阻塞点':'为什么不能直接用？'}</h4><div class="deep-result-strip">${blockers.slice(0,6).map(x=>`<small class="${waiting?'warn':'fail'}">${esc(x)}</small>`).join('')}</div></div>`:''}<p class="snapshot-boundary">OpenClaw 可高强度跑覆盖/沙盘验证，但只能只读或 simulation-only；不读密钥、不接券商、不下单、不调用交易 webhook。</p></section>`; }
function legacyStrategyDashboardPanel(report, evaluation, sourceProbe, sourceHypotheses, sourceHypothesisEvaluation, sourceFeatureCoverage, sourceDeepSandbox, refinedSandbox, rankingGate, sampleExpansion, strategyDiagnostics, strategyCases, dragonTiger, managedCycle) { const current=report?.strategy_blueprints||[]; const evalSummary=evaluation?.summary||{}; const probeSummary=sourceProbe?.summary||{}; const probeStatus=sourceProbe?.overall_status||'未探测'; const hypothesisSummary=sourceHypotheses||{}; const sourceEvalSummary=sourceHypothesisEvaluation?.summary||{}; const coverageSummary=sourceFeatureCoverage?.summary||{}; const deepSummary=sourceDeepSandbox?.summary||{}; const refinedSummary=refinedSandbox?.summary||{}; const gateSummary=rankingGate?.summary||{}; const expansionSummary=sampleExpansion?.summary||{}; const hypotheses=hypothesisSummary.hypotheses||[]; const evaluationMap=sourceHypothesisEvaluationMap(sourceHypothesisEvaluation); const deepMap=sourceDeepSandboxMap(sourceDeepSandbox); return `<div class="strategy-hero"><div><p class="eyebrow">策略不是信号，是筛选理由</p><h3>先看数据源，再看历史 case，最后才允许进入模拟研究。</h3><p>Tushare 的主力资金、机构持仓、股东人数、因子、龙虎榜和游资席位会被拆成独立源特征。当前已有 ${esc(refinedSummary.refined_sandbox_pass_candidate_count ?? 0)} 个组合策略候选，但 ranking gate 放行 ${esc(gateSummary.ranking_gate_approved_count ?? 0)} 个；stock-agent 已生成 ${esc(expansionSummary.expansion_task_count ?? 0)} 个扩样本任务。</p></div><div class="strategy-hero-metrics"><div><span>当前策略</span><b>${esc(current.length)}</b></div><div><span>A股 case</span><b>${esc(strategyCases?.summary?.a_share_case_count ?? 'N/A')}</b></div><div><span>Gate 放行</span><b>${esc(gateSummary.ranking_gate_approved_count ?? 0)}</b></div><div><span>扩样本任务</span><b>${esc(expansionSummary.expansion_task_count ?? 0)}</b></div></div></div><div class="strategy-next-step"><b>下一步策略开发顺序</b><span>优先 A 股：已探测 ${esc(probeSummary.endpoint_count ?? 0)} 个 Tushare 接口；龙虎榜/游资已有 ${esc(dragonTiger?.summary?.sample_count ?? 0)} 个样本、${esc(strategyCases?.summary?.a_share_dragon_tiger_research_sample_case_count ?? 0)} 个事件对齐 case。下一轮由 stock-agent 按计划扩到 lookback ${esc(expansionSummary.next_lookback_dates ?? 'N/A')}、股票上限 ${esc(expansionSummary.next_max_symbols ?? 'N/A')}。</span></div>${strategyEvidenceSnapshot(strategyCases,dragonTiger,managedCycle,refinedSandbox,rankingGate)}${strategyRoadmapPanel()}${strategyDiagnosticsPanel(strategyDiagnostics)}${deepSandboxBoard(sourceDeepSandbox)}${refinedSandboxBoard(refinedSandbox)}${rankingGateBoard(rankingGate)}${sampleExpansionBoard(sampleExpansion)}<h3 class="strategy-section-title">A 股特色策略假设队列</h3>${hypotheses.length?`<div class="source-hypothesis-grid">${hypotheses.map((item,index)=>sourceHypothesisCard(item,index,evaluationMap,deepMap)).join('')}</div>`:'<p class="empty">尚未生成 A 股策略假设队列，请先运行 build-a-share-tushare-source-hypotheses。</p>'}<h3 class="strategy-section-title">下一批 Tushare 增强数据源</h3><div class="strategy-module-grid">${tushareStrategyModules(sourceProbe).map(strategyModuleCard).join('')}</div><h3 class="strategy-section-title">当前 Aegis 正在用的策略</h3><div class="strategy-current-grid">${current.map(currentStrategyCard).join('')}</div><div class="strategy-boundary"><b>安全边界</b><span>先做 A 股：主力资金流向 → 龙虎榜/游资 → 机构持仓/股东变化 → 调研/治理。每一层只提升候选排序和风险判断，不生成真实交易动作。</span></div>`; }

function strategyDashboardPanel(report, evaluation, sourceProbe, sourceHypotheses, sourceHypothesisEvaluation, sourceFeatureCoverage, sourceDeepSandbox, refinedSandbox, rankingGate, sampleExpansion, strategyDiagnostics, strategyCases, dragonTiger, managedCycle, fullYearCoverage) {
  const current = report?.strategy_blueprints || [];
  const probeSummary = sourceProbe?.summary || {};
  const refinedSummary = refinedSandbox?.summary || {};
  const gateSummary = rankingGate?.summary || {};
  const expansionSummary = sampleExpansion?.summary || {};
  const hypothesisSummary = sourceHypotheses || {};
  const hypotheses = hypothesisSummary.hypotheses || [];
  const evaluationMap = sourceHypothesisEvaluationMap(sourceHypothesisEvaluation);
  const deepMap = sourceDeepSandboxMap(sourceDeepSandbox);
  return `${strategyCommandCenter(refinedSandbox,rankingGate,strategyDiagnostics,managedCycle,fullYearCoverage,strategyCases,dragonTiger)}${strategyGateSummary(refinedSandbox,rankingGate,sampleExpansion,strategyDiagnostics,managedCycle)}<div class="strategy-hero"><div><p class="eyebrow">策略不是信号，是筛选理由</p><h3>先看数据源，再看历史 case，最后才允许进入模拟研究。</h3><p>Tushare 的主力资金、机构持仓、股东人数、因子、龙虎榜和游资席位会被拆成独立源特征。当前已有 ${esc(refinedSummary.refined_sandbox_pass_candidate_count ?? 0)} 个组合策略候选，但 ranking gate 放行 ${esc(gateSummary.ranking_gate_approved_count ?? 0)} 个；stock-agent 已生成 ${esc(expansionSummary.expansion_task_count ?? 0)} 个扩样本任务。</p></div><div class="strategy-hero-metrics"><div><span>当前策略</span><b>${esc(current.length)}</b></div><div><span>A股 case</span><b>${esc(strategyCases?.summary?.a_share_case_count ?? 'N/A')}</b></div><div><span>Gate 放行</span><b>${esc(gateSummary.ranking_gate_approved_count ?? 0)}</b></div><div><span>全市场一年</span><b>${esc(fullYearCoverage?.answer_label || 'NO')}</b></div></div></div><div class="strategy-next-step"><b>下一步策略开发顺序</b><span>优先 A 股：已探测 ${esc(probeSummary.endpoint_count ?? 0)} 个 Tushare 接口；龙虎榜/游资已有 ${esc(dragonTiger?.summary?.sample_count ?? 0)} 个样本、${esc(strategyCases?.summary?.a_share_dragon_tiger_research_sample_case_count ?? 0)} 个事件对齐 case。下一轮由 stock-agent 按计划扩到 lookback ${esc(expansionSummary.next_lookback_dates ?? 'N/A')}、股票上限 ${esc(expansionSummary.next_max_symbols ?? 'N/A')}。</span></div>${fullYearCoverageBoard(fullYearCoverage)}${strategyEvidenceSnapshot(strategyCases,dragonTiger,managedCycle,refinedSandbox,rankingGate)}${tushareStrategyMatrix(sourceProbe,sourceDeepSandbox,rankingGate,sampleExpansion,strategyCases,dragonTiger)}${strategyRoadmapPanel()}${strategyDiagnosticsPanel(strategyDiagnostics)}${deepSandboxBoard(sourceDeepSandbox)}${refinedSandboxBoard(refinedSandbox)}${rankingGateBoard(rankingGate)}${sampleExpansionBoard(sampleExpansion)}<h3 class="strategy-section-title">A 股特色策略假设队列</h3>${hypotheses.length?`<div class="source-hypothesis-grid">${hypotheses.map((item,index)=>sourceHypothesisCard(item,index,evaluationMap,deepMap)).join('')}</div>`:'<p class="empty">尚未生成 A 股策略假设队列，请先运行 build-a-share-tushare-source-hypotheses。</p>'}<h3 class="strategy-section-title">下一批 Tushare 增强数据源</h3><div class="strategy-module-grid">${tushareStrategyModules(sourceProbe).map(strategyModuleCard).join('')}</div><h3 class="strategy-section-title">当前 Aegis 正在用的策略</h3><div class="strategy-current-grid">${current.map(currentStrategyCard).join('')}</div><div class="strategy-boundary"><b>安全边界</b><span>先做 A 股：主力资金流向 → 龙虎榜/游资 → 机构持仓/股东变化 → 调研/治理。每一层只提升候选排序和风险判断，不生成真实交易动作。</span></div>`;
}

function render() { const invalid=[]; return Promise.all(Object.entries(sources).map(async([key,file])=>[key,await read(file,invalid)])).then(entries=>{
  const d=Object.fromEntries(entries);
  const positions=[positionFromRisk(d.crcl,{symbol:'CRCL',name:'数据未提供',market:'US',source:'CRCL 风险监控'}),positionFromRisk(d.vanke,{symbol:'000002.SZ',name:'数据未提供',market:'A',source:'万科A风险监控'}),{symbol:'00700.HK',name:'数据未提供',market:'HK',status:d.health?.hk_00700_status==='MISSING'?'MISSING':'UNKNOWN',riskVeto:false,risks:[],updated:d.health?.generated_at,nextCheck:null,source:'港股监控状态',missing:true}];
  const simItems=d.simulationBrief?.items||[]; const simCandidates=simItems.filter(x=>x.brief_status==='simulation_candidate');
  const watchlist=d.watchlist?.stocks||[]; const vm={health:d.health,gate:d.gate,daily:d.daily,positions,watchlist,invalidSources:invalid}; const decision=deriveDailyDecision(vm);
  const selectionPanel=selectionWorkbenchPanel(d.stockSelection,d.feedback,d.pilot,decision);
  const system=d.health?.health_status || d.gate?.overall_verdict || 'UNKNOWN'; const daily=d.daily?.overall_verdict || 'UNKNOWN';
  byId('today-date').textContent=new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',weekday:'short'}).format(new Date());
  byId('system-status').textContent=stateLabel(system); byId('daily-status').textContent=stateLabel(daily); byId('data-time').textContent=`数据更新时间：${d.health?.generated_at || d.daily?.generated_at || '数据未提供'}`;
  byId('command-strip').innerHTML=commandStrip(decision,d.stockSelection,d.fullYearCoverage,d.rankingGate,d.feedback);
  const hero=byId('decision'); hero.className=`section hero ${decision.state==='Risk / Exit'?'risk-state':decision.state==='BLOCKED'?'blocked-state':decision.state==='Watch / Review'||decision.state==='Ready'?'warn-state':''}`;
  byId('decision-content').innerHTML=`${tag(decision.state)}<h2 class="decision-title">${esc(decision.title)}</h2><p class="decision-summary">${esc(decision.summary)}</p><div class="decision-actions"><div class="directive"><b>今天允许做什么</b>${esc(decision.allowed)}</div><div class="directive forbid"><b>今天禁止做什么</b>${esc(decision.forbidden)}</div></div><div class="metrics"><div class="metric"><span>风险数量</span><strong>${decision.risk_count}</strong></div><div class="metric"><span>可执行候选</span><strong>${decision.action_count}</strong></div><div class="metric"><span>下次检查</span><strong>${esc(decision.next_check)}</strong></div></div>${decision.blocking_reasons.length?`<p class="muted">${esc(decision.blocking_reasons.join('；'))}</p>`:''}`;
  byId('overview-actions').innerHTML=morningReadinessPanel(decision,d.stockSelection,d.fullYearCoverage,d.stockAgentCycle,d.rankingGate)+actionHub(decision,d.feedback,d.dashboardIntent);
  byId('overview-candidates').innerHTML=overviewCandidates(d.stockSelection);
  const risks=positions.filter(p=>p.status==='Exit'||p.riskVeto).slice(0,3); byId('risk-summary').textContent=risks.length?`${risks.length} 项需复核`:'无紧急风险'; byId('risk-content').innerHTML=risks.length?risks.map(riskCard).join(''):'<p class="empty">当前没有紧急风险。</p>';
  byId('holdings-summary').textContent=`${positions.length} 个持仓/监控对象`; byId('holdings-content').innerHTML=positions.map(holdingCard).join('');
  byId('next-summary-mini').textContent=String(decision.next_check||'每日 08:00'); byId('next-content').innerHTML=`<p class="daily-line"><b>${esc(decision.next_check)}</b> · 每日 08:00 自动检查</p><p class="muted">出现风险条件、数据异常或自动检查失败时，应提前复核。</p>`;
  byId('local-intents-content').innerHTML=localIntentBoard(d.feedback,d.dashboardIntent);
  const actions=watchlist.filter(x=>x.status==='Action'); const simulationPanel=simCandidates.length?`<details class="simulation-use more-candidates"><summary>旧建议简报：${simCandidates.map(x=>esc(x.symbol)).join('、')}</summary><div class="grid details-content">${simCandidates.map(simulationCandidateCard).join('')}</div>${blockedSimulationList(simItems)}</details>`:''; const actionPanel=actions.length?actions.map(candidateCard).join(''):'<p class="empty">没有实盘可执行候选。Aegis 只做选股研究和纸面模拟，不自动交易。</p>'; byId('action-content').innerHTML=selectionPanel+simulationPanel+actionPanel;
  byId('strategy-content').innerHTML=strategyDashboardPanel(d.stockSelection,d.strategyCaseEvaluation,d.strategySourceProbe,d.sourceHypotheses,d.sourceHypothesisEvaluation,d.sourceFeatureCoverage,d.sourceDeepSandbox,d.refinedSandbox,d.rankingGate,d.sampleExpansion,d.strategyDiagnostics,d.strategyCases,d.dragonTiger,d.stockAgentCycle,d.fullYearCoverage);
  const watchOnly=watchlist.filter(x=>x.status!=='Action'); const focus=watchOnly.slice(0,5); byId('watchlist-summary-mini').textContent=watchOnly.length?`${watchOnly.length} 只观察，重点 ${focus.length} 只`:'暂无观察名单'; byId('watchlist-content').innerHTML=watchOnly.length?`<p class="watch-summary">观察名单（${watchOnly.length}）　重点关注：${focus.length} 只</p><div class="watch-grid">${focus.map(candidateCard).join('')}</div>${watchOnly.length>focus.length?`<details><summary>查看全部观察名单</summary><div class="watch-grid details-content">${watchOnly.slice(focus.length).map(candidateCard).join('')}</div></details>`:''}`:'<p class="empty">候选列表尚未生成。</p>';
  const a=watchlist.length?'谨慎（仅有观察候选）':'数据不足'; const hk=d.health?.hk_00700_status==='MISSING'?'数据不足':'数据不足'; const us=positions[0].status==='Exit'?'注意（存在退出复核）':'数据不足'; byId('market-summary-mini').textContent=`A股 ${a} / 港股 ${hk} / 美股 ${us}`; byId('market-content').innerHTML=`<p class="market-line">A股：<b>${a}</b>　港股：<b>${hk}</b>　美股：<b>${us}</b></p><p class="muted">仅在真实状态为可执行且无风险阻断时允许行动。</p>`;
  const metrics=d.rolling?.portfolio_metrics||{},benchmark=d.rolling?.benchmark_metrics||{}; byId('backtest-content').innerHTML=`${strategySandboxPanel(d.strategySandbox,d.strategyCases,d.strategyCaseEvaluation)}<p class="research-notice">历史策略不等于当前 Watchlist。<br>回测结果不是实盘收益。</p><div class="research-summary"><div class="metric"><span>期数</span><strong>${esc(d.rolling?.periods_count)}</strong></div><div class="metric"><span>总收益</span><strong>${fmtPct(metrics.total_return)}</strong></div><div class="metric"><span>最大回撤</span><strong>${fmtPct(metrics.max_drawdown)}</strong></div><div class="metric"><span>基准收益</span><strong>${fmtPct(benchmark.total_return)}</strong></div><div class="metric"><span>超额收益</span><strong>${fmtPct(d.rolling?.excess_return)}</strong></div><div class="metric"><span>原始价格审计</span><strong>${esc(stateLabel(d.audit?.overall_verdict))}</strong></div></div><details><summary>查看研究条件</summary><ul class="detail-list"><li>年化收益：${fmtPct(metrics.annualized_return)}</li><li>波动率：${fmtPct(metrics.volatility)}</li><li>夏普比率：${esc(metrics.sharpe)}</li><li>胜率：${fmtPct(metrics.win_rate)}</li><li>要求按历史时点取数：${d.rolling?.point_in_time_required?'是':'否'}</li><li>静态快照回测：${d.rolling?.static_snapshot_backtest?'是':'否'}</li><li>存在幸存者偏差提示：${d.rolling?.survivorship_bias_warning?'是':'否'}</li><li>历史策略与当前候选等价：${d.rolling?.strategy_equivalence_claimed?'是':'否'}</li></ul></details>`;
  byId('daily-content').innerHTML=d.daily?`<p class="daily-line">每日 08:00　最近运行：${esc(d.daily.generated_at)}　结果：${tag(d.daily.overall_verdict)}　下次检查：每日 08:00</p><details><summary>查看检查详情</summary><ul class="detail-list">${stage(d.daily,'morning_health','系统健康')}${stage(d.daily,'rolling_pipeline','滚动回测')}${stage(d.daily,'final_evidence_gate','证据检查')}<li>锁残留：${d.daily.lock_recovery?.stale_lock_found?'有':'无'}</li></ul></details>`:'<p class="empty">自动检查状态未知。</p>';
  byId('evidence-content').innerHTML=`<p>证据检查：${tag(d.gate?.overall_verdict)}　数据流水线历史：${d.history?.runs?.length ?? '数据未提供'} 条记录　原始价格审计：${tag(d.audit?.overall_verdict)}</p><ul class="detail-list">${reportLink('选股工作台数据',sources.stockSelection)}${reportLink('选股+资讯简报','stock_selection_news_digest_latest.md')}${reportLink('A股 Tushare 策略源探测',sources.strategySourceProbe)}${reportLink('A股 source hypothesis 队列',sources.sourceHypotheses)}${reportLink('A股 source hypothesis 代理评估',sources.sourceHypothesisEvaluation)}${reportLink('A股龙虎榜/游资研究样本',sources.dragonTiger)}${reportLink('A股 source feature 覆盖',sources.sourceFeatureCoverage)}${reportLink('A股 source deep sandbox',sources.sourceDeepSandbox)}${reportLink('A股 refined strategy sandbox',sources.refinedSandbox)}${reportLink('A股 refined ranking gate',sources.rankingGate)}${reportLink('A股样本扩展计划',sources.sampleExpansion)}${reportLink('A股全市场一年覆盖计划',sources.fullYearCoverage)}${reportLink('A股策略诊断',sources.strategyDiagnostics)}${reportLink('stock-agent managed cycle',sources.stockAgentCycle)}${reportLink('策略验证输入','aegis_strategy_validation_input_latest.json')}${reportLink('策略沙盘覆盖',sources.strategySandbox)}${reportLink('逐标的历史 case',sources.strategyCases)}${reportLink('case 结果评估',sources.strategyCaseEvaluation)}${reportLink('Dashboard 本地按钮回执',sources.dashboardIntent)}${reportLink('最近按钮回传',sources.feedback)}${reportLink('当前模拟建议简报',sources.simulationBrief)}${reportLink('证据检查',sources.gate)}${reportLink('数据流水线历史',sources.history)}${reportLink('原始价格审计',sources.audit)}${reportLink('滚动回测历史',sources.rollingHistory)}${reportLink('信号快照','a_share_signal_snapshots_latest.json')}</ul><p class="muted">不可读取数据：${invalid.length?esc(invalid.length):'无'}</p>`;
  markSelectedActionButtons();
 }); }
byId('refresh').addEventListener('click',render);
setupNavigation();
render().then(()=> {
  const page = (location.hash || '#today').replace('#','');
  if (document.querySelector(`[data-page-view="${page}"]`)) activatePage(page);
});
