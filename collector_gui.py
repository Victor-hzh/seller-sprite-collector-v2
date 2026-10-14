"""Click-first Windows interface for the existing SellerSprite collector."""
from __future__ import annotations

import contextlib
import json
import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from tkinter import BooleanVar, Canvas, StringVar, Tk, Toplevel, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import collector_app
from app_paths import BASE_DIR

REPOSITORY = "Victor-hzh/seller-sprite-collector-v2"
SOURCE_ROOT = BASE_DIR / "data" / "source"
LOG_PATH = BASE_DIR / "runtime" / "collector.log"
REGIONS = {"美国站": "US", "英国站": "UK", "德国站": "DE", "法国站": "FR", "意大利站": "IT", "西班牙站": "ES", "日本站": "JP"}
CATEGORIES = ("洗地机", "吸尘器", "扫地机器人", "除螨仪", "布艺清洗机")


def build_change_request_prompt(region: str, category: str, urls: str, description: str) -> str:
    """Turn a user's four-field report into a reviewable change request."""
    if region not in REGIONS or category not in CATEGORIES:
        raise ValueError("请选择地区和品类。")
    links = [line.strip() for line in urls.splitlines() if line.strip()]
    if not links or any(urlparse(link).scheme not in ("http", "https") or not urlparse(link).netloc for link in links):
        raise ValueError("请每行填写一个完整的榜单网址，以 https:// 开头。")
    if not description.strip():
        raise ValueError("请填写当前问题和希望得到的结果。")
    formatted_links = "\n".join(f"- {link}" for link in links)
    return (
        "请协助修改 GitHub 仓库 Victor-hzh/seller-sprite-collector-v2 中的卖家精灵榜单采集与看板数据流程。"
        "这是独立的 V2 项目，请先阅读现有下载任务、清洗规则、GitHub Actions 和看板数据结构，"
        "不要修改原版 seller-sprite-dashboard-data 仓库。\n\n"
        f"地区：{region}（{REGIONS[region]}）\n品类：{category}\n榜单网址：\n{formatted_links}\n"
        f"现状与需求：{description.strip()}\n\n"
        "请核对这些网址对应的榜单节点及现有任务，判断需要新增下载来源、替换链接、合并榜单还是调整清洗规则，"
        "并说明判断依据。按需求修改本地下载配置及仓库代码，使每次运行和上传新 Excel 后都由代码自动完成处理；"
        "保留原始 Excel 于 data/source，清洗结果写入 data/processed，网站只读取清洗结果。"
        "同一 ASIN 跨榜单出现时去重，不重复累加同一产品销售额；需要排除非竞品时把规则写入代码并保留审计记录。"
        "请运行相关测试，核对下载来源数量、合并后的覆盖情况和看板指标；"
        "若真实下载或网页验证无法完成，请明确指出尚待人工验证的部分。"
    )


def chrome_path() -> Path | None:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    return next((path for path in candidates if path.is_file()), None)


def enabled_tasks() -> list[dict]:
    payload = json.loads((BASE_DIR / "tasks_v2.json").read_text(encoding="utf-8"))
    return [task for task in payload["tasks"] if task.get("enabled", True)]


class QueueWriter:
    def __init__(self, events: queue.Queue):
        self.events = events

    def write(self, value: str) -> int:
        if value:
            self.events.put(("text", value))
        return len(value)

    def flush(self) -> None:
        pass


