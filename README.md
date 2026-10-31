# ÖkoFEN Portal for Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lenoxys&repository=ha-oekofen-portal&category=integration)

Reads from the **my.oekofen.info** portal what the local JSON interface of an ÖkoFEN Touch controller does not expose.

> **Unofficial.** Not affiliated with or endorsed by ÖkoFEN. It uses the same web API as the portal's own web app, with your own account. ÖkoFEN can change it at any time. Use at your own risk.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/panel-dark.gif">
    <img alt="The ÖkoFEN sidebar panel: an animated schematic of the installation" src="docs/panel-light.gif" width="900">
  </picture>
</p>

<p align="center"><em>The sidebar panel, live from your controller (sample values: a sunny autumn day, the house heated from the buffer tank, a hot water draw, the pool off). Pumps turn, pipes flow, hover anything for its values.</em></p>

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

## Entity types (v0.8)

| Type | What | Writes |
|---|---|---|
| `climate` | one thermostat per heating circuit the controller has: room temperature, comfort target, mode (off / auto / heat) and preset (comfort / eco = setback), `hvac_action` *heating* when the circuit pump runs; attributes: flow temperature and setpoint, effective target, decoded status | mode and comfort target |
| `water_heater` | one per hot water circuit: top sensor of the tank, comfort target, operation (off / auto / performance = forced on) | operation and target |
| `weather` | the controller's forecast (see below) | no |
| `event` | the burner of the existing boiler: `started` and `stopped` (with the boiler temperature and, on stop, the run time in seconds), seen at the 30 s poll | no |
| `scene` | **Solar priority** (solar discharge 64 / 60 °C on the solar pump, buffer overshoot 3 K) and **Default values** (82 / 81 °C, schedule, 5 K). They write several settings at once and **put the earlier ones back if one write fails**. They are experimental: check the values in `presets.py` first. | yes |
| `switch`, `sensor` | **Solar boost** (off by default) and its state: *off*, *waiting* (attribute `reason`: buffer too cold, cloudy, outside the sun window…), *boosting*, *restoring*. See below. | the comfort target and the chosen radiator heads, while it runs |
| `binary_sensor` | *Pump running* for every pump that reports a speed in %, plus the two-state variables | no |
| `sensor`, `number`, `select` | measurements, decoded status words, the allow-listed settings (now also the eco mode of heating and hot water) | number, select |

All writes go through the same allow-list with bounds. Home Assistant's own scenes and scripts can drive the `number` and `select` entities too.

**Reconfigure**: the account can be changed from the integration's menu (the installation must stay the same). A refused password opens the *re-authenticate* prompt.

## Solar boost (v0.12, experimental)

On sunny days, heat the house a few degrees above normal with the buffer tank's solar surplus, without calling the boiler, so the walls carry the heat into the evening. ÖkoFEN's own *solar discharge* cannot do it: it starts at 82 °C on a tank that tops out around 70 °C, does not know the hot water reserve or the sunset, and does not open thermostatic radiator heads.

When the switch is on, the integration checks every 30 s and **raises the comfort target** (24 °C by default) when all of these hold: the burner is off, heating is on, it is between sunrise + 2 h and sunset − 1 h 30, the controller's forecast cloud cover is under its own limit (`weather_limit`), the outdoor temperature is under the heating limit, the **buffer top is above the worst-case buffer setpoint** (flow max + overshoot + 1 K + 1.5 K, because raising the comfort raises the buffer setpoint, and the boiler starts when the top falls under it), the **hot water probe keeps its reserve** (55 °C, and never under its own setpoint + 1 K), and the room is under the target. It opens the radiator heads you chose (any `climate` entity) at the same time.

It puts everything back as soon as one condition fails (with 1.5 K of hysteresis and 10 min between changes), **at once if the burner starts**, if values go missing, or if the comfort is changed by hand (then it keeps your value, and does not start again that day). A head changed by hand meanwhile is left alone. What to put back is saved on disk: after a restart or a reload the integration restores first, and retries on the reconnection schedule if the portal does not answer. Settings: *Configure* on the integration (target, buffer threshold, hot water reserve, minutes after sunrise / before sunset, radiator heads).

The effective room setpoint is the comfort target plus the controller's own offsets (remote control offset, eco mode on sunny days), so the house may settle under the target. Check the logic without Home Assistant with `python3 scripts/backtest_solar_boost.py`; with `HASS_URL` and `HASS_TOKEN` it also replays the decision on the history of the Pellematic Compact integration (read-only).

## ÖkoFEN panel (sidebar)

The integration adds an **ÖkoFEN** entry to Home Assistant's sidebar: an animated schematic of the installation (collectors, buffer tank with its four sensors, back-up boiler and its pump, heating circuit with the mixing valve, hot water plate exchanger, pool exchanger), drawn from the integration's own data every 15 seconds. Pumps turn when they run, pipes flow when there is circulation (including a hot water draw, read from the hot water kit pump), the burner is a red or grey flame, and the sky icon (sun, moon, cloud) follows the controller's weather. Hover (or focus) an element for its values, differences and a few computed figures. Below the schematic, a **replay bar** plays yesterday and today back (play / pause, drag, *Now*), with the burner and solar pump runs marked on the track; the sky follows, with sunrise, sunset, moonrise, rain, snow, storm and fog. Two more tabs: **Solar optimisation** (the solar boost, every condition with its value and threshold, turn it on or off) and **History** (today and yesterday: tank, collectors, flow, room and outdoor temperatures, burner, pumps and boost lanes). The integration keeps its own 48 h of values, one point a minute, so none of this needs the recorder. It follows the language of your user profile (English, French, German, Spanish, Portuguese, Japanese, Chinese) and Home Assistant's light / dark theme.

