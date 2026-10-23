"""Explainable skincare knowledge base used by the countdown planner.

Cosmetic, over-the-counter guidance only (no prescription drugs).  Every rule has
an id so the UI can show *why* a step is in the plan.  Timings reflect common
dermatology advice for event prep: actives need weeks to work; nothing new in
the last two weeks; stop retinoids about a week before and exfoliating acids
about five days before; threading/waxing 3-4 days out.
"""
from __future__ import annotations

# targets: concern -> strength (1 weak .. 3 strong)
INGREDIENTS: dict[str, dict] = {
    "niacinamide": dict(
        name={"en": "Niacinamide 5%", "hi": "नियासिनामाइड 5%"},
        targets={"oiliness": 3, "pore": 2, "age_spot": 2, "redness": 1, "acne": 1},
        when="am_pm", min_days=21, stop_before=0, exfoliant=False, preg_ok=True, sensitive_ok=True,
        how={"en": "2-3 drops after cleansing, morning and night.", "hi": "क्लींज़िंग के बाद 2-3 बूँदें, सुबह और रात।"},
        evidence={"en": "Regulates oil and evens tone; visible change in about 4-8 weeks.",
                  "hi": "तेल नियंत्रित करता है और रंगत एक-सी करता है; 4-8 हफ़्ते में असर दिखता है।"}),
    "salicylic_acid": dict(
        name={"en": "Salicylic acid 2% (BHA)", "hi": "सैलिसिलिक एसिड 2% (BHA)"},
        targets={"acne": 3, "pore": 3, "oiliness": 2, "texture": 1},
        when="pm", min_days=21, stop_before=5, exfoliant=True, preg_ok=False, sensitive_ok=False,
        how={"en": "3 nights a week, then alternate nights.", "hi": "हफ़्ते में 3 रात, फिर एक दिन छोड़कर।"},
        evidence={"en": "Oil-soluble exfoliant that clears inside pores.",
                  "hi": "तेल में घुलने वाला एक्सफ़ोलिएंट जो रोमछिद्रों के अंदर तक साफ़ करता है।"}),
    "azelaic_acid": dict(
        name={"en": "Azelaic acid 10%", "hi": "एज़ेलेइक एसिड 10%"},
        targets={"redness": 3, "age_spot": 2, "acne": 2},
        when="pm", min_days=28, stop_before=3, exfoliant=False, preg_ok=True, sensitive_ok=True,
        how={"en": "Pea-sized amount at night; may tingle for the first week.",
             "hi": "रात में मटर जितनी मात्रा; पहले हफ़्ते हल्की झनझनाहट हो सकती है।"},
        evidence={"en": "Calms redness and fades marks; gentle enough for sensitive skin.",
                  "hi": "लालिमा शांत करता है और निशान हल्के करता है; संवेदनशील त्वचा के लिए भी।"}),
    "vitamin_c": dict(
        name={"en": "Vitamin C 10-15%", "hi": "विटामिन C 10-15%"},
        targets={"radiance": 3, "age_spot": 2, "dark_circle_v2": 1},
        when="am", min_days=28, stop_before=0, exfoliant=False, preg_ok=True, sensitive_ok=True,
        how={"en": "Mornings, before moisturiser and sunscreen.", "hi": "सुबह, मॉइस्चराइज़र और सनस्क्रीन से पहले।"},
        evidence={"en": "Antioxidant that boosts glow and helps sunscreen against pigmentation.",
                  "hi": "एंटीऑक्सीडेंट जो चमक बढ़ाता है और सनस्क्रीन के साथ पिगमेंटेशन से बचाता है।"}),
    "alpha_arbutin": dict(
        name={"en": "Alpha arbutin 2%", "hi": "अल्फ़ा आर्बुटिन 2%"},
        targets={"age_spot": 3},
        when="am_pm", min_days=42, stop_before=0, exfoliant=False, preg_ok=False, sensitive_ok=True,
        how={"en": "On dark spots, twice a day.", "hi": "काले धब्बों पर, दिन में दो बार।"},
        evidence={"en": "Slows pigment production; needs 6+ weeks.",
                  "hi": "पिगमेंट बनना धीमा करता है; 6+ हफ़्ते चाहिए।"}),
    "lactic_acid": dict(
        name={"en": "Lactic acid 5% (gentle AHA)", "hi": "लैक्टिक एसिड 5% (हल्का AHA)"},
        targets={"texture": 3, "radiance": 2},
        when="pm", min_days=21, stop_before=7, exfoliant=True, preg_ok=False, sensitive_ok=False,
        how={"en": "2 nights a week, never on the same night as other acids.",
             "hi": "हफ़्ते में 2 रात, दूसरे एसिड वाली रात नहीं।"},
        evidence={"en": "Smooths texture so makeup sits flat.", "hi": "बनावट चिकनी करता है ताकि मेकअप अच्छे से बैठे।"}),
    "retinol": dict(
        name={"en": "Retinol 0.3%", "hi": "रेटिनॉल 0.3%"},
        targets={"wrinkle": 3, "texture": 2, "pore": 1, "acne": 1},
        when="pm", min_days=60, stop_before=7, exfoliant=True, preg_ok=False, sensitive_ok=False,
        how={"en": "2 nights a week for 2 weeks, then alternate nights.", "hi": "2 हफ़्ते तक हफ़्ते में 2 रात, फिर एक दिन छोड़कर।"},
        evidence={"en": "Renews skin, but can peel for 2-4 weeks: only worth it with 8+ weeks to go.",
                  "hi": "त्वचा नई करता है, पर 2-4 हफ़्ते छिलका उतर सकता है: 8+ हफ़्ते बचे हों तभी।"}),
    "hyaluronic_acid": dict(
        name={"en": "Hyaluronic acid", "hi": "हायल्यूरोनिक एसिड"},
        targets={"moisture": 3, "radiance": 1},
        when="am_pm", min_days=3, stop_before=0, exfoliant=False, preg_ok=True, sensitive_ok=True,
        how={"en": "On damp skin, then seal with moisturiser.", "hi": "हल्की गीली त्वचा पर, फिर मॉइस्चराइज़र लगाएँ।"},
        evidence={"en": "Pulls water into the skin for an instant plump look.",
                  "hi": "त्वचा में नमी खींचता है, तुरंत भरी-भरी दिखती है।"}),
    "centella": dict(
        name={"en": "Centella asiatica (cica)", "hi": "सेंटेला (सिका)"},
        targets={"redness": 2, "moisture": 1},
        when="am_pm", min_days=7, stop_before=0, exfoliant=False, preg_ok=True, sensitive_ok=True,
        how={"en": "Morning and night after cleansing.", "hi": "क्लींज़िंग के बाद सुबह-रात।"},
        evidence={"en": "Soothes a stressed barrier.", "hi": "तनावग्रस्त त्वचा को शांत करता है।"}),
    "caffeine": dict(
        name={"en": "Caffeine eye serum", "hi": "कैफ़ीन आई सीरम"},
        targets={"eye_bag": 3, "dark_circle_v2": 2},
        when="am_pm", min_days=14, stop_before=0, exfoliant=False, preg_ok=True, sensitive_ok=True,
        how={"en": "Pat under the eyes; keep it in the fridge for extra de-puffing.",
             "hi": "आँखों के नीचे थपथपाएँ; फ़्रिज में रखें तो सूजन और कम।"},
        evidence={"en": "Constricts vessels to reduce puffiness.", "hi": "सूजन कम करने में मदद करता है।"}),
    "peptides": dict(
        name={"en": "Peptides", "hi": "पेप्टाइड्स"},
        targets={"wrinkle": 2, "moisture": 1},
        when="am_pm", min_days=42, stop_before=0, exfoliant=False, preg_ok=True, sensitive_ok=True,
        how={"en": "Twice daily under moisturiser.", "hi": "मॉइस्चराइज़र से पहले दिन में दो बार।"},
        evidence={"en": "Gentle option for fine lines when retinol is off the table.",
                  "hi": "रेटिनॉल न ले पाएँ तो महीन रेखाओं के लिए हल्का विकल्प।"}),
}