class CollectorWindow:
    def __init__(self, root: Tk):
        self.root = root
        self.events: queue.Queue = queue.Queue()
        self.busy = False
        self.buttons: list[ttk.Button] = []
        self.status = StringVar(value="就绪 · 先检查环境，再初始化浏览器与插件")
        self.summary = StringVar(value="正在读取任务配置…")
        self.force = BooleanVar(value=False)
        self.task_label = StringVar(value="全部榜单")
        self.task_by_label: dict[str, str | None] = {"全部榜单": None}

        root.title("卖家精灵数据采集 · V2")
        root.geometry("980x830")
        root.minsize(790, 650)
        root.configure(bg="#f5f6f8")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_style()
        self._build_layout()
        self._refresh_summary()
        root.after(100, self._drain_events)

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f6f8")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f5f6f8", foreground="#24313d", font=("Microsoft YaHei UI", 10))
        style.configure("Card.TLabel", background="#ffffff", foreground="#24313d", font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", background="#f5f6f8", foreground="#172331", font=("Microsoft YaHei UI", 19, "bold"))
        style.configure("Section.TLabel", background="#ffffff", foreground="#172331", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(14, 9))
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 11, "bold"), padding=(18, 11), background="#e65b11", foreground="white")
        style.map("Primary.TButton", background=[("active", "#c74c0a"), ("disabled", "#d3d7da")])

    def _button(self, parent, text: str, command, primary: bool = False) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command, style="Primary.TButton" if primary else "TButton")
        self.buttons.append(button)
        return button

    def _card(self, parent, title: str, detail: str) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.pack(fill="x", pady=(0, 12))
        ttk.Label(card, text=title, style="Section.TLabel").pack(anchor="w")
        ttk.Label(card, text=detail, style="Card.TLabel", wraplength=840).pack(anchor="w", pady=(5, 12))
        return card

    def _build_layout(self) -> None:
        canvas = Canvas(self.root, background="#f5f6f8", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        shell = ttk.Frame(canvas, padding=20)
        window = canvas.create_window((0, 0), window=shell, anchor="nw")
        shell.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        ttk.Label(shell, text="卖家精灵榜单采集", style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell, textvariable=self.summary).pack(anchor="w", pady=(3, 14))

        setup = self._card(shell, "1  本地环境", "首次安装后按引导检查配置并安装 Chrome、卖家精灵插件。团队账号已包含在程序中。")
        setup_actions = ttk.Frame(setup, style="Card.TFrame")
        setup_actions.pack(anchor="w")
        self._button(setup_actions, "本地环境配置与部署", self._setup_dialog, primary=True).pack(side="left", padx=(0, 8))
        self._button(setup_actions, "卖家精灵一键登录", self._login_clicked).pack(side="left")

        download = self._card(shell, "2  下载并更新", "选择全部或单个榜单。点击“下载并更新看板”后，程序会依次下载、上传 Excel 并提交 GitHub。")
        picker = ttk.Frame(download, style="Card.TFrame")
        picker.pack(fill="x")
        ttk.Label(picker, text="下载范围", style="Card.TLabel").pack(side="left", padx=(0, 8))
        self.task_box = ttk.Combobox(picker, textvariable=self.task_label, state="readonly", width=52)
        self.task_box.pack(side="left", padx=(0, 14))
        ttk.Checkbutton(picker, text="重新下载已完成榜单", variable=self.force).pack(side="left")
        download_actions = ttk.Frame(download, style="Card.TFrame")
        download_actions.pack(anchor="w", pady=(14, 0))
        self._button(download_actions, "下载并更新看板", lambda: self._download(upload=True), primary=True).pack(side="left", padx=(0, 8))
        self._button(download_actions, "仅下载", lambda: self._download(upload=False)).pack(side="left")

        upload = self._card(shell, "3  GitHub 连接与上传", "首次使用先连接 GitHub。下载并更新会自动提交 Excel，触发仓库清洗；上传失败时可点击“重新上传已下载 Excel”。")
        upload_actions = ttk.Frame(upload, style="Card.TFrame")
        upload_actions.pack(anchor="w")
        self._button(upload_actions, "连接 GitHub", self._github_token_dialog).pack(side="left", padx=(0, 8))
        self._button(upload_actions, "重新上传已下载 Excel", self._upload_auto, primary=True).pack(side="left", padx=(0, 8))
        self._button(upload_actions, "手动上传页面（备用）", lambda: self._run_command("upload")).pack(side="left")
        upload_tools = ttk.Frame(upload, style="Card.TFrame")
        upload_tools.pack(anchor="w", pady=(8, 0))
        self._button(upload_tools, "打开数据文件夹", self._open_source_folder).pack(side="left", padx=(0, 8))
        self._button(upload_tools, "本地清洗预览（可选）", lambda: self._run_command("clean")).pack(side="left")

        prompt = self._card(shell, "4  提交新的榜单需求", "选择地区和品类，粘贴榜单网址并描述现状，生成可复制的完整修改提示词。")
        self._button(prompt, "填写需求并生成提示词", self._prompt_dialog, primary=True).pack(anchor="w")

        log_header = ttk.Frame(shell)
        log_header.pack(fill="x", pady=(2, 5))
        ttk.Label(log_header, text="运行记录").pack(side="left")
        self._button(log_header, "打开完整日志", self._open_log).pack(side="right")
        self.log = ScrolledText(shell, height=9, wrap="word", state="disabled", font=("Consolas", 9), background="#172331", foreground="#e7edf2")
        self.log.pack(fill="x")
        ttk.Label(shell, textvariable=self.status).pack(anchor="w", pady=(8, 0))

    def _setup_dialog(self) -> None:
        dialog = Toplevel(self.root)
        dialog.title("本地环境配置与部署")
        dialog.geometry("650x515")
        dialog.transient(self.root)
        body = ttk.Frame(dialog, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="首次使用向导", style="Title.TLabel").pack(anchor="w", pady=(0, 12))
        ttk.Label(body, text="程序已包含 Python、依赖和团队登录账号，无需设置环境变量。先检查，再安装 Chrome、初始化插件；验证码仍需本人完成。", wraplength=560).pack(anchor="w", pady=(0, 18))
        self._button(body, "1  检查配置与驱动", lambda: self._run_command("check")).pack(anchor="w", pady=4)
        self._button(body, "2  获取 Chrome（若尚未安装）", lambda: webbrowser.open("https://www.google.com/chrome/")).pack(anchor="w", pady=4)
        self._button(body, "3  打开专用浏览器，安装卖家精灵插件", lambda: self._run_command("inspect")).pack(anchor="w", pady=4)
        self._button(body, "4  使用团队账号一键登录", self._login_clicked).pack(anchor="w", pady=4)
        self._button(body, "5  改用本机账号（可选）", self._credential_dialog).pack(anchor="w", pady=4)
        self._button(body, "6  连接 GitHub 自动上传", self._github_token_dialog).pack(anchor="w", pady=4)
        ttk.Label(body, text="程序会自动填写并提交团队账号；插件首次安装及可能出现的验证码需要人工操作。", wraplength=560).pack(anchor="w", pady=(16, 0))

    def _prompt_dialog(self) -> None:
        dialog = Toplevel(self.root)
        dialog.title("生成榜单修改提示词")
        dialog.geometry("780x700")
        dialog.minsize(650, 600)
        dialog.transient(self.root)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="榜单需求", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(body, text="地区").grid(row=1, column=0, sticky="nw", pady=6)
        region = ttk.Combobox(body, state="readonly", values=list(REGIONS), width=24)
        region.grid(row=1, column=1, sticky="w", pady=6)
        ttk.Label(body, text="品类").grid(row=2, column=0, sticky="nw", pady=6)
        category = ttk.Combobox(body, state="readonly", values=CATEGORIES, width=24)
        category.grid(row=2, column=1, sticky="w", pady=6)
        ttk.Label(body, text="榜单网址\n每行一个").grid(row=3, column=0, sticky="nw", pady=6)
        urls = ScrolledText(body, height=4, wrap="word")
        urls.grid(row=3, column=1, sticky="nsew", pady=6)
        ttk.Label(body, text="现状描述").grid(row=4, column=0, sticky="nw", pady=6)
        description = ScrolledText(body, height=5, wrap="word")
        description.grid(row=4, column=1, sticky="nsew", pady=6)
        ttk.Label(body, text="生成的提示词").grid(row=6, column=0, sticky="nw", pady=(14, 6))
        output = ScrolledText(body, height=12, wrap="word")
        output.grid(row=6, column=1, sticky="nsew", pady=(14, 6))

        def generate() -> None:
            try:
                result = build_change_request_prompt(region.get(), category.get(), urls.get("1.0", "end"), description.get("1.0", "end"))
            except ValueError as exc:
                messagebox.showerror("请补充信息", str(exc), parent=dialog)
                return
            output.delete("1.0", "end")
            output.insert("1.0", result)

        def copy() -> None:
            value = output.get("1.0", "end").strip()
            if not value:
                messagebox.showinfo("提示词为空", "先点击“生成提示词”。", parent=dialog)
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.root.update_idletasks()
            messagebox.showinfo("已复制", "提示词已复制，可粘贴到新对话中。", parent=dialog)

        actions = ttk.Frame(body)
        actions.grid(row=5, column=1, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="生成提示词", command=generate, style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="复制提示词", command=copy).pack(side="left")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(6, weight=1)

    def _refresh_summary(self) -> None:
        try:
            tasks = enabled_tasks()
            self.task_by_label = {"全部榜单": None}
            for task in tasks:
                label = f"{task['marketplace']} · {task.get('category_label', task['category'])} · {task.get('node_id', '')} · {task['id']}"
                self.task_by_label[label] = task["id"]
            self.task_box["values"] = list(self.task_by_label)
            today = SOURCE_ROOT / datetime.now().strftime("%Y-%m-%d")
            count = len(list(today.glob("*.xlsx"))) if today.is_dir() else 0
            chrome = "Chrome 已安装" if chrome_path() else "未找到 Chrome"
            self.summary.set(f"{len(tasks)} 个下载来源 · 今天已有 {count} 份 Excel · {chrome} · 数据保存在 {SOURCE_ROOT}")
        except Exception as exc:
            self.summary.set(f"配置读取失败：{exc}")

    def _append_log(self, value: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", value)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain_events(self) -> None:
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "text":
                self._append_log(value)
            elif kind == "inspect_confirm":
                messagebox.showinfo("浏览器初始化", "请在刚打开的 Chrome 中确认卖家精灵插件已安装并登录。\n完成后点击“确定”，程序会保存诊断截图并关闭本次浏览器。", parent=self.root)
                value.set()
            elif kind == "login_confirm":
                messagebox.showinfo("完成登录验证", "请在 Chrome 中完成卖家精灵要求的验证码或其他验证，完成后点击“确定”。", parent=self.root)
                value.set()
            elif kind == "done":
                self.busy = False
                self.buttons = [button for button in self.buttons if button.winfo_exists()]
                for button in self.buttons:
                    button.configure(state="normal")
                self.status.set("完成" if value == 0 else f"运行失败（代码 {value}），请查看上方记录")
                self._refresh_summary()
            elif kind == "after_success":
                self.root.after(0, value)
        self.root.after(100, self._drain_events)

    def _wait_for_inspect(self) -> None:
        signal = threading.Event()
        self.events.put(("inspect_confirm", signal))
        signal.wait()

    def _wait_for_login(self) -> None:
        signal = threading.Event()
        self.events.put(("login_confirm", signal))
        signal.wait()

    def _run_worker(self, title: str, action, after_success=None) -> None:
        if self.busy:
            messagebox.showinfo("请稍候", "当前任务仍在运行，请等待完成。", parent=self.root)
            return
        self.busy = True
        self.buttons = [button for button in self.buttons if button.winfo_exists()]
        for button in self.buttons:
            button.configure(state="disabled")
        self.status.set(f"运行中：{title}")
        self._append_log(f"\n[{datetime.now():%H:%M:%S}] {title}\n")

        def work() -> None:
            writer = QueueWriter(self.events)
            code = 1
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                try:
                    code = action()
                except Exception:
                    traceback.print_exc()
            self.events.put(("done", code))
            if code == 0 and after_success is not None:
                self.events.put(("after_success", after_success))

        threading.Thread(target=work, name="seller-sprite-task", daemon=True).start()

    def _run_command(self, command: str, extra: list[str] | None = None) -> None:
        def action() -> int:
            if command == "check":
                print(f"Chrome：{chrome_path() or '未找到，请先安装 Google Chrome'}")
                print(f"数据目录：{SOURCE_ROOT}")
            wait_for_user = self._wait_for_inspect if command == "inspect" else self._wait_for_login if command in ("login", "run", "run-upload") else None
            return collector_app.main([command, *(extra or [])], wait_for_user=wait_for_user)

        self._run_worker({"run": "下载榜单", "run-upload": "下载并更新看板", "inspect": "初始化浏览器和插件", "login": "卖家精灵一键登录", "clean": "本地清洗与合并", "upload": "打开上传页面", "upload-auto": "自动上传已下载 Excel", "check": "检查环境"}[command], action)

    def _login_clicked(self) -> None:
        if not chrome_path():
            messagebox.showerror("需要 Chrome", "请先在“本地环境配置与部署”中安装 Chrome。", parent=self.root)
            return
        self._run_command("login")

    def _download(self, *, upload: bool) -> None:
        if upload:
            from github_upload import saved_token_exists
            if not saved_token_exists():
                self._github_token_dialog(after_save=lambda: self._download(upload=True))
                return
        args: list[str] = []
        task_id = self.task_by_label.get(self.task_label.get())
        if task_id:
            args.extend(["--task", task_id])
        if self.force.get():
            args.append("--force")
        self._run_command("run-upload" if upload else "run", args)

    def _upload_auto(self) -> None:
        from github_upload import saved_token_exists
        if not saved_token_exists():
            self._github_token_dialog(after_save=self._upload_auto)
            return
        args: list[str] = []
        task_id = self.task_by_label.get(self.task_label.get())
        if task_id:
            args.extend(["--task", task_id])
        self._run_command("upload-auto", args)

    def _github_token_dialog(self, after_save=None) -> None:
        dialog = Toplevel(self.root)
        dialog.title("连接 GitHub 自动上传")
        dialog.geometry("690x290")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="首次使用：保存个人 GitHub 访问令牌", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text="令牌需能写入 Victor-hzh/seller-sprite-collector-v2 的 Contents。保存后只供当前 Windows 用户使用，不会上传到仓库。", wraplength=635).pack(anchor="w", pady=(9, 13))
        ttk.Button(body, text="打开 GitHub 令牌创建页面", command=lambda: webbrowser.open("https://github.com/settings/personal-access-tokens/new?name=SellerSprite+Collector+V2&target_name=Victor-hzh&contents=write")).pack(anchor="w", pady=(0, 14))
        row = ttk.Frame(body)
        row.pack(fill="x")
        ttk.Label(row, text="粘贴令牌").pack(side="left", padx=(0, 10))
        secret = ttk.Entry(row, show="●", width=57)
        secret.pack(side="left", fill="x", expand=True)
        secret.focus_set()

        def save() -> None:
            token = secret.get().strip()
            if not token or any(ch.isspace() for ch in token):
                messagebox.showerror("令牌无效", "请粘贴完整的 GitHub 访问令牌。", parent=dialog)
                return
            secret.delete(0, "end")
            dialog.destroy()

            def action() -> int:
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(BASE_DIR / "save_github_token.ps1"), "-FromStdin"],
                    input=token + "\n", capture_output=True, text=True, encoding="utf-8", errors="replace",
                    env={key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"},
                )
                if result.returncode:
                    print("GitHub 令牌保存失败；请重试。")
                    return result.returncode
                from github_upload import GitHubClient, REPOSITORY, read_saved_token
                GitHubClient(read_saved_token()).request("GET", f"/repos/{REPOSITORY}")
                print("GitHub 连接成功。令牌已使用当前 Windows 用户加密保存在本机。")
                return 0

            self._run_worker("连接 GitHub", action, after_success=after_save)

        ttk.Button(body, text="保存并连接", command=save, style="Primary.TButton").pack(anchor="e", pady=(16, 0))
        dialog.bind("<Return>", lambda _event: save())

    def _credential_dialog(self, start_login_after_save: bool = False) -> None:
        dialog = Toplevel(self.root)
        dialog.title("保存卖家精灵账号")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="账号和密码只保存在本机，不上传到 GitHub。").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(body, text="账号").grid(row=1, column=0, sticky="w", pady=5)
        username = ttk.Entry(body, width=34)
        username.grid(row=1, column=1, pady=5)
        ttk.Label(body, text="密码").grid(row=2, column=0, sticky="w", pady=5)
        password = ttk.Entry(body, width=34, show="●")
        password.grid(row=2, column=1, pady=5)
        saved_user = BASE_DIR / "runtime" / "seller_sprite_username.txt"
        if saved_user.is_file():
            username.insert(0, saved_user.read_text(encoding="utf-8-sig").strip())
        username.focus_set()

        def save() -> None:
            user, secret = username.get().strip(), password.get()
            if not user or not secret or any(ch in user + secret for ch in "\r\n"):
                messagebox.showerror("输入不完整", "请输入账号和密码；不能包含换行。", parent=dialog)
                return
            password.delete(0, "end")
            dialog.destroy()

            def action() -> int:
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(BASE_DIR / "save_login_credentials.ps1"), "-FromStdin"],
                    input=f"{user}\n{secret}\n", capture_output=True, text=True, encoding="utf-8", errors="replace",
                    env={key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"},
                )
                if result.returncode:
                    print(result.stderr.strip() or "保存登录信息失败。")
                else:
                    print("卖家精灵账号已使用当前 Windows 用户加密保存在本机。")
                return result.returncode

            self._run_worker("保存登录信息", action, after_success=self._login_clicked if start_login_after_save else None)

        ttk.Button(body, text="加密保存", command=save, style="Primary.TButton").grid(row=3, column=1, sticky="e", pady=(14, 0))
        dialog.bind("<Return>", lambda _event: save())

    def _open_source_folder(self) -> None:
        SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
        os.startfile(str(SOURCE_ROOT))

    def _open_log(self) -> None:
        if LOG_PATH.is_file():
            os.startfile(str(LOG_PATH))
        else:
            messagebox.showinfo("运行日志", "尚无日志。下载任务开始后会自动生成。", parent=self.root)

    def _on_close(self) -> None:
        if self.busy and not messagebox.askyesno("任务正在运行", "关闭窗口会中断当前任务。确定关闭吗？", parent=self.root):
            return
        self.root.destroy()


def self_test() -> int:
    required = ["config_v2.json", "tasks_v2.json", "save_login_credentials.ps1", "save_github_token.ps1", "decrypt_login_password.ps1", "cleaning/cleaning_rules.json", "cleaning/exchange_rates.json"]
    missing = [name for name in required if not (BASE_DIR / name).is_file()]
    if missing:
        print("Missing installer files:", ", ".join(missing))
        return 1
    if not enabled_tasks():
        print("No enabled download tasks")
        return 1
    from shared_login import USERNAME, PASSWORD
    if not USERNAME or not PASSWORD:
        print("The team login is not configured")
        return 1
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        if playwright.chromium.name != "chromium":
            return 1
    print(f"Ready: {len(enabled_tasks())} download sources; Python is bundled.")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        return self_test()
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        return collector_app.main(sys.argv[2:])
    root = Tk()
    CollectorWindow(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
