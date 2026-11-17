"""
Home-Assistant-Add-on-Einstieg für den Cookidoo-MCP-Server.

- Liest die Add-on-Optionen aus /data/options.json
- Nutzt den Upstream-Server (danielkliem/mcp-cookidoo) unverändert für alle
  Cookidoo-Tools
- Ersetzt dessen statischen Bearer-Token durch GitHub-OAuth, damit claude.ai
  (Web + App) sich als Remote-Connector anmelden kann
- Lässt nur GitHub-Accounts aus `allowed_github_users` durch
"""

import json
import logging
import os
import sys
from pathlib import Path

OPTIONS_FILE = Path(os.environ.get("ADDON_OPTIONS", "/data/options.json"))
DATA_DIR = Path(os.environ.get("ADDON_DATA", "/data"))
PORT = 8001


def _load_options() -> dict:
    if not OPTIONS_FILE.exists():
        sys.exit(f"Optionsdatei {OPTIONS_FILE} nicht gefunden.")
    return json.loads(OPTIONS_FILE.read_text())


opts = _load_options()

logging.basicConfig(
    level=opts.get("log_level", "info").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("cookidoo-addon")

missing = [
    k
    for k in ("cookidoo_email", "cookidoo_password", "public_url",
              "github_client_id", "github_client_secret")
    if not opts.get(k)
]
allowed_users = {u.strip().lower() for u in opts.get("allowed_github_users", []) if u.strip()}
if missing:
    sys.exit(f"Bitte in der Konfiguration ausfüllen: {', '.join(missing)}")
if not allowed_users:
    sys.exit("allowed_github_users ist leer – mindestens deinen GitHub-Namen eintragen.")

PUBLIC_URL = opts["public_url"].rstrip("/")

# Umgebung für den Upstream-Code setzen, BEVOR er importiert wird.
os.environ["COOKIDOO_EMAIL"] = opts["cookidoo_email"]
os.environ["COOKIDOO_PASSWORD"] = opts["cookidoo_password"]
os.environ["COOKIDOO_QUALITY_BAR"] = str(opts.get("quality_bar", 70))
os.environ["COOKIDOO_MCP_MODE"] = "addon"  # verhindert, dass Upstream eine eigene App baut
os.environ["FASTMCP_HOME"] = str(DATA_DIR / "fastmcp")  # OAuth-Registrierungen überleben Neustarts

sys.path.insert(0, str(Path(__file__).parent / "upstream"))

import server as upstream  # noqa: E402
from fastmcp.server.auth.oauth_proxy import OAuthProxy  # noqa: E402
from fastmcp.server.auth.providers.github import GitHubTokenVerifier  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402
from starlette.routing import Route  # noqa: E402

mcp = upstream.mcp


# --------------------------------------------------------------------------
# Zugriffsschutz: GitHub-OAuth mit Allowlist
# --------------------------------------------------------------------------


class AllowlistGitHubVerifier(GitHubTokenVerifier):
    """Prüft das GitHub-Token wie üblich und lässt danach nur erlaubte Logins durch."""

    async def verify_token(self, token):
        result = await super().verify_token(token)
        if result is None:
            return None
        login = str((result.claims or {}).get("login") or "").lower()
        if login not in allowed_users:
            log.warning("Zugriff verweigert für GitHub-Benutzer '%s'", login)
            return None
        return result


redirect_uris = [u for u in opts.get("allowed_client_redirect_uris", []) if u.strip()]

auth = OAuthProxy(
    upstream_authorization_endpoint="https://github.com/login/oauth/authorize",
    upstream_token_endpoint="https://github.com/login/oauth/access_token",
    upstream_client_id=opts["github_client_id"],
    upstream_client_secret=opts["github_client_secret"],
    token_verifier=AllowlistGitHubVerifier(
        required_scopes=["read:user"],
        cache_ttl_seconds=300,  # spart GitHub-API-Aufrufe
    ),
    base_url=PUBLIC_URL,
    issuer_url=PUBLIC_URL,
    redirect_path="/auth/callback",
    allowed_client_redirect_uris=redirect_uris or None,
)
mcp.auth = auth


# --------------------------------------------------------------------------
# Zusätzliches Tool: die TM7-Regeln als abrufbare Anleitung
# (MCP-Prompts kann Claude nicht selbst aufrufen, Tools schon.)
# --------------------------------------------------------------------------

TM7_GUIDE = upstream.create_tm7_recipe.fn("<Gericht>") if hasattr(
    upstream.create_tm7_recipe, "fn"
) else upstream.create_tm7_recipe("<Gericht>")


@mcp.tool()
def tm7_rezept_anleitung() -> str:
    """
    IMMER ZUERST AUFRUFEN, bevor du ein Thermomix-Rezept entwirfst.

    Liefert die verbindlichen Formatregeln für TM7-Guided-Cooking-Schritte
    (Zeit/Temperatur/Stufe, Varoma, Anbraten, erlaubte Temperaturen) und den
    Ablauf Entwurf → Qualitätsprüfung → Freigabe durch den User → Upload.
    """
    return TM7_GUIDE


mcp.instructions = (
    "Cookidoo/Thermomix TM7 des Users (Cookidoo Schweiz, de-CH). "
    "Vor jedem neuen Rezept zuerst `tm7_rezept_anleitung` aufrufen und die Regeln "
    "strikt befolgen. Rezept immer erst dem User zeigen und nur nach ausdrücklicher "
    "Freigabe `upload_custom_recipe` aufrufen. `delete_custom_recipe` nur nach "
    "Bestätigung durch den User."
)


# --------------------------------------------------------------------------
# HTTP-App
# --------------------------------------------------------------------------


async def health(_request):
    return JSONResponse(
        {
            "status": "ok",
            "service": "cookidoo-mcp-addon",
            "public_url": PUBLIC_URL,
            "mcp_endpoint": f"{PUBLIC_URL}/mcp",
            "allowed_users": sorted(allowed_users),
        }
    )


public_host = PUBLIC_URL.split("://", 1)[-1].split("/", 1)[0]

app = mcp.http_app(
    path="/mcp",
    stateless_http=True,
    json_response=True,
    allowed_hosts=[public_host],
)
app.routes.append(Route("/health", health))


if __name__ == "__main__":
    import uvicorn

    log.info("Starte Cookidoo MCP auf Port %s – öffentlich: %s/mcp", PORT, PUBLIC_URL)
    log.info("Erlaubte GitHub-Benutzer: %s", ", ".join(sorted(allowed_users)))
    uvicorn.run(app, host="0.0.0.0", port=PORT, proxy_headers=True, forwarded_allow_ips="*")
