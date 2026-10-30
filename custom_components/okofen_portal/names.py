"""Readable names and descriptions (English, French) for the controller's German variable names.

Does not import Home Assistant. Words that are not in the glossary, or whose meaning is not certain,
are kept as they are rather than guessed.
"""

from __future__ import annotations

import re

from .catalog import group_of, pretty

# word (lower case) -> (English, French); "" drops the word
GLOSSARY: dict[str, tuple[str, str]] = {
    "abgastemperatur": ("flue gas temperature", "température des fumées"),
    "absenken": ("setback", "réduit"),
    "act": ("actual", "mesure"),
    "actheatpumpctrlerrors": ("heat pump controller errors", "erreurs du contrôleur de pompe à chaleur"),
    "actheatpumpstate": ("heat pump state", "état de la pompe à chaleur"),
    "actheatpumpsubstate": ("heat pump sub-state", "sous-état de la pompe à chaleur"),
    "actspeedcompressor": ("compressor speed", "vitesse du compresseur"),
    "activate": ("activate", "activer"),
    "agt": ("flue gas", "fumées"),
    "aktuell": ("current", "actuel"),
    "alterkessel": ("old boiler", "ancienne chaudière"),
    "amplitude": ("amplitude", "amplitude"),
    "analogeingang": ("analog input", "entrée analogique"),
    "anforderung": ("request", "demande"),
    "angeschlossen": ("connected", "raccordé"),
    "anlage": ("plant", "installation"),
    "anstroemdifferenz": ("inflow difference", "écart du fluide entrant"),
    "anstroemtemp": ("inflow temperature", "température du fluide entrant"),
    "anzeige": ("display", "affichage"),
    "asche": ("ash", "cendres"),
    "aschemenge": ("ash amount", "quantité de cendres"),
    "ascheschnecke": ("ash auger", "vis à cendres"),
    "aufzeichnung": ("recording", "enregistrement"),
    "aus": ("off", "arrêt"),
    "ausschaltfuehler": ("switch-off sensor", "sonde d'arrêt"),
    "aussentemperatur": ("outdoor temperature", "température extérieure"),
    "available": ("available", "disponible"),
    "avg": ("average", "moyenne"),
    "backup": ("backup", "secours"),
    "batt": ("battery", "batterie"),
    "bestke": ("existing boiler", "chaudière existante"),
    "betriebsart": ("operating mode", "mode de fonctionnement"),
    "bms": ("BMS", "BMS"),
    "br": ("burner", "brûleur"),
    "brennerkontakt": ("burner contact", "contact brûleur"),
    "brennerlaufzeit": ("burner runtime", "durée de marche du brûleur"),
    "brennerstarts": ("burner starts", "démarrages du brûleur"),
    "bsk": ("fire damper", "clapet coupe-feu"),
    "cancel": ("cancel", "annulation"),
    "car": ("car", "véhicule"),
    "cell": ("cell", "cellule"),
    "charge": ("charge", "charge"),
    "chargenow": ("charge now", "charger maintenant"),
    "chg": ("charge", "charge"),
    "clouds": ("clouds", "nuages"),
    "comfort": ("comfort", "confort"),
    "connectionstate": ("connection state", "état de la connexion"),
    "coolant": ("coolant", "liquide de refroidissement"),
    "current": ("current", "courant"),
    "data": ("data", "données"),
    "dcv": ("DC voltage", "tension continue"),
    "debug": ("debug", "débogage"),
    "defrost": ("defrost", "dégivrage"),
    "device": ("device", "appareil"),
    "dischg": ("discharge", "décharge"),
    "doquittallalarms": ("acknowledge all alarms", "acquitter toutes les alarmes"),
    "drehzahl": ("speed", "vitesse"),
    "drive": ("drive", "entraînement"),
    "durchfluss": ("flow", "débit"),
    "durchflussmenge": ("flow rate", "débit"),
    "ein": ("on", "marche"),
    "einschaltfuehler": ("switch-on sensor", "sonde de marche"),
    "einschublaufzeit": ("feed runtime", "durée d'alimentation"),
    "elect": ("electric", "électrique"),
    "enabled": ("enabled", "activé"),
    "end": ("end", "fin"),
    "endschalter": ("limit switch", "fin de course"),
    "energy": ("energy", "énergie"),
    "error": ("error", "erreur"),
    "exist": ("exists", "existe"),
    "exists": ("exists", "existe"),
    "expect": ("expected", "attendu"),
    "fehler": ("error", "erreur"),
    "fehlermeldung": ("error message", "message d'erreur"),
    "feuerraumtemperatur": ("combustion chamber temperature", "température du foyer"),
    "firmwareversion": ("firmware version", "version du micrologiciel"),
    "flammueb": ("flame monitor", "contrôle de flamme"),
    "flow": ("flow", "débit"),
    "folgewechsel": ("sequence change", "changement de séquence"),
    "force": ("forced", "forcé"),
    "forecast": ("forecast", "prévision"),
    "freigabetemp": ("release temperature", "température de libération"),
    "freq": ("frequency", "fréquence"),
    "frequency": ("frequency", "fréquence"),
    "frequenz": ("frequency", "fréquence"),
    "fuehler": ("sensor", "sonde"),
    "fuellstand": ("fill level", "niveau de remplissage"),
    "fusspunkt": ("base point", "pied de courbe"),
    "gen": ("generator", "générateur"),
    "gesamt": ("total", "total"),
    "graph": ("graph", "graphique"),
    "green": ("green", "vert"),
    "greenmode": ("green mode", "mode vert"),
    "greenstate": ("green state", "état vert"),
    "grid": ("grid", "réseau"),
    "gueltig": ("valid", "valide"),
    "hardwareversion": ("hardware version", "version matérielle"),
    "heat": ("heat", "chaleur"),
    "heater": ("heater", "résistance chauffante"),
    "heating": ("heating", "chauffage"),
    "heatpumps": ("heat pumps", "pompes à chaleur"),
    "heizen": ("heating", "chauffage"),
    "heizgrenze": ("heating limit", "limite de chauffage"),
    "heizkurve": ("heating curve", "courbe de chauffe"),
    "heute": ("today", "aujourd'hui"),
    "hp": ("heat pump", "pompe à chaleur"),
    "hyst": ("hysteresis", "hystérésis"),
    "in": ("in", "entrée"),
    "info": ("info", "info"),
    "injection": ("injection", "injection"),
    "interne": ("internal", "interne"),
    "ist": ("actual", "mesure"),
    "kap": ("capacitive", "capacitif"),
    "kaskade": ("cascade", "cascade"),
    "ke": ("existing boiler", "chaudière existante"),
    "kessel": ("boiler", "chaudière"),
    "kesselstatus": ("boiler status", "état de la chaudière"),
    "kesseltemperatur": ("boiler temperature", "température de la chaudière"),
    "kollektortemp": ("collector temperature", "température des capteurs"),
    "komforttemp": ("comfort temperature", "température de confort"),
    "l": ("", ""),
    "laufzeit": ("runtime", "durée de marche"),
    "leistung": ("power", "puissance"),
    "limit": ("limit", "limite"),
    "load": ("load", "charge"),
    "logdata": ("log data", "données du journal"),
    "loglevel": ("log level", "niveau de journalisation"),
    "luefterdrehzahl": ("fan speed", "vitesse du ventilateur"),
    "max": ("max", "max"),
    "min": ("min", "min"),
    "mischer": ("mixing valve", "vanne mélangeuse"),
    "mittlere": ("average", "moyenne"),
    "mode": ("mode", "mode"),
    "model": ("model", "modèle"),
    "modulationsstufe": ("modulation level", "niveau de modulation"),
    "neu": ("new", "nouveau"),
    "offset": ("offset", "décalage"),
    "once": ("once", "une fois"),
    "online": ("online", "en ligne"),
    "out": ("out", "sortie"),
    "party": ("", ""),
    "pausenzeit": ("pause time", "temps de pause"),
    "pe": ("pellet boiler", "chaudière à granulés"),
    "peak": ("peak", "pic"),
    "pelletsfuellstand": ("pellet level", "niveau de granulés"),
    "pfad": ("path", "chemin"),
    "phase": ("phase", "phase"),
    "phasenverschiebung": ("phase shift", "déphasage"),
    "power": ("power", "puissance"),
    "powermeter": ("power meter", "compteur électrique"),
    "price": ("price", "prix"),
    "pump": ("pump", "pompe"),
    "pumpe": ("pump", "pompe"),
    "purchase": ("purchase", "achat"),
    "pv": ("PV", "photovoltaïque"),
    "pwr": ("power", "puissance"),
    "quellenanforderung": ("source request", "demande de source"),
    "raumentnahme": ("room extraction", "extraction depuis le local"),
    "raumtemp": ("room temperature", "température de la pièce"),
    "reload": ("reload", "rechargement"),
    "reloadhc": ("reload heating circuit", "rechargement du circuit de chauffage"),
    "reloadwp": ("reload heat pump", "rechargement de la pompe à chaleur"),
    "remain": ("remaining", "restant"),
    "reorganize": ("reorganize", "réorganisation"),
    "report": ("report", "rapport"),
    "reserve": ("reserve", "réserve"),
    "reset": ("reset", "réinitialisation"),
    "rest": ("rest", "reste"),
    "rfid": ("RFID", "RFID"),
    "ruecklauf": ("return", "retour"),
    "ruecklauftemp": ("return temperature", "température de retour"),
    "ruecksetzen": ("reset", "réinitialiser"),
    "sauganlage": ("suction system", "système d'aspiration"),
    "saugintervall": ("suction interval", "intervalle d'aspiration"),
    "saugsonde": ("suction probe", "sonde d'aspiration"),
    "saugzugdrehzahl": ("induced draft fan speed", "vitesse du ventilateur d'extraction"),
    "schnecke": ("auger", "vis"),
    "sensor": ("sensor", "sonde"),
    "session": ("session", "session"),
    "set": ("setpoint", "consigne"),
    "sicherheitsabschaltungen": ("safety shutdowns", "arrêts de sécurité"),
    "sillstandszeit": ("standstill time", "temps d'arrêt"),
    "since": ("since", "depuis"),
    "single": ("single", "simple"),
    "smartpvgreenmode": ("smart PV green mode", "mode vert PV intelligent"),
    "soc": ("state of charge", "état de charge"),
    "soh": ("state of health", "état de santé"),
    "solarheiz": ("solar discharge", "décharge solaire"),
    "soll": ("setpoint", "consigne"),
    "sollabweichungen": ("setpoint deviations", "écarts de consigne"),
    "spannung": ("voltage", "tension"),
    "speed": ("speed", "vitesse"),
    "speichertemp": ("tank temperature", "température du ballon"),
    "sperrzeit": ("lockout time", "temps de blocage"),
    "st": ("Stirling", "Stirling"),
    "start": ("start", "démarrage"),
    "starts": ("starts", "démarrages"),
    "state": ("state", "état"),
    "statetext": ("state text", "texte d'état"),
    "status": ("status", "état"),
    "steigung": ("slope", "pente"),
    "step": ("step", "pas"),
    "stick": ("stick", "clé"),
    "stirling": ("Stirling", "Stirling"),
    "stopp": ("stop", "arrêt"),
    "strom": ("current", "courant"),
    "switch": ("switch", "commutateur"),
    "system": ("system", "système"),
    "temp": ("temperature", "température"),
    "therm": ("thermal", "thermique"),
    "third": ("third-party", "tiers"),
    "thyristor": ("thyristor", "thyristor"),
    "time": ("time", "heure"),
    "tmp": ("temperature", "température"),
    "today": ("today", "aujourd'hui"),
    "total": ("total", "total"),
    "ueberhoehung": ("overshoot", "surélévation"),
    "umgebungstemp": ("ambient temperature", "température ambiante"),
    "umschaltventil": ("changeover valve", "vanne d'inversion"),
    "unterdruck": ("negative pressure", "dépression"),
    "update": ("update", "mise à jour"),
    "usage": ("usage", "utilisation"),
    "usb": ("USB", "USB"),
    "value": ("value", "valeur"),
    "voltage": ("voltage", "tension"),
    "vorhanden": ("present", "présent"),
    "vorlauftemp": ("flow temperature", "température de départ"),
    "weather": ("weather", "météo"),
    "wirkleistung": ("active power", "puissance active"),
    "wp": ("heat pump", "pompe à chaleur"),
    "wpheater": ("heat pump heater", "résistance de la pompe à chaleur"),
    "wrcurrent": ("inverter current", "courant de l'onduleur"),
    "year": ("year", "année"),
    "zuend": ("ignition", "allumage"),
    "zwischenbehaelter": ("intermediate hopper", "trémie intermédiaire"),
}
SUFFIXES = {"ist", "soll", "act", "set"}  # shown in brackets after the name: "Room temperature (actual)"

