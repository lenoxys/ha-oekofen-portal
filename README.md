# ÖkoFEN Portal for Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lenoxys&repository=ha-oekofen-portal&category=integration)

Reads from the **my.oekofen.info** portal what the local JSON interface of an ÖkoFEN Touch controller does not expose.

> **Unofficial.** Not affiliated with or endorsed by ÖkoFEN. It uses the same web API as the portal's own web app, with your own account. ÖkoFEN can change it at any time. Use at your own risk.

## What it provides

Every read-only variable of the controller that the portal returns (about 440 on a typical Touch installation), one entity each:

- **numbers** (temperatures, percentages, durations, energy…), **two-state variables** as binary sensors, **multi-state variables** as enum sensors;
- **enabled by default**: the ones the local API does not give:

| Entity | Portal variable |
|---|---|
| Burner (binary sensor, "running") | `L_ke_brennerkontakt_1`: contact of the existing boiler's burner |
| Boiler temperature | `L_ke_temp_ist`: sensor of the existing boiler |
| Heating mixing valve (stopped / opening / closing) | `L_hk[0].mischer`: heating circuit 1 |

- **one Home Assistant device per circuit or function** (Heating circuit 1, Hot water 1, Buffer 1, Solar circuit 1…, Existing boiler, Weather, Pellet boiler 1-4…), all under the main ÖkoFEN device; only the groups present on your controller get entities.
- **all the others are created disabled** (diagnostic category): enable the ones you want in *Settings → Devices & services → ÖkoFEN Portal → entities*. Their names are the controller's own variable names (`hk[0] raumtemp ist`, `sk[1] pumpe`…); see [`catalog.json`](custom_components/okofen_portal/catalog.json).

The burner contact and boiler temperature are shown on the controller's screen but are **not** available through the local API (`/all`), hence not in the local Home Assistant integrations. This integration is meant to **complement**, not replace, an integration of the local API such as `oekofen_pellematic_compact`.

## Settings you can change (v0.3)

A short **allow-list** of settings is exposed as `number` / `select` entities (configuration category). Every number has bounds, nothing outside the list can be written, and safety settings (collector protection, maximum boiler temperatures) are deliberately not included. Values are written to the controller through the portal; the controller confirms each write.

| Entity | Portal variable | Bounds |
|---|---|---|
| Solar discharge heating: start / stop | `hk[0].solarheiz_temp_ein` / `_aus` | 40-90 / 30-90 °C |
| Solar discharge heating mode (schedule / solar pump) | `hk[0].solarheiz_mode` | 2 options |
| Solar discharge hot water: start / stop | `ww[0].solarheiz_temp_ein` / `_aus` | 40-90 / 30-90 °C |
| Buffer overshoot above flow setpoint | `hk[0].ueberhoehung` | 0-15 K |
| Heating flow temperature max / min | `hk[0].vorlauftemp_max` / `_min` | 30-75 / 15-40 °C |
| Heating curve base point / slope | `hk[0].heizkurve_fusspunkt` / `_steigung` | 20-60 °C / 0.2-3.5 |
| Heating limit outdoor temperature, comfort / setback | `hk[0].heizgrenze_heizen` / `_absenken` | 10-30 / 5-25 °C |
| Summer / winter mode | `anlage_betriebsart` | winter (heating + hot water) or summer (hot water only); "off" is not offered |

**You are changing the settings of your heating system.** Note the values before changing them. The portal and the controller's screen show the same settings, so you can always set them back there.

## Install with HACS

1. HACS → ⋮ → *Custom repositories* → add `https://github.com/lenoxys/ha-oekofen-portal`, type **Integration**.
2. Install **ÖkoFEN Portal**, restart Home Assistant.
3. Settings → Devices & services → *Add integration* → **ÖkoFEN Portal** and enter your my.oekofen.info login.

The three variables above are polled every 30 seconds, the rest of the catalog every 5 minutes. The OAuth client id/secret of the portal's web app are read from the app's public JavaScript at login, so no secret is stored in this repository. Your password is kept in Home Assistant's config entry, like any other integration.

## Limits

- First installation of the account only.
- Writing is limited to the allow-list above (heating circuit 1 and hot water circuit 1).
- Text variables are not exposed.
- Needs internet and the portal to be up.

## Try the API client without Home Assistant

```
pip install aiohttp
OEKOFEN_USER=you@example.com OEKOFEN_PASSWORD=... python scripts/check_api.py
```

## Français

Lit sur le portail **my.oekofen.info** ce que l'interface JSON locale des régulations ÖkoFEN Touch n'expose pas: contact brûleur et température de la chaudière existante, statut de la vanne mélangeuse du circuit de chauffage 1. API non officielle, avec votre propre compte. Installation par HACS (dépôt personnalisé, type *Intégration*), puis ajout de l'intégration avec vos identifiants my.oekofen.info. Version 0.3: lecture de toutes les variables en lecture du portail (environ 440 entités, la plupart désactivées par défaut) et écriture d'une liste autorisée de réglages avec bornes (décharge solaire, courbe de chauffe, marge du ballon, mode été/hiver).

## License

MIT
