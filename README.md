# iqtisodchi-bot

Shaxsiy kirim-chiqim Telegram boti. Tugmasiz, oddiy matn bilan ishlaydi:
"120 ming so'mlik non, sut va go'sht oldim" → AI tahlil qiladi → PostgreSQL yangilanadi.

## Stack
aiogram 3 · PostgreSQL 16 + pgvector · Docker Compose · Claude API · RAG · rate limiting

## Reja (skelet)
```
app/
  bot/handlers/      matnli xabar handlerlari
  bot/middlewares/   whitelist (ALLOWED_USER_IDS), rate limit
  db/models, repositories/   SQLAlchemy modellar va so'rovlar
  services/          kirim/chiqim, kunlik limit logikasi
  ai/                xabarni tranzaksiyaga aylantirish (structured output)
  rag/               out-of-topic himoya, knowledge/ dan qidiruv
knowledge/           RAG hujjatlari
migrations/          Alembic
```

## Xavfsizlik
- Polling (webhook yo'q) — tashqaridan hech qanday port ochilmaydi
- Postgres faqat `127.0.0.1` da
- Faqat `ALLOWED_USER_IDS` dagi foydalanuvchilar; boshqalar jim tashlanadi
- Rate limit + konteynerlarga CPU/RAM limit (noutbukni himoya qilish)
- Bot konteyneri: non-root, read-only FS, `cap_drop: ALL`

## Ishga tushirish
```
cp .env.example .env   # to'ldiring
make venv              # lokal rivojlantirish uchun
make up                # docker compose
```