# group kind -> (English label, French label, English description, French description)
GROUPS: dict[str, tuple[str, str, str, str]] = {
    "hk": ("Heating circuit", "Circuit de chauffage",
           "Heating circuit: pump, mixing valve, flow and room temperatures, heating curve and solar discharge settings.",
           "Circuit de chauffage : pompe, vanne mélangeuse, températures de départ et d'ambiance, courbe de chauffe et réglages de décharge solaire."),
    "ww": ("Hot water", "Eau chaude",
           "Domestic hot water circuit: sensors, pump and solar discharge settings.",
           "Circuit d'eau chaude sanitaire : sondes, pompe et réglages de décharge solaire."),
    "pu": ("Buffer tank", "Ballon tampon",
           "Buffer tank: temperature sensors, loading pump and request to the boiler.",
           "Ballon tampon : sondes de température, pompe de charge et demande à la chaudière."),
    "sk": ("Solar circuit", "Circuit solaire",
           "Solar circuit: collector and tank temperatures, pump and status.",
           "Circuit solaire : températures des capteurs et du ballon, pompe et état."),
    "boiler": ("Existing boiler", "Chaudière existante",
               "Back-up boiler (oil, gas...) driven by the controller: temperature, burner contact and pump/valve output.",
               "Chaudière d'appoint (fioul, gaz...) pilotée par la régulation : température, contact brûleur et sortie pompe/vanne."),
    "weather": ("Weather", "Météo",
                "Weather data and forecast used by the controller to anticipate sunny days.",
                "Données météo et prévisions utilisées par la régulation pour anticiper les jours ensoleillés."),
    "fa": ("Pellet boiler", "Chaudière à granulés",
           "Pellet boiler: combustion, fans, augers and fill levels. Empty on installations without a pellet boiler.",
           "Chaudière à granulés : combustion, ventilateurs, vis et niveaux. Sans valeur si l'installation n'en a pas."),
    "ertrag": ("Solar yield", "Gain solaire", "Solar heat meter.", "Compteur de chaleur solaire."),
    "heater": ("Heater", "Résistance", "Electric heating element.", "Résistance électrique."),
    "batt": ("Battery", "Batterie", "Battery storage.", "Stockage par batterie."),
    "car": ("Charging station", "Borne de recharge", "Electric vehicle charging station.", "Borne de recharge de véhicule électrique."),
    "p2h": ("Power2heat", "Power2heat", "Power2heat: surplus electricity turned into heat.", "Power2heat : surplus électrique transformé en chaleur."),
    "wp": ("Heat pump", "Pompe à chaleur", "Heat pump.", "Pompe à chaleur."),
    "zirkp": ("Circulation pump", "Pompe de circulation", "Hot water circulation pump.", "Pompe de bouclage d'eau chaude."),
    "zubrp": ("Feed pump", "Pompe d'alimentation", "Feed pump.", "Pompe d'alimentation."),
    "lambda": ("Lambda sensor", "Sonde lambda", "Lambda (oxygen) sensor.", "Sonde lambda (oxygène)."),
    "system": ("Controller", "Régulation",
               "The controller: outdoor temperature, plant mode (summer / winter), errors and general values.",
               "La régulation : température extérieure, mode de l'installation (été / hiver), erreurs et valeurs générales."),
}

