# Бот-оповещатель о новых голосованиях (рынках) на Polymarket

Этот бот каждые N секунд опрашивает публичное API Polymarket (Gamma Markets API) и, когда появляется **новый рынок** (новое событие/голосование), отправляет сообщение в Telegram‑чат.

## Как это работает (кратко)
- Используется endpoint: `https://gamma-api.polymarket.com/markets` (официальная Gamma Markets API).
- Запрос сортируется по времени создания и берёт последние `FETCH_LIMIT` рынков.
- Состояние сохранённых ID хранится локально в `data/seen_markets.json`.
- При обнаружении новых ID — бот отправляет в Telegram сообщение с названием, ссылкой и временем создания.

## Шаги установки

1) **Установите Python 3.10+**  
   Проверьте:  
   ```bash
   python --version
   ```

2) **Склонируйте/распакуйте проект** (или скачайте ZIP из чата)  
   Перейдите в папку проекта:
   ```bash
   cd polymarket_new_markets_alert_bot
   ```

3) **Создайте виртуальное окружение и установите зависимости**  
   ```bash
   python -m venv .venv
   .venv\Scripts\activate    # Windows
   # или
   source .venv/bin/activate   # macOS/Linux

   pip install -r requirements.txt
   ```

4) **Создайте файл `.env`** на основе `.env.example` и заполните:
   - `TELEGRAM_BOT_TOKEN` — токен вашего бота (получите у @BotFather)
   - `TELEGRAM_CHAT_ID` — ID чата/канала, куда слать оповещения  
     (для каналов/супергрупп это обычно отрицательное число, формат `-100...`).
   - Необязательно: `POLL_INTERVAL`, `FETCH_LIMIT`, `NOTIFY_ON_START`

5) **Запустите бота**  
   ```bash
   python polymarket_new_markets_bot.py
   ```

   По умолчанию бот **не** шлёт сообщения о старых рынках при старте (`NOTIFY_ON_START=false`), а только о **новых**, появившихся после запуска.  
   Если хотите разово получить оповещения о уже существующих рынках при первом старте — поставьте `NOTIFY_ON_START=true` и затем верните на `false`.

## Дополнительно
- Логи пишутся в консоль.
- Файл состояния: `data/seen_markets.json`. Можно удалить, если хотите «забыть» историю.
- При необходимости меняйте частоту опроса через `POLL_INTERVAL`.
- Endpoint и параметры соответствуют официальной документации Polymarket Gamma Markets API.

## Ссылки на документацию (для справки)
- Gamma Markets API — Get Markets: https://docs.polymarket.com/developers/gamma-markets-api/get-markets
- Эндпоинт: `https://gamma-api.polymarket.com/markets`

---

**Вопросы/идеи** — пишите в чате, помогу настроить фильтры (например, оповещать только по определённым категориям/тегам).
