# Claude Cowork START HERE — Project Aegis P0

> 用途：把本文件和 `Project_Aegis_MASTER_SPEC.md` 一起拖进 Claude Mac 桌面版 Cowork。  
> 目标：让 Claude Cowork 从 Phase 0 开始实现 Project Aegis，不发散、不跳阶段、不重写 Dashboard UI。

---

## 你现在的角色

你是 Project Aegis 的 Claude Cowork 实现助手。

你必须先阅读并遵守：

- `Project_Aegis_MASTER_SPEC.md`

该文件是 Project Aegis 的 Master Spec / Single Source of Truth。

如果本次对话没有附带 `Project_Aegis_MASTER_SPEC.md`，你必须先要求用户上传该文件，不要凭记忆开发。

---

## 绝对规则

1. 只做 **Phase 0: Project Skeleton**。
2. 不要提前做 Phase 1 或后续模块。
3. 不要实现 Tushare Adapter。
4. 不要实现 Expert Committee。
5. 不要实现 Decision Engine。
6. 不要实现 Paper Trading。
7. 不要实现 Time Travel Backtest。
8. 不要重写 `dashboard/index.html` 的 UI。
9. 不要使用综合评分。
10. 不要编造市场数据、推荐、收益、虚拟盘结果。
11. 不要写入真实 token、cookie、API key。
12. 不要把新代码塞进旧 `stock-picker` 项目。
13. 旧 `stock-picker` 只能参考数据层，不能复用评分逻辑。
14. 每次暂停前必须更新 `docs/HANDOFF.md`。

---

## 本轮只允许完成的 Phase 0 事项

请创建 Project Aegis 的最小工程骨架：

```text
project-aegis/
├── README.md
├── .env.example
├── pyproject.toml
├── config/
├── data/
├── aegis/
├── dashboard/
├── scripts/
├── tests/
└── docs/
```

Phase 0 允许创建：

- 目录结构
- 配置文件骨架
- `.env.example`
- `pyproject.toml`
- `README.md`
- 数据模型文件骨架
- JSONL 工具骨架
- 基础测试文件
- `docs/HANDOFF.md`

Phase 0 不允许实现真实业务逻辑。

---

## 你开始写文件前，先回复用户这三项

在改文件之前，先输出：

1. Phase 0 的交付物清单；
2. 本轮会创建或修改的文件；
3. 本轮会运行的测试命令。

用户确认或未明确反对后，再开始修改文件。

---

## Phase 0 验收标准

Phase 0 完成后必须满足：

1. 项目目录结构存在；
2. `README.md` 存在；
3. `.env.example` 存在，且只包含变量名，不包含真实 token；
4. `pyproject.toml` 存在；
5. `config/` 下存在基础 YAML 配置文件；
6. `aegis/models/` 下存在 P0 核心数据模型骨架；
7. `aegis/utils/jsonl.py` 存在；
8. `tests/` 下存在基础测试；
9. `pytest` 可运行；
10. `docs/HANDOFF.md` 已更新；
11. 没有实现 Phase 1+ 内容；
12. 没有真实 API key；
13. 没有综合评分逻辑。

---

## 本轮结束时必须输出

完成后，请输出：

```text
Phase 0 完成情况：
- 已创建/修改文件：...
- 已运行测试：...
- 测试结果：...
- 未完成事项：...
- 下一步建议：Phase 1 Data Pipeline
```

并确认：

```text
已更新 docs/HANDOFF.md
```

---

## 现在开始

请读取 `Project_Aegis_MASTER_SPEC.md`，然后只执行 Phase 0。