# specific explanations (English, French) for the variables that matter most
DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "LOCAL.L_ke_brennerkontakt_1": ("Burner request sent by the controller to the existing boiler. On = the burner is running.", "Demande de brûleur envoyée par la régulation à la chaudière existante. Marche = le brûleur tourne."),
    "LOCAL.L_ke_temp_ist": ("Temperature measured by the existing boiler's sensor (terminal X13).", "Température mesurée par la sonde de la chaudière existante (borne X13)."),
    "LOCAL.L_ke_temp_soll": ("Setpoint of the existing boiler (8 °C = no request).", "Consigne de la chaudière existante (8 °C = aucune demande)."),
    "LOCAL.L_bestke_umschaltventil": ("Dry contact (terminal X24) that starts the existing boiler's pump or changeover valve.", "Contact sec (borne X24) qui commande la pompe ou la vanne d'inversion de la chaudière existante."),
    "LOCAL.L_hk[0].mischer": ("Mixing valve of the heating circuit: stopped, opening or closing. Three-point control, there is no position feedback.", "Vanne mélangeuse du circuit de chauffage : arrêt, ouverture ou fermeture. Commande 3 points, sans retour de position."),
    "LOCAL.L_hk[0].vorlauftemp_ist": ("Heating flow temperature measured after the mixing valve.", "Température de départ du chauffage mesurée après la vanne mélangeuse."),
    "LOCAL.L_hk[0].vorlauftemp_soll": ("Heating flow temperature wanted. The buffer setpoint is this value plus the overshoot setting. 8 °C = heating off.", "Température de départ du chauffage demandée. La consigne du ballon vaut cette valeur plus la surélévation. 8 °C = chauffage arrêté."),
    "LOCAL.L_hk[0].raumtemp_ist": ("Room temperature measured by the room unit.", "Température de la pièce mesurée par la sonde d'ambiance."),
    "LOCAL.L_hk[0].raumtemp_soll": ("Room temperature wanted at this moment (comfort or setback, remote offset and eco mode included).", "Température de pièce demandée à cet instant (confort ou réduit, décalage de télécommande et mode écolo compris)."),
    "LOCAL.L_hk[0].pumpe": ("Heating circuit pump.", "Pompe du circuit de chauffage."),
    "LOCAL.L_pu[0].einschaltfuehler_ist": ("Buffer tank, top sensor (switch-on sensor): the boiler is requested when it falls below its setpoint.", "Ballon tampon, sonde haute (sonde de marche) : la chaudière est demandée quand elle passe sous sa consigne."),
    "LOCAL.L_pu[0].ausschaltfuehler_ist": ("Buffer tank, middle sensor (switch-off sensor): the boiler stops when it reaches its setpoint.", "Ballon tampon, sonde milieu (sonde d'arrêt) : la chaudière s'arrête quand elle atteint sa consigne."),
    "LOCAL.L_pu[0].pumpe": ("Buffer tank loading pump, in %.", "Pompe de charge du ballon tampon, en %."),
    "LOCAL.L_ww[0].einschaltfuehler_ist": ("Hot water switch-on sensor (the highest sensor of the buffer tank).", "Sonde de marche de l'eau chaude (la sonde la plus haute du ballon)."),
    "LOCAL.L_sk[0].kollektortemp_ist": ("Solar collector temperature.", "Température des capteurs solaires."),
    "LOCAL.L_sk[0].speichertemp_ist": ("Temperature at the bottom of the tank, where the solar coil is.", "Température en bas du ballon, là où se trouve la spirale solaire."),
    "LOCAL.L_sk[0].pumpe": ("Solar circuit pump speed, in %.", "Vitesse de la pompe du circuit solaire, en %."),
    "LOCAL.L_aussentemperatur_ist": ("Outdoor temperature used by the controller.", "Température extérieure utilisée par la régulation."),
    # settings
    "LOCAL.hk[0].solarheiz_temp_ein": ("Solar discharge: starts when the top of the buffer reaches this temperature and sun is forecast.", "Décharge solaire : démarre quand le haut du ballon atteint cette température et que du soleil est prévu."),
    "LOCAL.hk[0].solarheiz_temp_aus": ("Solar discharge: stops when the buffer falls below this temperature, which keeps a hot water reserve.", "Décharge solaire : s'arrête quand le ballon passe sous cette température, ce qui garde une réserve d'eau chaude."),
    "LOCAL.hk[0].solarheiz_mode": ("Schedule = follows the time program. Solar pump = only while the solar pump is running.", "Programme = suit le programme horaire. Pompe solaire = seulement pendant que la pompe solaire tourne."),
    "LOCAL.ww[0].solarheiz_temp_ein": ("Solar discharge towards hot water: start temperature.", "Décharge solaire vers l'eau chaude : température de démarrage."),
    "LOCAL.ww[0].solarheiz_temp_aus": ("Solar discharge towards hot water: stop temperature.", "Décharge solaire vers l'eau chaude : température d'arrêt."),
    "LOCAL.hk[0].ueberhoehung": ("The buffer setpoint is the flow setpoint plus this margin. Lowering it delays the boiler.", "La consigne du ballon vaut la consigne de départ plus cette marge. La baisser retarde la chaudière."),
    "LOCAL.hk[0].vorlauftemp_max": ("Highest flow temperature the heating circuit may ask for (and so the buffer setpoint minus the overshoot).", "Température de départ maximale que le circuit peut demander (donc la consigne du ballon moins la surélévation)."),
    "LOCAL.hk[0].vorlauftemp_min": ("Lowest flow temperature of the heating circuit.", "Température de départ minimale du circuit de chauffage."),
    "LOCAL.hk[0].heizkurve_fusspunkt": ("Flow temperature at 15 °C outdoors; changing it shifts the whole curve.", "Température de départ à 15 °C dehors ; la modifier décale toute la courbe."),
    "LOCAL.hk[0].heizkurve_steigung": ("Change of the flow temperature for each degree of outdoor temperature.", "Variation de la température de départ pour chaque degré de température extérieure."),
    "LOCAL.hk[0].heizgrenze_heizen": ("During comfort periods, heating is cut above this average outdoor temperature.", "En période de confort, le chauffage est coupé au-dessus de cette température extérieure moyenne."),
    "LOCAL.hk[0].heizgrenze_absenken": ("During setback periods, heating is cut above this average outdoor temperature.", "En période de réduit, le chauffage est coupé au-dessus de cette température extérieure moyenne."),
    "LOCAL.anlage_betriebsart": ("Winter = heating and hot water. Summer = hot water only.", "Hiver = chauffage et eau chaude. Été = eau chaude seule."),
}

