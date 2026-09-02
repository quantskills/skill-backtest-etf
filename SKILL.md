---
name: skill-backtest-etf
description: 使用 panda_data 和本地 parquet 做 ETF 策略回测，只做 ETF，不做因子分析，不用分钟线。
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: quantskills/skill-backtest-etf
  repository_url: https://github.com/quantskills/skill-backtest-etf
  project_type: skill
  collection: etf-research
  license: GPL-3.0-only
  creator: cuijie0317
  maintainer: abgyjaguo
  platforms: [claude-code, codex, cursor, hermes, openclaw]
---

# ETF 回测

## 目标

- 只做场内 ETF 策略回测
- 支持时序策略和截面策略
- 先快取数，再生成代码，再做回测

## 必须遵守

- 只做 ETF，不做非 ETF 标的。
- 必须从获得授权的来源安装 `panda_data 0.1.0`；SDK 未安装或版本不符时，先报告安装错误，不得探测 Parquet。本仓库不分发该第三方 SDK。
- 不做因子分析。
- 不使用分钟线回测。
- 不写账号、密码、token、私有路径到技能文件。
- `panda_data 0.1.0` 是访问本地 ETF Parquet 的必经 SDK：先安装 SDK，再读取 `.env`，最后调用 SDK；禁止绕过 SDK 直接扫描 Parquet 文件。
- 同一任务若已有由 `panda_data` 取得且通过数据契约的 DataFrame，可直接复用；否则只调用一次批量查询。
- 只请求所需 ETF、日期和字段；先用 `get_fund_detail` 建立在册 ETF 池，再批量取行情，禁止逐 ETF 全库扫描。
- 取数成功后立即打印行数、代码数、日期范围和缺失列，满足契约就进入回测。

## 标准流程（每次任务都执行）

1. 在当前 Python 3.12 环境从获得授权的来源安装并导入 `panda_data`，确认版本为 `0.1.0`；未通过不得读数据。
2. `load_dotenv` 读取 `.env`，校验 `PARQUET_ROOT_PATH` 可访问且包含 `fund_basic`、`fund_daily`（及需要时的复权行情目录）。不扫描整盘。
3. 优先复用本任务已由 `panda_data` 获取的完整面板；否则由 `panda_data` 根据 `.env` 访问本地 Parquet。SDK 只调用一次批量查询，结果在本任务内复用。
4. 用 `get_fund_detail(etf_lof_type="ETF", status="L")` 建立在册场内 ETF 池；用户未给股票池时，截面默认使用该池中数据覆盖率最高的前 20 只，并在报告披露。
5. 只取策略所需日线字段，按 `symbol,date` 去重并排序；生成独立代码到 `scripts/tests/`。
6. 先运行数据契约检查，再执行回测。代码失败时只修复根因并重跑一次，仍失败则返回阶段、异常、已检查项和修复建议。

## 口径要求

- 研究信号用 `get_fund_daily_post`
- 正式回测价格用 `get_fund_daily`
- ETF 股票池只取场内 ETF
- 信号和成交口径要分开
- 当日收盘生成的信号最早在下一交易日成交；默认使用下一交易日 `open`，没有 `open` 才允许明确披露的下一日 `close` 代理。
- 截面排名只使用调仓日及之前的数据，缺失标的不得以前值填充为未来数据；权重和现金合计为 1。
- 远程调用失败最多重试 2 次并使用指数退避；本地路径/权限错误不重试，直接返回修复建议。

## 输出要求

- 策略规则
- 回测区间
- 初始资金
- 总收益
- 年化收益
- 最大回撤
- Sharpe
- 交易次数
- 换手率、费用和滑点影响
- 最终净值
- 数据覆盖率、缺失交易日、实际成交时点
- 结论

## 按需读取参考文件

- 所有任务先读 `references/research_rules.md` 和 `panda_data_etf_whitelist.md`。
- 代码生成读 `references/strategy_codegen_assistant.md`；输出读 `references/output_contract.md`。
- 参数不完整时读 `references/prompt_template.md`，不要直接终止。
- 每个请求生成代码到 `scripts/tests/` 并执行；失败返回阶段、异常、检查结果和修复动作。
