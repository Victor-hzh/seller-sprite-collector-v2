# SellerSprite Collector V2

独立实验仓库：Victor-hzh/seller-sprite-collector-v2。没有网站部署流程，不修改原看板仓库。

## 当前功能

- 7 个站点、5 个品类，共 35 个品类组、36 个下载来源。
- 德国洗地机新增 2077530031，与 218877962031 合并。
- 新文件名包含 Node 编号，原始 Excel 始终保留。
- 按日期、站点、品类合并，ASIN 去重，按月销售额排序。
- 同 ASIN 数值冲突按 tasks_v2.json 来源顺序选用一份，不相加，审计记录包含差异。
- 大盘计算包含全部清洗后的产品，不截取 Top50；品牌和卖家汇总重新生成。
- cleaning_rules.json 支持各站点品类 ASIN 保留/排除及标题正则排除，默认没有自动排除规则。
- 旧格式历史文件也可以读取；缺少新增来源的历史日期会标记 missingSourceNodes。

## 源码运行

安装 requirements.txt。双击 RUN_DOWNLOAD_V2.bat，或运行：

```text
python collector_app.py check
python collector_app.py inspect
python collector_app.py credentials
python collector_app.py run
python collector_app.py clean
python collector_app.py upload
```

仅测试德国新增来源：python collector_app.py run --task DE_WET_DRY_FLOOR_WASHER_2077530031。
EXE 支持相同参数：SellerSpriteCollector.exe run --task DE_WET_DRY_FLOOR_WASHER_2077530031。

浏览器初始化时需要在专用 Chrome 中安装并登录卖家精灵。验证码仍需人工完成。
下载保持原来的浏览器、登录和导出逻辑。未自动启动真实下载；新增来源需实测。

## 清洗规则

groups 中以 DE/Wet-Dry-Floor-Washer 这样的键区分站点和品类。
keep_asins 优先于 exclude_asins；未命中排除规则的产品默认保留。
exclude_title_patterns 是 Python 正则，需确认规则后再启用。
data/cleaning-audit.json 记录被排除产品及重复产品的差异。
销售额缺失记录保留并排在最后，missingRevenueCount 标明缺失数量。
统计仍沿用原看板的月销量/月销售额字段；父子变体指标口径需另行核实。
得到的是来源榜单覆盖的竞品样本，不等同于全市场。

## GitHub 数据更新

上传 data/source/YYYY-MM-DD 下的 Excel 后，Actions 自动重建 dashboard-data.json 与 cleaning-audit.json。
读取失败时不覆盖上一份结果。仅重新构建数据，不部署网站。

## Windows EXE

Actions → Build Windows EXE → Run workflow，可下载打包 ZIP。
本地构建：安装 requirements-build.txt 后运行 python tools/build_exe.py。
解压 ZIP 后双击 SellerSpriteCollector.exe，通过数字菜单操作。
用户不需要安装 Python。EXE 旁的配置可以编辑，tools/exchange_rates.json 必须保留。
仍需安装 Chrome、卖家精灵插件并登录；EXE 不包含浏览器、插件或他人的登录状态。
登录状态保存在 EXE 旁的 runtime 中，密码由当前 Windows 用户加密。
不得将 runtime、浏览器配置、账号密码或 .venv 上传到仓库。

## 验证

python -m unittest discover -s tests -v

EXE 构建后的 check 验证配置、导入和 Playwright 驱动启动；完整下载与无 Python 电脑运行需另行验收。