_LANG = {"en": 0, "fr": 1}


def _index(lang: str) -> int:
    return _LANG.get(lang, 0)


def _parse_group(group_id: str) -> tuple[str, int | None]:
    match = re.fullmatch(r"([a-z0-9]+?)(\d+)", group_id)
    return (match.group(1), int(match.group(2))) if match else (group_id, None)


def group_title(group_id: str, lang: str) -> str:
    """'hk0' -> 'Heating circuit 1' / 'Circuit de chauffage 1'."""
    kind, index = _parse_group(group_id)
    label = GROUPS.get(kind, (kind.title(),) * 2)[_index(lang)]
    return label if index is None else f"{label} {index + 1}"


def group_description(group_id: str, lang: str) -> str:
    """Short explanation of what the group of entities is."""
    kind, _ = _parse_group(group_id)
    entry = GROUPS.get(kind)
    return entry[2 + _index(lang)] if entry else ""


def friendly_name(key: str, lang: str) -> str:
    """'LOCAL.L_hk[0].raumtemp_ist' -> 'Room temperature (actual)'."""
    words = re.findall(r"[A-Za-z]+|\d+", pretty(key))
    suffix = ""
    if words and words[-1].lower() in SUFFIXES and len(words) > 1:
        suffix = GLOSSARY[words.pop().lower()][_index(lang)]
    parts = []
    for word in words:
        entry = GLOSSARY.get(word.lower())
        text = entry[_index(lang)] if entry else (word.upper() if word.isalpha() and len(word) <= 3 else word)
        if text:
            parts.append(text)
    name = " ".join(parts) or key
    if suffix:
        name += f" ({suffix})"
    return name[0].upper() + name[1:]


def entity_description(key: str, lang: str) -> str:
    """The specific explanation if there is one, otherwise 'Group: name'."""
    if key in DESCRIPTIONS:
        return DESCRIPTIONS[key][_index(lang)]
    return f"{group_title(group_of(key)[0], lang)}: {friendly_name(key, lang)}"


def build_names(keys: list[str], lang: str) -> dict[str, str]:
    """Names unique inside each group: duplicates get the controller's variable name appended."""
    names = {key: friendly_name(key, lang) for key in keys}
    seen: dict[tuple[str, str], list[str]] = {}
    for key, name in names.items():
        seen.setdefault((group_of(key)[0], name), []).append(key)
    for (_, name), same in seen.items():
        if len(same) > 1:
            for key in same:
                names[key] = f"{name} [{pretty(key)}]"
    return names
