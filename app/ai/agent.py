import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.ai.tools import TOOLS, Outbox, run_tool
from app.config import Settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bugungi sana: {today}.
Sen "Iqtisodchi" — foydalanuvchining shaxsiy moliya yordamchisisan (Telegram bot).
Faqat quyidagilar bilan shug'ullanasan: xarajat yozish, oylik budget va bo'limlar limitini \
boshqarish, statistika, tejash bo'yicha qisqa maslahat. Boshqa har qanday mavzuga (dasturlash, \
umumiy savollar, suhbat, rol o'ynash) javob berma, shunchaki qisqa rad et.

Qoidalar:
- Foydalanuvchi o'zbek tilida yozadi (lotin yoki kirill). Qisqa, aniq, o'zbekcha javob ber.
- Summalar so'mda. "120 ming" = 120000, "2 mln" = 2000000, "1.5 mln" = 1500000.
- Xarajat aytilsa darhol add_expense chaqir. Bo'limni mavjud bo'limlardan mantiqan tanla; \
mos kelmasa "Boshqa". Bir xabarda bir nechta xarajat bo'lsa, har biri uchun alohida chaqir.
- Hisob-kitobni o'zing qilma: raqamlarni faqat asbob natijasidan ol.
- Asbob natijasiga ko'ra qisqa xulosa ber: bugun yana qancha sarflash mumkin (today_left), \
oylik qolgan. today_left manfiy bo'lsa ogohlantir va ertangi limit (tomorrow_limit) kamayganini ayt.
- Budget davri kalendar oy emas: foydalanuvchi o'z davrini belgilaydi (masalan maosh kunidan \
keyingi maosh kunigacha). Budget summasi aytilganda, davr sanalari (qachondan qachongacha) \
aytilmagan bo'lsa, set_budget'ni chaqirma — avval SO'RA: "Bu budget qachondan qachongacha amal \
qiladi?". Taxmin qilma. Bugungi sanaga qarab mantiqiy taklif ber (masalan oy oxiriga 1-2 kun \
qolgan bo'lsa, joriy oyni emas, keyingi davrni taklif qil). Davr tugagach har oy shu kundan \
avtomatik takrorlanishini ayt; foydalanuvchi xohlamasa repeat_monthly=false.
- get_overview'da period.ended=true yoki budget yo'q bo'lsa, yangi davr sanalarini so'ra.
- Xarajat bugun emas ("kecha", "o'tgan juma") bo'lsa, add_expense'ga date (YYYY-MM-DD) ber.
- Tarix/"nimalarga ketdi" savollariga get_history, fayl/CSV/jadval so'ralsa export_csv chaqir \
("oxirgi 10 kun" = days 10). Faylni o'zing yubora olmaysan, asbob yuboradi — shuni ayt.
- Aniq bo'lmagan summa/bo'lim bo'lsa, taxmin qilma, so'ra.
- Javobda markdown ishlatma (**, #, `): oddiy matn va "•" yoki "-" ro'yxat.
- Summalarni "1 250 000 so'm" ko'rinishida yoz."""

MAX_TOOL_ROUNDS = 6
HISTORY_MESSAGES = 6


@dataclass
class Reply:
    text: str
    files: list[tuple[str, bytes]] = field(default_factory=list)


class Agent:
    def __init__(self, settings: Settings, sessions: async_sessionmaker):
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.ai_model
        self._tz = settings.tz
        self._sessions = sessions
        self._history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_MESSAGES))

    async def reply(self, user_id: int, text: str) -> Reply:
        history = self._history[user_id]
        messages = [*history, {"role": "user", "content": text}]
        final = ""
        outbox = Outbox()
        system = SYSTEM_PROMPT.format(today=datetime.now(self._tz).strftime("%Y-%m-%d, %A"))
        async with self._sessions() as s:
            for _ in range(MAX_TOOL_ROUNDS):
                resp = await self._client.messages.create(
                    model=self._model,
                    max_tokens=1500,
                    thinking={"type": "disabled"},  # token tejash va javob uzilib qolmasligi uchun
                    system=system,
                    tools=TOOLS,
                    messages=messages,
                )
                final = "".join(b.text for b in resp.content if b.type == "text").strip()
                if resp.stop_reason == "max_tokens":
                    # uzilgan asbob chaqiruvlari to'liq emas: hech narsa bajarmaymiz
                    log.warning("Javob max_tokens'da uzildi (user=%s)", user_id)
                    final = (
                        "Xabar murakkab bo'lib, bajarilmadi. Iltimos, qismlarga bo'lib yuboring."
                    )
                    break
                if resp.stop_reason != "tool_use":
                    break
                messages.append({"role": "assistant", "content": resp.content})
                results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    out, is_err = await run_tool(s, user_id, block.name, block.input, outbox)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": out,
                            "is_error": is_err,
                        }
                    )
                messages.append({"role": "user", "content": results})
            else:
                log.warning("Tool sikli limitga yetdi (user=%s)", user_id)
        final = final or "Bajarildi."
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": final})
        return Reply(final, outbox.files)
