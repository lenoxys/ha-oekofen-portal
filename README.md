# ÖkoFEN Portal for Home Assistant

Reads from the **my.oekofen.info** portal what the local JSON interface of an ÖkoFEN Touch controller does not expose.

> **Unofficial.** Not affiliated with or endorsed by ÖkoFEN. It uses the same web API as the portal's own web app, with your own account. ÖkoFEN can change it at any time. Use at your own risk.

## What it provides (v0.1, read-only)

| Entity | Portal variable |
|---|---|
| Burner (binary sensor, "running") | `L_ke_brennerkontakt_1`: contact of the existing boiler's burner |
| Boiler temperature | `L_ke_temp_ist`: sensor of the existing boiler |
| Boiler setpoint (disabled by default) | `L_ke_temp_soll` |
| Heating mixing valve (stopped / opening / closing) | `L_hk[0].mischer`: heating circuit 1 |

These values are shown on the controller's screen but are **not** available through the local API (`/all`), hence not in the local Home Assistant integrations.

It is meant to **complement**, not replace, an integration of the local API such as `oekofen_pellematic_compact`.

## Install with HACS

1. HACS → ⋮ → *Custom repositories* → add `https://github.com/lenoxys/ha-oekofen-portal`, type **Integration**.
2. Install **ÖkoFEN Portal**, restart Home Assistant.
3. Settings → Devices & services → *Add integration* → **ÖkoFEN Portal** and enter your my.oekofen.info login.

The integration polls every 30 seconds. The OAuth client id/secret of the portal's web app are read from the app's public JavaScript at login, so no secret is stored in this repository. Your password is kept in Home Assistant's config entry, like any other integration.

## Limits

- First installation of the account only; heating circuit 1 and the "existing boiler" input only.
- Needs internet and the portal to be up.
- No write access yet (planned, with an allow-list of variables).

## Try the API client without Home Assistant

```
pip install aiohttp
OEKOFEN_USER=you@example.com OEKOFEN_PASSWORD=... python scripts/check_api.py
```

## Français

Lit sur le portail **my.oekofen.info** ce que l'interface JSON locale des régulations ÖkoFEN Touch n'expose pas: contact brûleur et température de la chaudière existante, statut de la vanne mélangeuse du circuit de chauffage 1. API non officielle, avec votre propre compte. Installation par HACS (dépôt personnalisé, type *Intégration*), puis ajout de l'intégration avec vos identifiants my.oekofen.info. Version 0.1: lecture seule.

## License

MIT
