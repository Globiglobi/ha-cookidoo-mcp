# Cookidoo MCP

MCP-Server, mit dem Claude Thermomix-TM7-Rezepte direkt in dein Cookidoo-Konto
schreibt. Die vollständige Einrichtung steht im
[README des Repos](https://github.com/Globiglobi/ha-cookidoo-mcp).

## Optionen

| Option | Bedeutung |
|---|---|
| `cookidoo_email` / `cookidoo_password` | Cookidoo-Login (Cookidoo Schweiz, de-CH) |
| `public_url` | Öffentliche Adresse über den Cloudflare-Tunnel, ohne `/mcp` |
| `github_client_id` / `github_client_secret` | GitHub-OAuth-App, Callback `<public_url>/auth/callback` |
| `allowed_github_users` | Nur diese GitHub-Accounts dürfen den Server nutzen |
| `allowed_client_redirect_uris` | Erlaubte OAuth-Callbacks der MCP-Clients; leer = alle |
| `quality_bar` | Mindestpunktzahl 0–100 für den Upload (Standard 70) |
| `log_level` | debug, info, warning, error |

## Endpunkte

- `POST /mcp` – MCP (OAuth erforderlich)
- `GET /health` – Status ohne Anmeldung
