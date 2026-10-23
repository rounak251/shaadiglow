"""Indicative monthly climate bands for popular Indian wedding cities.

Hand-encoded, rounded bands from public climate summaries (not a forecast):
  humidity  D dry (<45% mean RH) | M moderate | H humid (>65%)
  temp      C cool (<18 C mean)  | M mild     | W warm | H hot (>30 C)
  uv        H high (6-7)         | V very high (8-10) | E extreme (11+)
Twelve characters per string = Jan..Dec.  `smog` lists the winter months when
Indo-Gangetic cities usually report poor air quality.
"""
from __future__ import annotations

from datetime import date

CITIES = {
    "mumbai":     dict(name="Mumbai", hi="मुंबई", hum="MMMHHHHHHHMM", temp="MMWWWWWWWWWM", uv="VVEEEVVVVVVV", smog=[]),
    "delhi":      dict(name="Delhi NCR", hi="दिल्ली एनसीआर", hum="HMMDDMHHMMMH", temp="CCMWHHHWWWMC", uv="HHVEEEVVVVHH", smog=[10, 11, 12, 1]),
    "bengaluru":  dict(name="Bengaluru", hi="बेंगलुरु", hum="MMMMMHHHHHHM", temp="MMWWWMMMMMMM", uv="VEEEEVVVVVVV", smog=[]),
    "chennai":    dict(name="Chennai", hi="चेन्नई", hum="HHHHMMMMHHHH", temp="WWWHHHHWWWWW", uv="VEEEEEEEEVVV", smog=[]),
    "kolkata":    dict(name="Kolkata", hi="कोलकाता", hum="MMMHHHHHHHMM", temp="MMWHHWWWWWMM", uv="HVVEEEVVVVHH", smog=[12, 1]),
    "hyderabad":  dict(name="Hyderabad", hi="हैदराबाद", hum="MDDDDMHHHMMM", temp="MWWHHWWWWWMM", uv="VVEEEEVVVVVV", smog=[]),
    "pune":       dict(name="Pune", hi="पुणे", hum="MDDDDHHHHMMM", temp="MMWWWWMMMMMM", uv="VVEEEVVVVVVV", smog=[]),
    "ahmedabad":  dict(name="Ahmedabad", hi="अहमदाबाद", hum="DDDDDMHHHMDD", temp="MWWHHHWWWWWM", uv="HVVEEEVVVVHH", smog=[]),
    "jaipur":     dict(name="Jaipur", hi="जयपुर", hum="MDDDDDHHMDDD", temp="CMMWHHWWWWMC", uv="HVVEEEVVVVHH", smog=[11, 12]),
    "udaipur":    dict(name="Udaipur", hi="उदयपुर", hum="MDDDDMHHMDDD", temp="CMMWHHWWWWMC", uv="HVVEEEVVVVHH", smog=[]),
    "lucknow":    dict(name="Lucknow", hi="लखनऊ", hum="HMDDDMHHHMMH", temp="CMMWHHWWWWMC", uv="HHVEEEVVVVHH", smog=[11, 12, 1]),
    "varanasi":   dict(name="Varanasi", hi="वाराणसी", hum="HMDDDMHHHMMH", temp="CMMWHHWWWWMC", uv="HHVEEEVVVVHH", smog=[11, 12, 1]),
    "patna":      dict(name="Patna", hi="पटना", hum="HMDDMHHHHHMH", temp="CMMWHHWWWWMC", uv="HHVEEEVVVVHH", smog=[11, 12, 1]),
    "chandigarh": dict(name="Chandigarh", hi="चंडीगढ़", hum="HMMDDMHHHMMH", temp="CCMWHHWWWMMC", uv="HHVVEEVVVVHH", smog=[11, 12]),
    "kochi":      dict(name="Kochi", hi="कोच्चि", hum="HHHHHHHHHHHH", temp="WWWWWWWWWWWW", uv="VEEEEVVVVVVV", smog=[]),
    "goa":        dict(name="Goa", hi="गोवा", hum="MMHHHHHHHHHM", temp="WWWWWWWWWWWW", uv="VVEEEVVVVVVV", smog=[]),
}

HUM = {"D": "dry", "M": "moderate", "H": "humid"}
TEMP = {"C": "cool", "M": "mild", "W": "warm", "H": "hot"}
UV = {"H": "high", "V": "very high", "E": "extreme"}


def bands(city: str, when: date) -> dict:
    c = CITIES.get(city, CITIES["delhi"])
    i = when.month - 1
    hum, temp, uv = HUM[c["hum"][i]], TEMP[c["temp"][i]], UV[c["uv"][i]]
    # Cold air holds little water and heaters dry skin further: treat cool months as "dry" for the barrier.
    skin_air = "dry" if (hum == "dry" or temp == "cool") else ("humid" if hum == "humid" else "moderate")
    return {"city": city, "name": c["name"], "name_hi": c["hi"], "month": when.strftime("%b"), "month_num": when.month,
            "humidity": hum,
            "temp": temp, "uv": uv, "smog": when.month in c["smog"], "skin_air": skin_air}


def city_list() -> list[dict]:
    return [{"id": k, "name": v["name"], "hi": v["hi"]} for k, v in CITIES.items()]
