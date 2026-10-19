# 数据清洗与合并流程

上传 `data/source/YYYY-MM-DD/` 中的卖家精灵 Excel 后，GitHub Actions 运行 `.github/workflows/build-dashboard-data.yml`。流程先运行测试，再读取原始 Excel、应用 `cleaning/cleaning_rules.json`，生成 `data/processed/dashboard-data.json`、`data/processed/cleaning-audit.json` 和 `data/merged/YYYY-MM-DD/` 中的合并 Excel。看板只读取处理后的数据。

清洗规则按 `default`（全部站点共享）、`categories`（品类）和 `groups`（站点与品类）依次叠加。明确排除的 ASIN 和标题模式不会进入看板；标题不足以确认品类的商品进入审计记录的待复核项，也暂不计入大盘。明确保留的 ASIN 可覆盖其他规则。

同一站点、品类和日期的多个榜单先合并，再按 ASIN 去重。相同 ASIN 在两个来源出现时保留配置顺序更靠前的来源的销量与销售额，并记录所有来源和数值差异，避免重复加总。不同 ASIN 的销售额按品牌及卖家汇总。德国洗地机使用两个来源，其余品类目前通常只有一个来源。

如自动构建失败，先查看 Actions 的失败步骤和 `data/processed/cleaning-audit.json`。修复代码后，可在 GitHub Actions 页面手动运行 “Build cleaned dashboard data”，对仓库中已有的 Excel 重新处理。
