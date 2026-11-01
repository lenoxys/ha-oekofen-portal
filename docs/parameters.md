---
title: Parameters and nomenclature
nav_order: 2
---

# Parameters and nomenclature
{: .no_toc }

What the integration learned about the controller: where the values come from, how they are named and how to read them. Observed on a Pelletronic Touch with JSON interface V4.00b; treat anything marked *observed* as a finding on one installation, not a specification.

1. TOC
{:toc}

## Two ways to the controller

| | Portal (my.oekofen.info) | Local JSON interface |
|---|---|---|
| Address | `https://my.oekofen.info/api/pwa/v1/plants/<plant>/remotecontrol/variables` | `http://<controller>:4321/<password>/<command>` |
| Read | `POST` a JSON list of names | `GET all` (values) or `all?` (values with factor, unit, bounds and state texts) |
| Write | `PUT` a list of name / value | `GET <group>_<field>=<raw>` |
| Covers | every variable of the controller, settings included | a subset: measurements, thermostats, hot water, solar, weather |
| Limits | needs the internet and the portal's link to the controller | one request every 2.5 s; enable it on the Touch (network settings, JSON interface) |

**Portal.** The integration logs in like the portal's web app (OAuth2 with your account) and reads the plant id from the plant list. A read answers `{"name", "value", "divisor", "unitText", "formatTexts"}` per variable; the real value is `value / divisor`. A 404 on `remotecontrol/variables` means the portal cannot reach the controller at the moment.

**Local interface.** Other commands: one group (`hk1`, `pu1`, `ww1`, `sk1`, `system`, `weather`, `forecast`, `error`…); a group the plant does not have answers with a help page. A write answers with the field and the value it accepted (`hk1_temp_heat=225`); anything else is a refusal. Too fast a request answers `Wait at least …`: wait and retry. Fields starting with `L_` are read only.

The integration reads the local interface every 10 seconds when it is configured, writes there what the local interface knows (thermostat mode, comfort temperature, eco mode, hot water mode and target) and uses the portal for the rest.

## Naming

Portal names look like `CAPPL:LOCAL.hk[0].raumtemp_heizen`:

| Part | Meaning |
|---|---|
| `CAPPL:` | prefix of every portal name |
| `LOCAL.` | the controller itself; the pellet boilers are `CAPPL:FA[n].…` without it |
| `hk[0]` | group and instance, counted **from 0** on the portal; the local interface counts **from 1** (`hk[0]` = `hk1`) |
| `L_` | a measurement or a state (`L_hk[0].vorlauf_ist`): read only. Without it: a setting |
| `[1]` after a field | an index inside the field (`betriebsart[1]`, `zeitprogramm[1].tag[3]`) |

The local interface uses its own, mostly English, field names (`hk1.temp_heat` = `hk[0].raumtemp_heizen`). The [variable reference](variables.md) lists the pairs the integration knows.

### Groups

| Group | Meaning |
|---|---|
| `hk` (Heizkreis) | heating circuit |
| `ww` (Warmwasser) | hot water |
| `pu` (Pufferspeicher) | buffer tank |
| `sk` (Solarkreis) | solar circuit |
| `ke_`, `bestke_` (bestehender Kessel) | existing boiler (oil or gas) driven by the controller |
| `FA` (Feuerungsautomat) | pellet boiler |
| `weather_`, `L_weather…` | weather module (forecast from the internet) |
| `anlage_`, `system` | the plant as a whole |

### German glossary

| Term | Meaning | Term | Meaning |
|---|---|---|---|
| `soll` / `ist` | setpoint / measured | `vorlauf` / `ruecklauf` | flow / return |
| `raumtemp` | room temperature | `aussentemp` | outdoor temperature |
| `heizen` / `absenken` | comfort (heat) / setback | `heizgrenze` | heating limit (outdoor) |
| `heizkurve` | heating curve | `steigung` / `fusspunkt` | slope / base point |
| `ueberhoehung` | overshoot above a setpoint | `hyst`, `hysterese` | hysteresis |
| `kessel` | boiler | `brennerkontakt` | burner contact |
| `mischer` | mixing valve | `pumpe` | pump |
| `pumpenfreigabe` | pump release (temperature) | `nachlaufzeit` | pump overrun time |
| `einschaltfuehler` / `ausschaltfuehler` | start / stop sensor | `fuehler` | sensor |
| `speicher` | storage tank | `kollektor` | solar collector |
| `umschaltventil` | diverting valve | `fernb`, `fernbedienung` | remote control (room unit) |
| `betriebsart` | operating mode | `zeitprogramm` | schedule |
| `tag` / `zeitreihe` | day / time slot | `frostschutz` | frost protection |
| `solarheiz` | solar discharge (surplus to the house) | `kuehlen` | cooling |
| `ein` / `aus` | on (start) / off (stop) | `vorhanden` | present (installed) |
| `estrich` | screed drying program | `ertrag` | yield (energy meter) |

