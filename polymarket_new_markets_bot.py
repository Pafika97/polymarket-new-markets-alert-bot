\
import asyncio
import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Set
import httpx
from dotenv import load_dotenv

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"

# Папка/файл для состояния
DATA_DIR = "data"
SEEN_FILE = os.path.join(DATA_DIR, "seen_markets.json")

def iso_to_local_str(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return iso

def load_seen() -> Set[str]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("ids", []))
        except Exception:
            return set()
    return set()

def save_seen(ids: Set[str]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = {"ids": sorted(list(ids))}
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tmp, f, ensure_ascii=False, indent=2)

def build_market_url(slug: str | None) -> str:
    if not slug:
        return "https://polymarket.com/"
    return f"https://polymarket.com/event/{slug}"

async def fetch_latest_markets(client: httpx.AsyncClient, limit: int = 50) -> List[dict]:
    # Сортируем по созданию (createdAt) по убыванию, берём последние N
    params = {
        "limit": limit,
        "order": "createdAt",
        "ascending": "false",
    }
    r = await client.get(GAMMA_MARKETS_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

async def send_telegram_message(bot_token: str, chat_id: str, text: str, disable_web_page_preview: bool = False) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": disable_web_page_preview,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()

def format_market_msg(m: dict) -> str:
    title = m.get("question") or "Новый рынок на Polymarket"
    slug = m.get("slug")
    url = build_market_url(slug)
    created = m.get("createdAt") or m.get("startDate") or ""
    created_local = iso_to_local_str(created) if created else "—"
    category = m.get("category") or "—"
    active = m.get("active")
    status = "active" if active else "inactive"
    # outcomePrices может быть строкой/массивом в схеме; аккуратно:
    outcome_prices = m.get("outcomePrices")
    if isinstance(outcome_prices, list):
        prices = ", ".join([str(p) for p in outcome_prices[:3]])
    else:
        prices = str(outcome_prices) if outcome_prices is not None else "—"
    msg = (
        f"<b>Новый рынок:</b> {title}\n"
        f"Категория: {category}\n"
        f"Создано: {created_local}\n"
        f"Статус: {status}\n"
        f"Цены исходов: {prices}\n"
        f"Ссылка: {url}"
    )
    return msg

async def main():
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    poll_interval = int(os.getenv("POLL_INTERVAL", "30"))
    fetch_limit = int(os.getenv("FETCH_LIMIT", "50"))
    notify_on_start = os.getenv("NOTIFY_ON_START", "false").lower() == "true"

    if not bot_token or not chat_id:
        raise SystemExit("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env")

    seen = load_seen()

    async with httpx.AsyncClient() as client:
        # Первичная выборка
        try:
            markets = await fetch_latest_markets(client, limit=fetch_limit)
        except Exception as e:
            raise SystemExit(f"Не удалось получить рынки: {e}")

        new_ids = []
        for m in markets:
            mid = str(m.get("id"))
            if mid and mid not in seen:
                new_ids.append(mid)

        if notify_on_start and new_ids:
            for m in markets:
                mid = str(m.get("id"))
                if mid in new_ids:
                    try:
                        await send_telegram_message(bot_token, chat_id, format_market_msg(m))
                    except Exception as e:
                        print(f"[ERROR] send start msg failed: {e}")
            seen.update(new_ids)
            save_seen(seen)
            print(f"[INIT] Отправлено начальных оповещений: {len(new_ids)}")
        else:
            # Просто запомнить текущие рынки, без уведомлений
            if new_ids:
                seen.update(new_ids)
                save_seen(seen)
                print(f"[INIT] Зафиксировано {len(new_ids)} существующих рынков без оповещения.")

        print("[RUN] Старт мониторинга новых рынков...")

        while True:
            try:
                markets = await fetch_latest_markets(client, limit=fetch_limit)
                to_notify = []
                for m in markets:
                    mid = str(m.get("id"))
                    if not mid:
                        continue
                    if mid not in seen:
                        to_notify.append(m)
                        seen.add(mid)

                if to_notify:
                    # Новые рынки обычно идут сверху; оповестим от старого к новому, чтобы сохранить порядок
                    for m in reversed(to_notify):
                        try:
                            await send_telegram_message(bot_token, chat_id, format_market_msg(m))
                        except Exception as e:
                            print(f"[ERROR] send msg failed: {e}")
                    save_seen(seen)
                    print(f"[{datetime.now().isoformat(timespec='seconds')}] Новых рынков: {len(to_notify)}")
            except httpx.HTTPStatusError as e:
                print(f"[HTTP] {e.response.status_code} {e.request.url}")
            except Exception as e:
                print(f"[ERROR] {e}")

            await asyncio.sleep(poll_interval)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Завершение работы...")
