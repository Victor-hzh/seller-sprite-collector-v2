# SellerSprite Collector V2

独立实验仓库：Victor-hzh/seller-sprite-collector-v2。下载器、清洗程序、原始榜单和新版看板源码都在此仓库；Sites 仅发布前端页面，不修改原看板仓库。

## 数据目录与自动更新

| 目录 | 用途 |
| --- | --- |
| `data/source/YYYY-MM-DD/` | 上传卖家精灵导出的原始 Excel；保留原文件。 |
| `cleaning/` | 清洗、双榜单合并、规则、汇率和压缩程序。 |
| `data/processed/` | 自动生成的 `dashboard-data.json`、浏览器读取的 `dashboard-data.json.gz` 和 `cleaning-audit.json`。 |

上传新的 Excel 到 `data/source/` 后，GitHub Actions 自动运行 `cleaning/` 中的测试和程序，读取全部原始文件，更新 `data/processed/`；合并后的 Excel 另存于 `data/merged/`。看板只读取 `data/processed/dashboard-data.json.gz`，不会读取原始 Excel。清洗失败时保留上一版数据，不发布不完整结果。网页代码改变时需要另行更新 Sites；仅更新 Excel 和清洗结果不需要重新发布网页。

## 当前功能

- 7 个站点、5 个品类，共 35 个品类组、36 个下载来源。
- 德国洗地机新增 2077530031，与 218877962031 合并。
- 新文件名包含 Node 编号，原始 Excel 始终保留。
- 按日期、站点、品类合并，ASIN 去重，按月销售额排序。
- 同 ASIN 数值冲突按 tasks_v2.json 来源顺序选用一份，不相加，审计记录包含差异。
- 大盘计算包含全部清洗后的产品，不截取 Top50；品牌和卖家汇总重新生成。
- cleaning/cleaning_rules.json 支持各站点品类 ASIN 保留/排除及标题正则排除；德国洗地机已启用家用吸拖洗一体机范围，其他品类仍保留原规则。
- data/merged/YYYY-MM-DD 保存合并清洗Excel，保留原70列、图片、商品链接、列宽、冻结首行及DE/Brands/Sellers/Note工作表。
- 合并表的 # 是竞品销售额顺序，原始小类BSR字段不修改。Brands/Sellers重新汇总，市场份额沿用原表月销量口径。
- 原始商品表没有逐SKU年销量/年销售额，所以重算汇总的年指标留空，不相加原表的整榜年度汇总。
- 未能确认品类的产品列为 review，不进入已确认大盘；审计记录保留ASIN、标题和来源。
- 看板总览、品牌、价格带和机会对比使用全部清洗产品，TopN仅限制商品列表展示。竞品排名和来源BSR分别显示。
- 旧格式历史文件也可以读取；缺少新增来源的历史日期会标记 missingSourceNodes。

## 源码运行

安装 requirements.txt。双击 RUN_DOWNLOAD_V2.bat，或运行：

```text
python collector_app.py check
python collector_app.py inspect
python collector_app.py login
python collector_app.py credentials
python collector_app.py run
python collector_app.py run-upload
python collector_app.py upload-auto
python collector_app.py clean
python collector_app.py upload
```

仅测试德国新增来源：python collector_app.py run --task DE_WET_DRY_FLOOR_WASHER_2077530031。
桌面版仍可通过 `SellerSpriteCollector.exe --cli run --task DE_WET_DRY_FLOOR_WASHER_2077530031` 使用命令行。

浏览器初始化时需要在专用 Chrome 中安装卖家精灵插件；团队账号由程序自动登录。验证码仍需人工完成。
下载前先检查卖家精灵登录状态并自动登录，检查通过后才进入原来的浏览器、登录与导出逻辑；每个榜单仍检查掉线并尝试重登。未自动启动真实下载；新增来源需实测。

## 清洗规则

groups 中以 DE/Wet-Dry-Floor-Washer 这样的键区分站点和品类。
keep_asins 优先于 exclude_asins；未命中排除规则的产品默认保留。
exclude_title_patterns 是 Python 正则，需确认规则后再启用。
data/processed/cleaning-audit.json 记录被排除产品及重复产品的差异。
销售额缺失记录保留并排在最后，missingRevenueCount 标明缺失数量。
统计仍沿用原看板的月销量/月销售额字段；父子变体指标口径需另行核实。
得到的是来源榜单覆盖的竞品样本，不等同于全市场。来源覆盖不一致的历史日期不计算虚假的排名/销售环比。

## GitHub 数据更新

上传 data/source/YYYY-MM-DD 下的 Excel 后，Actions 自动重建 data/processed/ 下的 JSON、压缩数据和审计记录。
读取失败时不覆盖上一份结果。仅重新构建数据与合并Excel，不部署网站。

## 实验看板

安装 package.json 中的依赖后运行 npm run dev。前端直接读取 GitHub 上 data/processed/dashboard-data.json.gz，Sites 只托管页面代码。
生产验证使用 npm run lint 和 npm run build。仅在独立仓库验证，不改变原网站。

## Windows 安装版

在 Actions → Build Windows EXE 的最新成功运行中下载 `SellerSpriteCollector-v2-Windows`，解压后双击 `SellerSpriteCollector-v2-Setup.exe` 安装。开始菜单和桌面会出现“SellerSprite Collector V2”。也保留免安装 ZIP，供便携使用。安装版用户无需安装 Python、配置虚拟环境或设置环境变量；开发者本地构建时运行 `python tools/build_exe.py` 和 `python tools/build_installer.py`（构建机需有 NSIS）。

窗口首次使用先完成本地环境配置并点击“连接 GitHub”，用拥有本仓库 Contents 读写权限的个人令牌连接一次。之后选择下载范围并点击“下载并更新看板”，程序自动检查卖家精灵登录状态、下载 Excel、向 V2 仓库提交新增或变化的 Excel；GitHub Actions 随后自动清洗、合并并更新看板 JSON。令牌通过 Windows 当前用户加密保存在 `runtime/github_token.dpapi`，不会加入仓库或安装包。下载支持全部 36 个来源、单榜单、跳过已完成任务和强制重下；上传失败可单独重试，不需要重新下载。“仅下载”和手动 GitHub 上传页面保留备用。

首次仍需安装 Chrome，并在程序打开的专用 Chrome 中安装卖家精灵插件；团队账号自动登录，验证码人工完成。程序不附带浏览器、插件或登录状态。团队账号按项目所有人的要求随公开 V2 仓库与安装包提供；本机覆盖账号由当前 Windows 用户加密，保存在 `runtime/`。不要将本机 `runtime/`、浏览器配置或 `.venv` 上传到仓库。安装版数据也保存在安装目录下；卸载程序时保留下载数据与登录状态，方便自行备份或删除。详见 `README_WINDOWS_GUI.txt`。

## 验证

python -m unittest discover -s tests -v

打包过程会运行 EXE 自检，验证配置和 Playwright 驱动启动；完整下载与另一台无 Python 电脑上的安装仍需实测。
