卖家精灵榜单采集 V2 · Windows 使用说明

安装：双击 SellerSpriteCollector-v2-Setup.exe，按提示完成安装。桌面和开始菜单会出现“SellerSprite Collector V2”。程序已经包含 Python 与所需的程序库，不用安装 Python，也不用手动设置环境变量。
目标电脑：Windows 10/11 的 64 位系统。安装包在 GitHub 的 Windows 构建机生成；下载和安装请在目标电脑完成。Chrome 和卖家精灵插件需要使用者安装；团队账号已包含在程序中。

首次使用：
1. 打开程序，点击“本地环境配置与部署”，按弹窗顺序检查配置和浏览器驱动。如果没有 Chrome，点击获取 Chrome 并完成官方安装。
2. 点击向导中的“打开专用浏览器”，在打开的 Chrome 中安装卖家精灵插件；然后点击“卖家精灵一键登录”。需要验证码时由本人完成。插件和登录状态保存在本机 runtime/chrome-profile。
3. 点击“卖家精灵一键登录”。程序会使用内置团队账号自动填写并提交；以后也可直接点击此按钮。若卖家精灵弹出验证码，按浏览器提示完成。需要改用本机账号时，可在环境向导中保存，本机账号会优先使用。
4. 点击“连接 GitHub”，打开令牌创建页。令牌的资源所有者选 Victor-hzh，只选择 seller-sprite-collector-v2 仓库，并授予 Repository permissions → Contents → Read and write。粘贴令牌后点击“保存并连接”。每位同事需要自己的 GitHub 写入权限；令牌使用 Windows 当前用户加密保存，不会放入仓库或安装包。

每次采集：
1. 选择全部或单个榜单，点击“下载并更新看板”。程序先检查卖家精灵登录状态，必要时自动登录；然后下载 Excel，并将当天 Excel 自动提交到 GitHub。已完成任务会跳过，需要重跑时勾选“重新下载已完成榜单”。
2. 下载和上传成功后，无需打开 GitHub 上传页面，也无需拖拽或点击“Commit changes”。GitHub Actions 会自动清洗、合并并更新看板数据。等待仓库 Actions 的“Build cleaned dashboard data”显示成功后刷新看板。
3. 若下载完成但网络或权限导致上传失败，可点击“重新上传已下载 Excel”，无需重新下载。仓库已有相同 Excel 时程序不会重复提交。“仅下载”和“手动上传页面（备用）”保留供特殊情况使用。

“本地清洗预览”是可选操作，不是上传前必须步骤。团队登录信息随公开 V2 仓库源码和安装包分发；本机覆盖账号使用当前 Windows 用户加密，只保存在本机。程序的 runtime 文件夹包含登录状态与日志，不要上传到 GitHub。卸载软件时已下载的 Excel 和 runtime 文件夹会保留，避免误删工作数据。

新榜单需求：点击“填写需求并生成提示词”，选择地区和品类，逐行粘贴榜单网址，描述当前问题和期望结果。点击“生成提示词”后检查文本，再点击“复制提示词”，粘贴到新的协作对话中。这个功能只生成需求文本，不会自行修改采集规则或上传数据。

仓库：https://github.com/Victor-hzh/seller-sprite-collector-v2
看板：https://seller-sprite-dashboard-lab.jg749nmqt5.chatgpt.site/
