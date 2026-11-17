# Cookidoo MCP für Home Assistant

Thermomix-TM7-Rezepte in Claude (Web **und** App) erstellen und direkt in deinem
Cookidoo-Konto unter «Meine Rezepte» anlegen – mit Guided-Cooking-Schritten
(Play-Button am TM7).

```
Claude-App / claude.ai
        │  (Anthropic-Cloud ruft den Connector auf)
        ▼
Cloudflare Tunnel  →  https://cookidoo.immer.uk
        ▼
Dieses Add-on auf dem Pi (Port 8001, GitHub-Login, nur Globiglobi erlaubt)
        ▼
Cookidoo → Sync → TM7
```

Basis: [danielkliem/mcp-cookidoo](https://github.com/danielkliem/mcp-cookidoo) (MIT),
unverändert eingebunden unter `cookidoo_mcp/app/upstream/`. Dazu kommen
GitHub-OAuth mit Allowlist (damit claude.ai sich anmelden kann), ein Tool
`tm7_rezept_anleitung` und die Home-Assistant-Verpackung.

> Inoffiziell: Cookidoo hat keine öffentliche API. Vorwerk kann die
> Schnittstelle jederzeit ändern. Nur für das eigene Konto verwenden.

---

## Einrichtung (ca. 30 Minuten)

### 1. Repo öffentlich machen

Home Assistant kann private GitHub-Repos nicht ohne Weiteres laden. Im Repo
liegen keine Geheimnisse (Passwörter kommen erst in HA in die Konfiguration),
also: GitHub → `ha-cookidoo-mcp` → **Settings** → ganz unten **Change
visibility** → **Public**.

### 2. GitHub-OAuth-App anlegen

GitHub → Profilbild → **Settings** → **Developer settings** → **OAuth Apps**
→ **New OAuth App**:

| Feld | Wert |
|---|---|
| Application name | `Cookidoo MCP` |
| Homepage URL | `https://cookidoo.immer.uk` |
| Authorization callback URL | `https://cookidoo.immer.uk/auth/callback` |

**Register application** → **Generate a new client secret**. Die **Client ID**
und das **Client secret** kopieren (das Secret wird nur einmal angezeigt).

### 3. Add-on installieren

1. HA → **Einstellungen → Apps** (früher «Add-ons») → **App Store**
2. Oben rechts **⋮ → Repositories** → `https://github.com/Globiglobi/ha-cookidoo-mcp` → **Hinzufügen**
3. Seite neu laden, **Cookidoo MCP** öffnen → **Installieren**
   (der Pi baut das Image selbst, das dauert 5–10 Minuten)
4. Tab **Konfiguration** ausfüllen:

   | Option | Wert |
   |---|---|
   | `cookidoo_email` | deine Cookidoo-E-Mail |
   | `cookidoo_password` | dein Cookidoo-Passwort |
   | `public_url` | `https://cookidoo.immer.uk` (vorausgefüllt) |
   | `github_client_id` | aus Schritt 2 |
   | `github_client_secret` | aus Schritt 2 |
   | `allowed_github_users` | `Globiglobi` (vorausgefüllt) |

   Den Rest so lassen → **Speichern**.
5. Tab **Info** → **Starten**. Im Tab **Protokoll** sollte erscheinen:
   `Starte Cookidoo MCP auf Port 8001 – öffentlich: https://cookidoo.immer.uk/mcp`
6. Kurzer Test im Heimnetz: `http://<IP-des-Pi>:8001/health` im Browser
   → `{"status":"ok", …}`. Die IP findest du unter
   **Einstellungen → System → Netzwerk**.

### 4. Cloudflare-Tunnel einrichten

1. **Einstellungen → Apps → App Store → ⋮ → Repositories** →
   `https://github.com/homeassistant-apps/repository` hinzufügen
2. **Cloudflared** installieren, Tab **Konfiguration**, auf **In YAML bearbeiten** umschalten und einfügen
   (IP durch die deines Pi ersetzen):

   ```yaml
   external_hostname: ""
   additional_hosts:
     - hostname: cookidoo.immer.uk
       service: http://192.168.1.XX:8001
   ```

   `external_hostname` bleibt leer, damit Home Assistant selbst **nicht**
   ins Internet gestellt wird – nur der MCP-Server.
3. **Starten** → im **Protokoll** erscheint ein Link zu Cloudflare. Öffnen, die
   Domain `immer.uk` auswählen, **Authorize**. Tunnel und DNS-Eintrag legt das
   Add-on danach selbst an.
4. Test von unterwegs (z. B. Handy ohne WLAN):
   `https://cookidoo.immer.uk/health` → `{"status":"ok", …}`

### 5. Connector in Claude hinzufügen

1. claude.ai im Browser → **Einstellungen → Connectors** →
   **Eigenen Connector hinzufügen**
2. Name `Cookidoo`, URL `https://cookidoo.immer.uk/mcp` → **Hinzufügen**
3. **Verbinden** → Bestätigungsseite des Servers → GitHub-Login → zurück zu Claude
4. Fertig – der Connector ist jetzt auch in der Claude-App verfügbar.

### 6. Erster Test

Neuer Chat: *«Erstelle mir ein TM7-Rezept für Risotto mit Pilzen für 4 Personen
und lade es nach meiner Freigabe in Cookidoo hoch.»*

Danach am TM7 unter **Meine Rezepte** öffnen und prüfen, ob die Schritte mit
Play-Button erscheinen.

### Optional: ChatGPT anbinden

1. In HA bei **Cookidoo MCP → Konfiguration** unter `allowed_client_redirect_uris`
   `https://chatgpt.com/connector_platform_oauth_redirect` ergänzen → Speichern → Add-on neu starten
2. chatgpt.com → **Einstellungen → Apps & Connectors → Erweitert → Entwicklermodus** einschalten
3. **Connector erstellen**: URL `https://cookidoo.immer.uk/mcp`, Authentifizierung **OAuth**
   (Client-ID/Secret leer lassen) → GitHub-Login
4. Im Chat den Connector über das **+**-Menü aktivieren

---

## Was am TM7 geführt funktioniert

| Art | Format im Schritt | Am TM7 |
|---|---|---|
| Mixen/Kochen | `5 Sek./Stufe 5`, `18 Min./100°C/Linkslauf/Stufe 1` | Play-Button |
| Varoma | `15 Min./Varoma/Stufe 2` | Play-Button |
| Anbraten | `5 Min./150°C/Intensiv` (140–160 °C) | Play-Button |
| Teigkneten, Gären, Turbo, Reiskocher | als Text | manuell einstellen |

Schritte müssen **nur** die Einstellung enthalten (höchstens ein Verb davor),
sonst zeigt der TM7 eine Checkbox statt Play-Button. Claude bekommt diese
Regeln über das Tool `tm7_rezept_anleitung`.

## Sicherheit

- Zugriff nur nach GitHub-Login, und nur Accounts aus `allowed_github_users`.
  Alle anderen bekommen bei jedem Aufruf `401`.
- Nur die Claude-Callback-Adressen dürfen sich als Client registrieren
  (`allowed_client_redirect_uris`).
- Home Assistant selbst bleibt privat, getunnelt wird nur Port 8001.
- Empfehlung: für Cookidoo ein eigenes, sonst nirgends verwendetes Passwort.

## Fehlersuche

| Symptom | Lösung |
|---|---|
| Add-on startet nicht, «Bitte in der Konfiguration ausfüllen» | fehlende Option eintragen |
| Claude: «Verbindung fehlgeschlagen» beim Hinzufügen | `https://cookidoo.immer.uk/health` prüfen → Tunnel/IP in Cloudflared falsch |
| GitHub zeigt «redirect_uri is not associated» | Callback-URL der OAuth-App muss exakt `https://cookidoo.immer.uk/auth/callback` sein |
| Login klappt, Tools liefern 401 | GitHub-Name in `allowed_github_users` prüfen (Protokoll zeigt «Zugriff verweigert für …») |
| «invalid_redirect_uri» bei der Registrierung | Claude nutzt eine neue Callback-Adresse → `allowed_client_redirect_uris` leeren (erlaubt alle) |
| «Login failed» bei Cookidoo-Tools | Cookidoo-E-Mail/Passwort prüfen; Abo aktiv? |

## Updates

Version in `cookidoo_mcp/config.yaml` erhöhen und pushen → HA zeigt ein Update an.