The layout is **one fixed reference scheme** (a buffer tank with a low solar coil, hot water by plate exchanger, a pool exchanger). Elements your controller does not report show "–". Try it outside Home Assistant with sample values by serving the repository (`python3 -m http.server`) and opening `/scripts/preview.html?lang=fr` (`&tab=solar`, `&tab=history`, `&code=601` for snow; `python3 scripts/preview_history.py` fills the replay with your own Home Assistant history).

## Readable names, descriptions and status

- **One Home Assistant device per circuit or function** (Heating circuit 1, Hot water 1, Buffer 1, Solar circuit 1…, Existing boiler, Weather…), each with a short description in its *model* field. **Only equipment the controller really has** is created: the portal answers for 6 heating circuits, 4 pellet boilers, etc. whether they exist or not, so the controller's own `vorhanden` (present) flags are used to leave the others out (on a typical installation, 9 devices instead of 38). Devices created for absent equipment by earlier versions are removed.
- **A real `weather` entity** for the controller's weather module: current temperature, cloud cover, wind and condition, plus the 3-hourly forecast it uses to anticipate sunny days. The other weather values (forecast clouds and temperature used by the eco mode, forecast day, the daily window as HH:MM) are sensors.
- **Entity names are translated** (English or French, following Home Assistant's language) from the controller's German variable names: `raumtemp_ist` becomes *Room temperature (actual)* / *Température de la pièce (mesure)*. Words that are not in the glossary stay as they are.
- **Languages live in files, not in code**: `custom_components/okofen_portal/i18n/<code>.json` holds the glossary, the circuit labels and descriptions, the explanations of the main variables and the panel strings; `translations/<code>.json` holds Home Assistant's own entity and form texts. The files shipped are `en`, `fr`, `de`, `es`, `pt`, `ja` and `zh` (Simplified Chinese: `i18n/zh.json` and `translations/zh-Hans.json`); `de`, `es`, `pt`, `ja` and `zh` were machine-translated, so corrections are welcome. To add a language, copy the `en.json` of both folders and translate what you can: missing keys fall back to English.
- **Every entity has a `description` attribute** (and a `portal_variable` attribute with the controller's own name). For the writable settings it is ÖkoFEN's own help text.
- **Status words are decoded**: the controller's `status` numbers (for example `512` on the buffer tank) are shown as ÖkoFEN's own messages, such as *Demande marche OFF*; each set bit is one message, and the raw number stays in the `raw` attribute.

ÖkoFEN's labels and help texts are **downloaded from the portal's public files when the integration starts** (and cached by Home Assistant for a week); none of them is stored in this repository. If the portal cannot be reached, names and descriptions fall back to the built-in glossary and status words are shown as numbers.

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

Lit sur le portail **my.oekofen.info** ce que l'interface JSON locale des régulations ÖkoFEN Touch n'expose pas: contact brûleur et température de la chaudière existante, statut de la vanne mélangeuse du circuit de chauffage 1. API non officielle, avec votre propre compte. Installation par HACS (dépôt personnalisé, type *Intégration*), puis ajout de l'intégration avec vos identifiants my.oekofen.info. Version 0.12 (expérimental): **surchauffe solaire** (interrupteur, désactivé par défaut): les jours de soleil, la consigne de confort est relevée (24 °C) et les têtes de radiateur choisies sont ouvertes pour chauffer la maison avec le surplus du ballon, sans la chaudière; tout est remis dès qu'une condition n'est plus remplie, immédiatement si le brûleur démarre. Panneau: barre de lecture d'hier et d'aujourd'hui sous le schéma, onglets *Optimisation solaire* et *Historique*. Version 0.8: entités climate, water_heater, event et scene, reconfiguration du compte. Version 0.7: panneau ÖkoFEN dans la barre latérale (schéma animé), entité météo, équipements absents ignorés. Version 0.5: noms et descriptions lisibles, codes d'état décodés avec les libellés d'ÖkoFEN (téléchargés au démarrage depuis le portail), un appareil par circuit, lecture de toutes les variables en lecture du portail (environ 440 entités, la plupart désactivées par défaut) et écriture d'une liste autorisée de réglages avec bornes (décharge solaire, courbe de chauffe, marge du ballon, mode été/hiver).

## License

MIT

## Local interface (optional)

The controller also has a local JSON interface (`http://<address>:4321/<local password>/all`, to enable on the controller). If you give its address and local password when adding or reconfiguring the integration, the fast values (collector, the four buffer sensors, pumps, flow and room temperatures, outdoor temperature: 15 variables) are read **locally every 10 seconds** instead of through the portal every 30 seconds. What the local interface does not give (burner contact, boiler temperature, mixing valve, status words, every other variable) still comes from the portal, and all writes go through the portal. If the local interface stops answering, the integration silently falls back to the portal. `scripts/check_local.py` compares both sources.
