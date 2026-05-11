# scop: kernel min v1.3.0
# -- end --

from __future__ import annotations

from datetime import datetime

from telethon import events

from core.lib.loader.module_base import ModuleBase, command


class Time(ModuleBase):
    name = "Time"
    version = "1.0.2"
    author = "@x_modules"
    description = {
        "ru": "Показывает дату и время в указанном часовом поясе",
        "en": "Shows date and time in specified timezone",
    }

    strings = {
        "ru": {
            "usage": "❌ <b>Использование:</b> <code>.time Europe/Kiev</code>\n💡 <b>Примеры:</b> Europe/Kiev, America/New_York, Asia/Tokyo",
            "invalid_tz": "❌ <b>Неверный часовой пояс:</b> <code>{tz}</code>\n💡 <b>Примеры:</b> Europe/Kiev, America/New_York, Asia/Tokyo",
        },
        "en": {
            "usage": "❌ <b>Usage:</b> <code>.time Europe/Kiev</code>\n💡 <b>Examples:</b> Europe/Kiev, America/New_York, Asia/Tokyo",
            "invalid_tz": "❌ <b>Invalid timezone:</b> <code>{tz}</code>\n💡 <b>Examples:</b> Europe/Kiev, America/New_York, Asia/Tokyo",
        },
    }

    @command("time", doc_ru="<timezone> показать дату и время", doc_en="<timezone> show date and time")
    async def cmd_time(self, event: events.NewMessage.Event) -> None:
        args = event.text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(self.strings["usage"], parse_mode="html")
            return

        tz_name = args[1].strip()

        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            await event.edit(
                self.strings["invalid_tz"].format(tz=tz_name),
                parse_mode="html",
            )
            return

        now = datetime.now(tz)

        days_ru = {
            "Monday": "Понедельник",
            "Tuesday": "Вторник",
            "Wednesday": "Среда",
            "Thursday": "Четверг",
            "Friday": "Пятница",
            "Saturday": "Суббота",
            "Sunday": "Воскресенье",
        }

        months_ru = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
        }

        day_name = days_ru.get(now.strftime("%A"), now.strftime("%A"))
        month_name = months_ru.get(now.month, now.strftime("%B"))

        msg = (
            f"🕐 <b>Время:</b> <code>{now.strftime('%H:%M:%S')}</code>\n"
            f"📅 <b>Дата:</b> <code>{now.day} {month_name} {now.year}</code>\n"
            f"📆 <b>День:</b> <code>{day_name}</code>\n"
            f"🌍 <b>Часовой пояс:</b> <code>{tz_name}</code>\n"
            f"⏳ <b>UTC offset:</b> <code>{now.strftime('%z')}</code>"
        )

        await event.edit(msg, parse_mode="html")
