# Shlink + Uptime Kuma

Self-hosted link shortener (Shlink) + uptime monitor (Uptime Kuma).
A small Python bridge syncs every Shlink short URL into Kuma as an HTTP
monitor, so you find out within minutes if a target page goes down.

---

## Mimari

```
                            ┌─────────────────┐
   tarayıcı ──────────►   nginx (8080/8081)
                            │   reverse proxy │
                            └────┬───────┬────┘
                                 │       │
                  ┌──────────────┘       └───────────────┐
                  ▼ /                                    ▼ / (basic auth)
            ┌──────────┐                          ┌──────────────┐
            │  shlink  │  ◄── REST API ◄──────────│  shlink_web  │
            │ (PHP)    │                          │ (SPA + nginx)│
            └────┬─────┘                          └──────────────┘
                 │
                 ▼
            ┌──────────┐                          ┌──────────────┐
            │ shlink_db│                          │  uptime_kuma │  ◄── tarayıcı
            │ postgres │                          └──────┬───────┘     :3001
            └──────────┘                                 ▲
                  ▲                                      │
                  │      ┌────────────────────────┐      │
                  └──────│  shlink_kuma_bridge    │──────┘
                         │  (Python, polls 60s)   │
                         └────────────────────────┘
                          her döngü:
                          1. Shlink'ten short URL listesini çek
                          2. Kuma'daki [shlink] prefix'li monitorlerle karşılaştır
                          3. ekle / sil / güncelle
```

---

## Container'lar ve portlar

`shlink/docker-compose.yml` 6 servis çalıştırır:

| Servis | Image | Host portu | İç port | Görev |
| --- | --- | --- | --- | --- |
| `shlink_nginx` | `nginx:alpine` (custom) | **8080**, **8081** | 8080, 8081 | Reverse proxy + 8081'de basic auth |
| `shlink` | `shlinkio/shlink:stable` | — | 8080 | Shlink REST API + redirect motoru |
| `shlink_web` | `shlinkio/shlink-web-client:stable` (custom) | — | 8080 | Dashboard SPA, açılışta `servers.json`'ı `.env`'den üretir |
| `shlink_db` | `postgres:16-alpine` | — | 5432 | Shlink'in veritabanı |
| `uptime_kuma` | `louislam/uptime-kuma:1` | **3001** | 3001 | Monitor UI + sqlite |
| `shlink_kuma_bridge` | Python 3.12 (custom) | — | — | Shlink → Kuma sync döngüsü |

**Tarayıcıdan sadece 8080, 8081 ve 3001 erişilebilir.** Diğerleri docker network'ünde.

---

## URL'ler

| URL | Ne yapar | Yetki |
| --- | --- | --- |
| `http://localhost:8080/<kod>` | Kısa URL → uzun URL'ye 302 redirect | Public |
| `http://localhost:8080/rest/v3/...` | Shlink REST API | `X-Api-Key` header (`SHLINK_API_KEY`) |
| `http://localhost:8080/` | **404 — normal.** Shlink kökte hiçbir şey servis etmez | — |
| `http://localhost:8081/` | Shlink dashboard (SPA), API server otomatik bağlı | Basic auth: `NGINX_USER` / `NGINX_PASS` |
| `http://localhost:3001/` | Uptime Kuma UI | İlk açılışta admin kur, sonra o credentials |

---

## İlk kurulum

```powershell
cd shlink
docker compose up -d --build
```

Container'ların hepsinin ayakta olduğunu doğrula:

```powershell
docker compose ps
```

6 satır görmelisin. Sonra **mecburi tek manuel adım**:

1. `http://localhost:3001` aç
2. Kuma sana admin kurma ekranı gösterir. Username + password **birebir** `.env`'deki `KUMA_USER` ve `KUMA_PASS` ile aynı olsun (yoksa bridge giriş yapamaz).
   - Default: `KUMA_USER=admin@demo`, `KUMA_PASS=123456A`
3. Kuma admin'i oluşturulduğu an bridge sıradaki polling cycle'ında otomatik bağlanır — restart gerekmez.

Bunu yapana kadar `docker compose logs shlink_kuma_bridge` sürekli `Connection refused` veya login hatası basar — **normal**.

---

## Akış (end-to-end test)

1. **Dashboard'a gir:** `http://localhost:8081` → basic auth ile giriş.
2. **Kısa URL oluştur:** "Create short URL" → uzun URL gir (örn `https://example.com`) → save.
3. **Kısa URL'i test et:** Dashboard sana `http://localhost:8080/<kod>` döner. Yeni sekmede aç → `example.com`'a redirect.
4. **Kuma'ya senkronize olmasını bekle:** En fazla `POLL_INTERVAL` saniye (default 60). `http://localhost:3001` aç → monitor listesinde `[shlink] <kod> | https://example.com` görmelisin.
5. **Bridge log'undan teyit:**
   ```powershell
   docker compose logs -f shlink_kuma_bridge
   ```
   `[+] Added: <kod> → https://example.com` satırı geçmiş olmalı.