# Copy for the rules the planner fires.  {placeholders} are filled at plan time.
RULES: dict[str, dict] = {
    "R-FOCUS": {"en": "{concern} scored {ui}/100, one of your lowest: it gets a targeted active.",
                "hi": "{concern} का स्कोर {ui}/100 है, सबसे कम में से: इसके लिए खास एक्टिव।"},
    "R-TIME-SKIP": {"en": "{ingredient} needs about {need} days to show results; you have {days}. Skipped.",
                    "hi": "{ingredient} को असर दिखाने में लगभग {need} दिन लगते हैं; आपके पास {days} हैं। छोड़ा गया।"},
    "R-PREG": {"en": "{ingredient} is left out because you marked pregnancy/breastfeeding. Ask your doctor before any active.",
               "hi": "गर्भावस्था/स्तनपान चुना है, इसलिए {ingredient} नहीं। कोई भी एक्टिव लेने से पहले डॉक्टर से पूछें।"},
    "R-SENSITIVE": {"en": "{ingredient} is left out for sensitive skin; we use gentler options.",
                    "hi": "संवेदनशील त्वचा के लिए {ingredient} नहीं; हल्के विकल्प चुने गए।"},
    "R-ONE-EXFOLIANT": {"en": "Only one exfoliating active at a time, so {ingredient} waits.",
                        "hi": "एक समय में एक ही एक्सफ़ोलिएंट, इसलिए {ingredient} अभी नहीं।"},
    "R-BUDGET": {"en": "Your {tier} budget fits {n} actives; {ingredient} would go over.",
                 "hi": "आपके {tier} बजट में {n} एक्टिव आते हैं; {ingredient} बजट से बाहर।"},
    "R-HUMID": {"en": "{city} in {month} is humid: gel textures and a gel sunscreen won't feel heavy.",
                "hi": "{month} में {city} नम रहता है: जेल टेक्सचर और जेल सनस्क्रीन भारी नहीं लगेंगे।"},
    "R-DRY": {"en": "{city} in {month} is dry or cool: a ceramide cream protects your barrier.",
              "hi": "{month} में {city} रूखा या ठंडा रहता है: सेरामाइड क्रीम त्वचा की परत बचाती है।"},
    "R-UV": {"en": "UV in {city} is {uv} in {month}: SPF 50 PA++++ every morning, reapply outdoors every 2-3 hours.",
             "hi": "{month} में {city} का UV {uv} है: रोज़ सुबह SPF 50 PA++++, बाहर हों तो हर 2-3 घंटे में दोबारा।"},
    "R-SEASON": {"en": "{city} turns {air} from {month}: switch to the {texture} moisturiser then.",
                 "hi": "{month} से {city} {air} हो जाता है: तब {texture} मॉइस्चराइज़र पर बदलें।"},
    "R-SMOG": {"en": "Winter smog season in {city}: cleanse twice at night to lift pollution and sunscreen.",
               "hi": "{city} में सर्दियों का स्मॉग: रात में दो बार क्लींज़ करें ताकि प्रदूषण और सनस्क्रीन हटें।"},
    "R-SKINTYPE": {"en": "Your skin type reads {type} (T-zone {tz}), so we pick {texture} textures.",
                   "hi": "आपकी त्वचा {type} है (टी-ज़ोन {tz}), इसलिए {texture} टेक्सचर।"},
    "R-NO-NEW": {"en": "No new products in the last 14 days: a reaction now has no time to settle.",
                 "hi": "आख़िरी 14 दिनों में कोई नया प्रोडक्ट नहीं: अब कोई रिएक्शन हुआ तो ठीक होने का समय नहीं।"},
    "R-STOP-RETINOL": {"en": "Stop retinol 7 days before: no peeling or sensitivity under bridal makeup.",
                       "hi": "रेटिनॉल 7 दिन पहले बंद: दुल्हन के मेकअप के नीचे छिलका या जलन नहीं।"},
    "R-STOP-ACIDS": {"en": "Stop exfoliating acids 5 days before, and never around threading or waxing.",
                     "hi": "एक्सफ़ोलिएटिंग एसिड 5 दिन पहले बंद, और थ्रेडिंग/वैक्सिंग के आसपास कभी नहीं।"},
    "R-PATCH": {"en": "Patch-test every new product behind the ear for 48 hours; add one product at a time.",
                "hi": "हर नया प्रोडक्ट 48 घंटे कान के पीछे पैच-टेस्ट करें; एक बार में एक ही जोड़ें।"},
    "R-HENNA": {"en": "Mehendi: use natural henna only; 'black henna' can contain PPD, which causes severe reactions.",
                "hi": "मेहंदी: सिर्फ़ प्राकृतिक मेहंदी; 'काली मेहंदी' में PPD हो सकता है, जिससे गंभीर रिएक्शन होता है।"},
    "R-HALDI": {"en": "Haldi: turmeric can dry and stain; rinse with a gentle cleanser and moisturise after.",
                "hi": "हल्दी: हल्दी रूखापन और दाग़ छोड़ सकती है; हल्के क्लींज़र से धोएँ और मॉइस्चराइज़ करें।"},
    "R-BP-FABRIC": {"en": "Benzoyl peroxide bleaches fabric: keep it away from your outfit, towels and pillow covers.",
                    "hi": "बेंज़ॉयल पेरॉक्साइड कपड़े का रंग उड़ाता है: पोशाक, तौलिये और तकिये से दूर रखें।"},
    "R-KEEP-BASICS": {"en": "Already using a gentle cleanser, moisturiser and SPF that suit you? Keep them: only the actives are new.",
                      "hi": "पहले से कोई हल्का क्लींज़र, मॉइस्चराइज़र और SPF सूट करता है? वही रखें: सिर्फ़ एक्टिव नए हैं।"},
    "R-RESCUE": {"en": "With under 2 weeks left we don't start actives: hydrate, protect, sleep and spot-treat.",
                 "hi": "2 हफ़्ते से कम बचे हैं, इसलिए कोई नया एक्टिव नहीं: नमी, सुरक्षा, नींद और स्पॉट-केयर।"},
}

DISCLAIMER = {
    "en": "Cosmetic guidance, not a medical diagnosis. See a dermatologist for painful, persistent or spreading acne, "
          "sudden pigmentation, or any reaction.",
    "hi": "यह सौंदर्य सलाह है, चिकित्सा निदान नहीं। दर्द वाले, लगातार या फैलते मुंहासे, अचानक पिगमेंटेशन या किसी "
          "रिएक्शन के लिए त्वचा विशेषज्ञ से मिलें।",
}
