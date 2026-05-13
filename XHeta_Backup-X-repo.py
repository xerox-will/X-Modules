# scop: kernel min v1.3.0
# scop: inline
# requires: aiohttp
# -- end --

from __future__ import annotations

import re
import html as html_lib
import aiohttp
from typing import Any, Dict, List, Optional

from telethon import events

from core.lib.loader.module_base import ModuleBase, command, callback


REPO_OWNER = "xerox-will"
REPO_NAME = "X-Modules"
GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents"
GITHUB_RAW = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main"
FILE_SUFFIX = "-X-repo.py"
PER_PAGE = 5


class XHeta(ModuleBase):
    name = "XHeta"
    version = "1.2.0"
    author = "@x_modules"
    description = {
        "ru": "Поиск и установка модулей из репозитория X-Modules",
        "en": "Search and install modules from X-Modules repository",
    }

    strings = {
        "ru": {
            "searching": "🔍 <b>Ищу модули...</b>",
            "not_found": "❌ <b>Ничего не найдено по запросу:</b> <code>{query}</code>",
            "usage": "❌ <b>Использование:</b> <code>.xheta &lt;название или описание&gt;</code>",
            "error": "⚠️ <b>Ошибка при загрузке репозитория</b>",
            "installing": "⏳ <b>Устанавливаю модуль...</b>",
            "install_ok": "✅ Модуль {name} установлен и загружен!",
            "install_fail": "❌ Ошибка установки: {error}",
            "list_title": "📋 <b>Все найденные модули:</b>",
        },
        "en": {
            "searching": "🔍 <b>Searching modules...</b>",
            "not_found": "❌ <b>Nothing found for:</b> <code>{query}</code>",
            "usage": "❌ <b>Usage:</b> <code>.xheta &lt;name or description&gt;</code>",
            "error": "⚠️ <b>Error loading repository</b>",
            "installing": "⏳ <b>Installing module...</b>",
            "install_ok": "✅ Module {name} installed and loaded!",
            "install_fail": "❌ Installation error: {error}",
            "list_title": "📋 <b>All found modules:</b>",
        },
    }

    async def on_load(self) -> None:
        await super().on_load()
        self._modules_cache: List[Dict[str, Any]] = []
        self._session: Optional[aiohttp.ClientSession] = None

    async def on_unload(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _fetch_repo_modules(self) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            async with session.get(GITHUB_API, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                files = await resp.json()
        except Exception:
            return []

        modules = []
        for f in files:
            name = f.get("name", "")
            if not name.endswith(FILE_SUFFIX):
                continue

            module_name = name.replace(FILE_SUFFIX, "")
            download_url = f.get("download_url", f"{GITHUB_RAW}/{name}")

            meta = await self._parse_module_meta(session, download_url)
            meta["file_name"] = name
            meta["module_name"] = module_name
            meta["download_url"] = download_url
            if not meta.get("name"):
                meta["name"] = module_name
            modules.append(meta)

        self._modules_cache = modules
        return modules

    async def _parse_module_meta(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return {}
                code = await resp.text()
        except Exception:
            return {}

        meta: Dict[str, Any] = {}

        name_m = re.search(r'name\s*=\s*["\'](.+?)["\']', code)
        version_m = re.search(r'version\s*=\s*["\'](.+?)["\']', code)
        author_m = re.search(r'author\s*=\s*["\'](.+?)["\']', code)

        if name_m:
            meta["name"] = name_m.group(1)
        if version_m:
            meta["version"] = version_m.group(1)
        if author_m:
            meta["author"] = author_m.group(1)

        desc_match = re.search(r'"ru"\s*:\s*"(.+?)"', code)
        if not desc_match:
            desc_match = re.search(r'"en"\s*:\s*"(.+?)"', code)
        meta["description"] = desc_match.group(1) if desc_match else ""

        commands = re.findall(r'@command\(\s*"(\w+)"', code)
        meta["commands"] = commands

        return meta

    def _search(self, modules: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        results = []
        for m in modules:
            searchable = " ".join([
                m.get("name", ""),
                m.get("module_name", ""),
                m.get("description", ""),
                m.get("author", ""),
                " ".join(m.get("commands", [])),
            ]).lower()
            if q in searchable:
                results.append(m)
        return results

    def _format_module(self, m: Dict[str, Any], index: int, total: int) -> str:
        name = html_lib.escape(m.get("name", "Unknown"))
        author = html_lib.escape(m.get("author", "@x_modules"))
        version = html_lib.escape(m.get("version", "?.?.?"))
        desc = html_lib.escape(m.get("description", "Нет описания"))
        commands = m.get("commands", [])

        text = f"📦 <b>{name}</b> by <code>{author}</code>"
        if version != "?.?.?":
            text += f" (v{version})"

        text += f"\n\n📝 <b>Описание:</b>\n{desc}"

        if commands:
            cmds_str = ", ".join(f"<code>.{html_lib.escape(c)}</code>" for c in commands[:10])
            if len(commands) > 10:
                cmds_str += f" ...и ещё {len(commands) - 10}"
            text += f"\n\n⚙️ <b>Команды:</b> {cmds_str}"

        text += f"\n\n🔢 <b>{index + 1}/{total}</b>"

        return text

    def _build_buttons(self, index: int, modules: List[Dict[str, Any]], query: str) -> list:
        total = len(modules)
        m = modules[index]
        buttons = []

        # Row 1: Install + Code link
        row1 = [
            self.Button.inline(
                "📥 Установить",
                self._cb_install,
                args=(m.get("download_url", ""), m.get("module_name", "module")),
            ),
            self.Button.url("📄 Код", m.get("download_url", "")),
        ]
        buttons.append(row1)

        # Row 2: Navigation
        if total > 1:
            nav_row = []
            if index > 0:
                nav_row.append(
                    self.Button.inline("⬅️", self._cb_navigate, args=(index - 1, query))
                )
            nav_row.append(
                self.Button.inline(f"📋 {index + 1}/{total}", self._cb_show_list, args=(0, index, query))
            )
            if index < total - 1:
                nav_row.append(
                    self.Button.inline("➡️", self._cb_navigate, args=(index + 1, query))
                )
            buttons.append(nav_row)

        return buttons

    def _build_list_buttons(self, page: int, current_index: int, modules: List[Dict[str, Any]], query: str) -> list:
        buttons = []
        start = page * PER_PAGE
        end = min(start + PER_PAGE, len(modules))

        for i in range(start, end):
            name = modules[i].get("name", "Unknown")
            buttons.append([
                self.Button.inline(f"{i + 1}. {name}", self._cb_navigate, args=(i, query))
            ])

        nav = []
        total_pages = (len(modules) + PER_PAGE - 1) // PER_PAGE
        if page > 0:
            nav.append(self.Button.inline("⬅️", self._cb_show_list, args=(page - 1, current_index, query)))
        nav.append(self.Button.inline(f"📄 {page + 1}/{total_pages}", self._cb_noop, args=()))
        if page < total_pages - 1:
            nav.append(self.Button.inline("➡️", self._cb_show_list, args=(page + 1, current_index, query)))
        buttons.append(nav)

        buttons.append([
            self.Button.inline("↩️ Назад", self._cb_navigate, args=(current_index, query))
        ])

        return buttons

    # ── Callbacks ──

    @callback(ttl=900)
    async def _cb_noop(self, call: events.CallbackQuery.Event) -> None:
        await call.answer()

    @callback(ttl=900)
    async def _cb_navigate(self, call: events.CallbackQuery.Event, index: int, query: str) -> None:
        modules = self._search(self._modules_cache, query) if query else self._modules_cache
        if not modules or index >= len(modules):
            await call.answer("Модуль не найден", alert=True)
            return
        text = self._format_module(modules[index], index, len(modules))
        buttons = self._build_buttons(index, modules, query)
        try:
            await call.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            pass

    @callback(ttl=900)
    async def _cb_show_list(self, call: events.CallbackQuery.Event, page: int, current_index: int, query: str) -> None:
        modules = self._search(self._modules_cache, query) if query else self._modules_cache
        if not modules:
            await call.answer("Список пуст", alert=True)
            return
        text = self.strings["list_title"]
        buttons = self._build_list_buttons(page, current_index, modules, query)
        try:
            await call.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            pass

    @callback(ttl=900)
    async def _cb_install(self, call: events.CallbackQuery.Event, url: str, module_name: str) -> None:
        """Download module and load it via kernel.install_from_url (auto-reload)."""
        try:
            await call.answer(self.strings["installing"], alert=False)
            success, msg = await self.kernel.install_from_url(url, module_name)
            if success:
                await call.answer(
                    self.strings["install_ok"].format(name=module_name),
                    alert=True,
                )
            else:
                await call.answer(
                    self.strings["install_fail"].format(error=msg[:150]),
                    alert=True,
                )
        except Exception as e:
            await call.answer(
                self.strings["install_fail"].format(error=str(e)[:150]),
                alert=True,
            )

    # ── Main command ──

    @command("xheta", doc_ru="<запрос> поиск модулей в X-Modules", doc_en="<query> search modules in X-Modules")
    async def cmd_xheta(self, event: events.NewMessage.Event) -> None:
        args = event.text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(self.strings["usage"], parse_mode="html")
            return

        query = args[1].strip()
        await event.edit(self.strings["searching"], parse_mode="html")

        # Fetch modules from repo
        all_modules = await self._fetch_repo_modules()
        if not all_modules:
            await event.edit(self.strings["error"], parse_mode="html")
            return

        # Search
        results = self._search(all_modules, query)
        if not results:
            await event.edit(
                self.strings["not_found"].format(query=html_lib.escape(query)),
                parse_mode="html",
            )
            return

        # Show first result via self.inline
        text = self._format_module(results[0], 0, len(results))
        buttons = self._build_buttons(0, results, query)

        try:
            await self.inline(
                event.chat_id,
                text,
                buttons=buttons,
                ttl=900,
                parse_mode="html",
            )
            await event.delete()
        except Exception:
            await event.edit(text, buttons=buttons, parse_mode="html")