---

## .env ayarları

| Değişken | Ne işe yarar | Default |
| --- | --- | --- |
| `SHLINK_DOMAIN` | Shlink'in **kendine** gönderdiği canonical domain (kısa URL'lerin içinde geçer) | `localhost:8080` |
| `SHLINK_HTTPS` | Shlink kısa URL'leri `https://` olarak mı yazsın | `false` |
| `SHLINK_PUBLIC_URL` | **Tarayıcının** Shlink API'ye eriştiği URL (dashboard `servers.json` için) | `http://localhost:8080` |
| `SHLINK_API_KEY` | İlk API key (Shlink ilk açılışta seed eder), dashboard ve bridge bunu kullanır | `degistir-bunu-...` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Postgres credentials | `shlink` / `shlink` / `degistir...` |
| `NGINX_USER` / `NGINX_PASS` | `:8081` dashboard'a basic auth | `admin` / `degistir...` |
| `KUMA_USER` / `KUMA_PASS` | Bridge'in Kuma'ya login için kullandığı credentials. Kuma admin'ini birebir bunlarla kur | `admin@demo` / `123456A` |
| `POLL_INTERVAL` | Bridge'in Shlink ↔ Kuma sync döngü periyodu (saniye) | `60` |

> Prod'a almadan önce `degistir...` ile başlayan tüm değerleri rotate et ve `.env`'i `.gitignore`'a al.

---

## Bridge nasıl çalışır

`shlink/bridge/app.py`, sonsuz döngüde:

1. `GET /rest/v3/short-urls` ile Shlink'teki tüm kısa URL'leri çeker (paginated).
2. Kuma'ya login olur, `[shlink]` prefix'iyle başlayan monitorleri listeler — bunlar bridge'in yönettiği monitorler.
3. Üç set işlemi yapar:
   - **ADD:** Shlink'te var, Kuma'da yok → yeni HTTP monitor oluştur (5dk interval).
   - **DELETE:** Shlink'te yok, Kuma'da var → monitor'ü sil.
   - **UPDATE:** Her ikisinde var ama uzun URL değişmiş → monitor'ün URL'ini güncelle.
4. `POLL_INTERVAL` saniye uyu, baştan.

Kuma'da `[shlink]` prefix'i olmayan monitor'lere **dokunmaz** — manuel monitor'lerin güvende.

---

## Yaygın sorunlar

| Belirti | Sebep | Çözüm |
| --- | --- | --- |
| `localhost:8080/` → 404 | Shlink kökte UI yok, by design | UI için `:8081`'e git |
| `localhost:8081/` → 502 | nginx'in upstream port'u yanlış (eski image v3'te `:80`, yeni v4+'ta `:8080`) | `nginx.conf` doğru, `docker compose build --no-cache nginx && docker compose up -d nginx` |
| Bridge log: `Connection refused` (shlink) | Bridge, Shlink henüz ready değilken poll etti | Birkaç döngüde otomatik geçer |
| Bridge log: `Incorrect username or password` | Kuma'daki admin user/pass `.env`'dekiyle eşleşmiyor | Ya Kuma'da düzelt, ya `.env`'i değiştir + `docker compose up -d shlink_kuma_bridge` |
| Dashboard "Server not found" | `SHLINK_PUBLIC_URL` tarayıcıdan erişilemiyor (örn `http://shlink:8080` yazdın) | `.env`'de `SHLINK_PUBLIC_URL`'i `http://localhost:8080` yap, `docker compose up -d --build shlink_web` |
| `dependency failed to start: No such container: <id>` | Docker iç state'i bayatlamış | `docker compose down && docker compose up -d` |
| Windows'ta script `illegal option -` | git LF→CRLF çevirisi yapmış | `.gitattributes` LF zorluyor; sorunu görürsen `git rm --cached <file> && git checkout <file>` |

---

## Faydalı komutlar

```powershell
# Durum
docker compose ps

# Belirli servisin log'u
docker compose logs -f shlink
docker compose logs -f shlink_kuma_bridge

# Servisi cache'siz rebuild + restart
docker compose build --no-cache <servis>
docker compose up -d <servis>

# Tüm stack'i temiz başlat (data korunur)
docker compose down
docker compose up -d

# Tüm stack'i SİL (volume'ler dahil — Postgres, Kuma data uçar)
docker compose down -v
```