## Values

- **Scale.** A portal value is `value / divisor`; temperatures usually have a divisor of 10 (`225` = 22.5 °C). On the local interface the factor is in `all?`; writes use the raw value (`hk1_temp_heat=225`).
- **Options.** A value of type `options` is an index into a list of state texts (`formatTexts` on the portal, `format` in `all?`). The texts come from the controller in its language; the integration downloads them and does not store them.
- **Clock times** (`time`, `simpletime`) are `HHMM` as a number: `1830` = 18:30.
- **Status words** (`L_…status`) are bit fields: several states at once (see below).

## Modes

`hk[n].betriebsart[1]` (local `hkN.mode_auto`) is the heating circuit's mode, `ww[n].betriebsart[1]` (local `wwN.mode_auto`) the hot water's:

| Value | Heating circuit | Hot water |
|---|---|---|
| 0 | off | off |
| 1 | auto (schedule) | auto (schedule) |
| 2 | comfort | forced on |
| 3 | setback | |

Eco mode `oekomode` (heating and hot water): 0 off, 1 comfort, 2 intermediate (heating) / minimum (hot water), 3 ecological. When the forecast is sunny, it lowers the room setpoint by 0.5 / 1 / 1.5 K, or the hot water target by 5 / 10 / 15 K.

`anlage_betriebsart` is the summer / winter switch of the Touch: 1 = heating and hot water (winter), 2 = hot water only (summer); 0 stops the whole plant (the integration does not offer it).

## Status bits

*Observed* on the buffer tank `L_pu[n].status` and the hot water `L_ww[n].status`:

| Group | Bit | Meaning |
|---|---|---|
| buffer | `0x100` | asks the boiler (demand on) |
| buffer | `0x200` | does not ask (demand off) |
| buffer | `0x10` | pump overrun |
| buffer | `0x40` | boiler below the pump release temperature |
| buffer | `0x80` | boiler below its low limit |
| hot water | `0x4000` | asks the boiler (demand on) |
| hot water | `0x2000` | demand off |
| hot water | `0x10` / `0x8` | inside / outside the schedule |
| hot water | `0x800` | anti-seize or frost run of the pump |

The solar boost uses the two *demand on* bits to know when the boiler is asked even if the burner contact is not readable.

**Buffer setpoint.** *Observed:* the buffer setpoint `L_pu[n].einschaltfuehler_soll` is the heating flow setpoint plus `hk[n].ueberhoehung`; the boiler is asked when the top of the buffer is below it, and released when the middle sensor is above it. Lowering the heating curve lowers the buffer setpoint, and so the boiler starts.

## Schedules

`hk[n].zeitprogramm[p].tag[d].zeitreihe[i]` (and `ww[n]…`): program `p`, day `d` (0 = Monday, *observed*), slot `i`. `hk[n].aktives_zeitprogramm` picks the program (0 = program 1).

A slot is one number: start and end as `HHMM`, after a leading digit; `107001800` reads 1 · 0700 · 1800, 07:00 to 18:00. *Observed:* the leading digit groups days edited together (1 weekdays, 2 weekend, 3 a single day); a negative value seems to mark a setback slot. Read a schedule with the portal's own page before writing one.

## Sensor calibration

Each sensor has an offset (±15 K) on the Touch, in the general menu at technician level (*sensor calibration*). The room unit's sensor sits in the wall-mounted screen and can read high when the screen is warm: compare it with a thermometer nearby over a day before changing the offset. Ask your installer for the technician access.

## Settings the integration writes

Only the settings listed in the [README](https://github.com/lenoxys/ha-oekofen-portal#settings-you-can-change), within safe bounds, plus the thermostats and the hot water. Safety settings (collector protection, maximum boiler temperatures) are not written. The [variable reference](variables.md) marks them with *set*.
