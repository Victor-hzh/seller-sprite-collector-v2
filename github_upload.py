"""Upload downloaded Excel files as one GitHub commit without browser automation."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app_paths import BASE_DIR

REPOSITORY = "Victor-hzh/seller-sprite-collector-v2"
BRANCH = "main"
TOKEN_FILE = BASE_DIR / "runtime" / "github_token.dpapi"
DECRYPT_SCRIPT = BASE_DIR / "decrypt_login_password.ps1"


class UploadError(RuntimeError):
    pass


def saved_token_exists() -> bool:
    return TOKEN_FILE.is_file() and TOKEN_FILE.stat().st_size > 0


def read_saved_token() -> str:
    if not saved_token_exists():
        raise UploadError("请先点击“连接 GitHub”，保存有仓库写入权限的访问令牌。")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(DECRYPT_SCRIPT), "-PasswordFile", str(TOKEN_FILE.resolve())],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"},
    )
    if result.returncode or not result.stdout.strip():
        raise UploadError("无法读取本机保存的 GitHub 令牌，请在“连接 GitHub”中重新保存。")
    return result.stdout.strip()


def excel_files(folder: Path, task_id: str | None = None) -> list[Path]:
    """Only upload Excel files from one dated source folder, never runtime data."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", folder.name) or not folder.is_dir():
        raise UploadError("请选择 data/source 下含 Excel 的日期文件夹。")
    if task_id is None:
        files = sorted(path for path in folder.glob("*.xlsx") if path.is_file())
    else:
        manifest = folder / "run_manifest.json"
        if not manifest.is_file():
            raise UploadError("缺少当日下载清单，无法确认所选榜单的 Excel。")
        records = json.loads(manifest.read_text(encoding="utf-8"))["tasks"]
        matching = [record for record in records if record.get("id") == task_id and record.get("status") == "completed"]
        if len(matching) != 1:
            raise UploadError("所选榜单尚未成功下载，不能上传其他 Excel。")
        raw_path = matching[0]["download_file"].replace("\\", "/")
        path = (BASE_DIR / raw_path).resolve()
        if path.parent != folder.resolve() or path.suffix.lower() != ".xlsx" or not path.is_file():
            raise UploadError("下载清单中的 Excel 路径无效。")
        files = [path]
    if not files:
        raise UploadError("所选日期文件夹里没有可上传的 Excel。")
    return files


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


class GitHubClient:
    def __init__(self, token: str):
        if not token.strip():
            raise UploadError("GitHub 令牌为空。")
        self.token = token.strip()

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            "https://api.github.com" + path,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "SellerSpriteCollector-v2",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=90) as response:
                    return json.load(response)
            except HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                if exc.code in (401, 403):
                    raise UploadError("GitHub 拒绝访问。请确认令牌未过期，并拥有该仓库 Contents 读写权限。") from exc
                raise UploadError(f"GitHub API 返回 HTTP {exc.code}；请检查仓库权限和网络后重试。") from exc
            except (URLError, TimeoutError) as exc:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise UploadError(f"无法连接 GitHub：{exc}") from exc
        raise UploadError("GitHub 请求重试后仍失败。")


def upload_excel_files(files: list[Path], folder: Path, client: GitHubClient) -> tuple[int, str | None]:
    """Commit only changed Excel blobs; retry a non-force ref update if main advances."""
    if not files:
        raise UploadError("没有可上传的 Excel。")
    folder = folder.resolve()
    paths: dict[str, bytes] = {}
    for file in files:
        path = file.resolve()
        if path.parent != folder or path.suffix.lower() != ".xlsx":
            raise UploadError("只能上传所选日期文件夹中的 Excel。")
        paths[f"data/source/{folder.name}/{path.name}"] = path.read_bytes()
    prefix = f"/repos/{REPOSITORY}"
    uploaded_blobs: dict[str, str] = {}
    for retry in range(3):
        head = client.request("GET", f"{prefix}/git/ref/heads/{BRANCH}")["object"]["sha"]
        base_tree = client.request("GET", f"{prefix}/git/commits/{head}")["tree"]["sha"]
        tree = client.request("GET", f"{prefix}/git/trees/{base_tree}?recursive=1")
        if tree.get("truncated"):
            raise UploadError("仓库文件树过大，无法安全判断重复 Excel；请联系维护者。")
        existing = {entry["path"]: entry["sha"] for entry in tree["tree"] if entry["type"] == "blob"}
        changed = {path: content for path, content in paths.items() if existing.get(path) != git_blob_sha(content)}
        if not changed:
            return 0, None
        for path, content in changed.items():
            if path not in uploaded_blobs:
                response = client.request("POST", f"{prefix}/git/blobs", {
                    "content": base64.b64encode(content).decode("ascii"), "encoding": "base64",
                })
                uploaded_blobs[path] = response["sha"]
        new_tree = client.request("POST", f"{prefix}/git/trees", {
            "base_tree": base_tree,
            "tree": [{"path": path, "mode": "100644", "type": "blob", "sha": uploaded_blobs[path]}
                     for path in changed],
        })["sha"]
        commit = client.request("POST", f"{prefix}/git/commits", {
            "message": f"Upload SellerSprite Excel data for {folder.name} ({len(changed)} files)",
            "tree": new_tree,
            "parents": [head],
        })["sha"]
        try:
            client.request("PATCH", f"{prefix}/git/refs/heads/{BRANCH}", {"sha": commit, "force": False})
            return len(changed), f"https://github.com/{REPOSITORY}/commit/{quote(commit)}"
        except UploadError as exc:
            if retry == 2 or "HTTP 409" not in str(exc) and "HTTP 422" not in str(exc):
                raise
    raise UploadError("仓库主分支在上传时持续变化，请稍后重试。")
