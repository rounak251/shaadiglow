"""SAMPLE catalogue: fictional, unbranded products with indicative Indian prices (INR).

Nothing here is a real brand or a real offer.  Makeup items carry the exact
YouCam Makeup VTO effect they render with, so "try on" and "add to cart" are the
same object; jewellery items carry the reference image sent to the 2D VTO APIs.
"""
from __future__ import annotations

TIERS = {"essential": {"label": "₹", "cap": 2500}, "balanced": {"label": "₹₹", "cap": 5500},
         "premium": {"label": "₹₹₹", "cap": 11000}}


def P(id, name, cat, slot, price, size, tier, *, ing=(), texture=None, concerns=(), art=None, vto=None,
      hi=None, note=None, role=("bride", "groom", "guest")):
    return {"id": id, "name": name, "name_hi": hi, "category": cat, "slot": slot, "price": price, "size": size,
            "tier": tier, "ingredients": list(ing), "texture": texture, "concerns": list(concerns),
            "art": art or {}, "vto": vto, "note": note, "roles": list(role)}


SKINCARE = [
    P("cl_gel", "Gentle Gel Cleanser", "Cleanser", "cleanser", 349, "100 ml", "essential", texture="gel",
      concerns=["oiliness"], art={"shape": "tube", "color": "#CFE8E4", "accent": "#2F7D73"}),
    P("cl_cream", "Ceramide Cream Cleanser", "Cleanser", "cleanser", 399, "100 ml", "essential", texture="cream",
      ing=["ceramides"], concerns=["moisture", "redness"], art={"shape": "tube", "color": "#F4E6D8", "accent": "#A0643C"}),
    P("cl_bha", "Salicylic 2% Face Wash", "Cleanser", "cleanser", 449, "100 ml", "essential", texture="gel",
      ing=["salicylic_acid"], concerns=["acne", "oiliness", "pore"], art={"shape": "tube", "color": "#DDE7F7", "accent": "#3558A8"}),
    P("cl_balm", "Cleansing Balm (removes sunscreen & makeup)", "Cleanser", "first_cleanse", 699, "90 g", "balanced",
      texture="balm", art={"shape": "jar", "color": "#F6E3C6", "accent": "#C7892C"}),
    P("se_nia", "Niacinamide 5% + Zinc Serum", "Serum", "serum", 549, "30 ml", "essential",
      ing=["niacinamide"], concerns=["oiliness", "pore", "acne", "age_spot", "redness"],
      art={"shape": "dropper", "color": "#EDEFF3", "accent": "#5B6FA8"}),
    P("se_vitc", "Vitamin C 10% Brightening Serum", "Serum", "serum_am", 799, "30 ml", "balanced",
      ing=["vitamin_c"], concerns=["radiance", "age_spot", "dark_circle_v2"],
      art={"shape": "dropper", "color": "#FBE3B5", "accent": "#E08A1E"}),
    P("se_vitc_lux", "Stabilised Vitamin C 15% + Ferulic Serum", "Serum", "serum_am", 1499, "30 ml", "premium",
      ing=["vitamin_c"], concerns=["radiance", "age_spot"], art={"shape": "dropper", "color": "#F7D08A", "accent": "#B4651A"}),
    P("se_aza", "Azelaic Acid 10% Gel", "Treatment", "treatment", 699, "30 g", "balanced",
      ing=["azelaic_acid"], concerns=["redness", "age_spot", "acne"], art={"shape": "tube", "color": "#F1E8F4", "accent": "#7D4B8E"}),
    P("se_bha", "Salicylic Acid 2% Serum", "Treatment", "treatment", 599, "30 ml", "essential",
      ing=["salicylic_acid"], concerns=["acne", "pore", "oiliness"], art={"shape": "dropper", "color": "#E3ECF9", "accent": "#2F5FA8"}),
    P("se_lactic", "Lactic Acid 5% Gentle Exfoliant", "Treatment", "treatment", 649, "30 ml", "balanced",
      ing=["lactic_acid"], concerns=["texture", "radiance"], art={"shape": "dropper", "color": "#F9EDEA", "accent": "#C0645A"}),
    P("se_retinol", "Retinol 0.3% Night Serum", "Treatment", "treatment", 999, "30 ml", "balanced",
      ing=["retinol"], concerns=["wrinkle", "texture", "pore"], art={"shape": "dropper", "color": "#EDE3F7", "accent": "#5E3A8C"}),
    P("se_ha", "Hyaluronic Acid 2% Hydrating Serum", "Serum", "hydrator", 499, "30 ml", "essential",
      ing=["hyaluronic_acid"], concerns=["moisture"], art={"shape": "dropper", "color": "#E2F1FB", "accent": "#2B86C5"}),
    P("se_arbutin", "Alpha Arbutin 2% Spot Serum", "Serum", "serum", 599, "30 ml", "essential",
      ing=["alpha_arbutin"], concerns=["age_spot"], art={"shape": "dropper", "color": "#F6F1E7", "accent": "#9C7A3C"}),
    P("se_cica", "Cica Calming Serum", "Serum", "serum", 649, "30 ml", "balanced",
      ing=["centella"], concerns=["redness"], art={"shape": "dropper", "color": "#E4F2E6", "accent": "#3E8A52"}),
    P("se_peptide", "Peptide Firming Serum", "Serum", "serum", 1199, "30 ml", "premium",
      ing=["peptides"], concerns=["wrinkle"], art={"shape": "pump", "color": "#EFE7F1", "accent": "#7A4E7E"}),
    P("ey_caff", "Caffeine 5% Eye Serum", "Eye care", "eye", 549, "15 ml", "essential",
      ing=["caffeine"], concerns=["eye_bag", "dark_circle_v2"], art={"shape": "roller", "color": "#EAE4DE", "accent": "#6B4B34"}),
    P("ey_lux", "Brightening Eye Cream", "Eye care", "eye", 1099, "15 g", "premium",
      ing=["caffeine", "niacinamide"], concerns=["dark_circle_v2", "eye_bag"], art={"shape": "jar", "color": "#F3ECE3", "accent": "#9B6B3D"}),
    P("mo_gel", "Oil-free Gel Moisturiser", "Moisturiser", "moisturiser", 399, "50 g", "essential", texture="gel",
      ing=["hyaluronic_acid"], concerns=["oiliness", "moisture"], art={"shape": "jar", "color": "#DFF1EE", "accent": "#2F7D73"}),
    P("mo_lotion", "Lightweight Daily Lotion", "Moisturiser", "moisturiser", 449, "75 ml", "essential",
      texture="lotion", concerns=["moisture"], art={"shape": "pump", "color": "#F5EFE6", "accent": "#8A6A45"}),
    P("mo_cream", "Ceramide Barrier Cream", "Moisturiser", "moisturiser", 599, "50 g", "balanced", texture="cream",
      ing=["ceramides"], concerns=["moisture", "redness"], art={"shape": "jar", "color": "#F7EADB", "accent": "#A0643C"}),
    P("mo_night", "Overnight Repair Cream", "Moisturiser", "night", 899, "50 g", "premium", texture="cream",
      ing=["ceramides", "peptides"], concerns=["moisture", "wrinkle"], art={"shape": "jar", "color": "#E9E1F2", "accent": "#5E3A8C"}),
    P("ss_gel", "Gel Sunscreen SPF 50 PA++++", "Sunscreen", "sunscreen", 499, "50 g", "essential", texture="gel",
      ing=["sunscreen"], concerns=["age_spot", "radiance"], art={"shape": "tube", "color": "#FFF1C7", "accent": "#E09A12"}),
    P("ss_fluid", "Ultra-light Fluid Sunscreen SPF 50 PA++++", "Sunscreen", "sunscreen", 749, "50 ml", "balanced",
      texture="fluid", ing=["sunscreen"], concerns=["age_spot"], art={"shape": "bottle", "color": "#FFE9B8", "accent": "#D9840C"}),
    P("ss_cream", "Hydrating Cream Sunscreen SPF 50", "Sunscreen", "sunscreen", 549, "50 g", "essential", texture="cream",
      ing=["sunscreen", "ceramides"], concerns=["moisture"], art={"shape": "tube", "color": "#FFF4DE", "accent": "#C7892C"}),
    P("ss_tinted", "Tinted Mineral Sunscreen SPF 50", "Sunscreen", "sunscreen", 899, "40 ml", "premium",
      texture="fluid", ing=["sunscreen"], concerns=["redness", "age_spot"], art={"shape": "tube", "color": "#E8C1A0", "accent": "#8A5A3A"}),
    P("mk_clay", "Kaolin Clay Mask", "Mask", "weekly", 449, "100 g", "essential",
      ing=["clay"], concerns=["oiliness", "pore"], art={"shape": "jar", "color": "#E7E3DA", "accent": "#6E6A5E"}),
    P("mk_sheet", "Hydrating Sheet Masks (pack of 3)", "Mask", "weekly", 299, "3 masks", "essential",
      ing=["hyaluronic_acid"], concerns=["moisture", "radiance"], art={"shape": "sachet", "color": "#E3F0FA", "accent": "#2B86C5"}),
    P("sp_patch", "Hydrocolloid Pimple Patches", "Spot care", "spot", 249, "36 patches", "essential",
      ing=["hydrocolloid"], concerns=["acne"], art={"shape": "box", "color": "#F3F4F6", "accent": "#3A6EA5"}),
    P("sp_bp", "Benzoyl Peroxide 2.5% Spot Gel", "Spot care", "spot", 299, "20 g", "essential",
      ing=["benzoyl_peroxide"], concerns=["acne"], art={"shape": "tube", "color": "#FDEDED", "accent": "#B03A3A"},
      note="Bleaches fabric: keep it away from your wedding outfit, towels and pillow covers."),
    P("lp_balm", "Lip Repair Balm", "Lip care", "lip", 199, "10 g", "essential", concerns=["moisture"],
      art={"shape": "stick", "color": "#F6D7D2", "accent": "#B4505A"}),
    P("bl_paper", "Oil Blotting Papers", "Wedding-day kit", "kit", 149, "100 sheets", "essential",
      concerns=["oiliness"], art={"shape": "box", "color": "#F6EAD6", "accent": "#C7892C"}),
    P("pr_matte", "Mattifying Primer", "Wedding-day kit", "primer", 699, "30 ml", "balanced",
      concerns=["oiliness", "pore"], art={"shape": "tube", "color": "#EFE6EE", "accent": "#7A4E7E"}),
    P("pr_glow", "Hydrating Glow Primer", "Wedding-day kit", "primer", 699, "30 ml", "balanced",
      concerns=["moisture", "radiance"], art={"shape": "tube", "color": "#FBEBD9", "accent": "#C77A2C"}),
    P("st_spray", "Long-wear Setting Spray", "Wedding-day kit", "kit", 799, "100 ml", "balanced",
      art={"shape": "bottle", "color": "#E6EEF5", "accent": "#43698F"}),
    P("gr_beardoil", "Softening Beard Oil", "Grooming", "beard", 399, "30 ml", "essential",
      art={"shape": "dropper", "color": "#F2E2C8", "accent": "#7A4B1E"}, role=("groom",)),
    P("gr_beardwash", "Beard & Face Wash", "Grooming", "beard", 349, "100 ml", "essential",
      art={"shape": "tube", "color": "#E2E8E6", "accent": "#2F5B55"}, role=("groom",)),
    P("gr_aftershave", "Alcohol-free Soothing Aftershave Balm", "Grooming", "beard", 399, "75 ml", "essential",
      concerns=["redness"], art={"shape": "tube", "color": "#E8F1F4", "accent": "#2D6E86"}, role=("groom",)),
]

FOUNDATION_SHADES = [  # name, hex (used for the VTO foundation + concealer colour)
    ("Porcelain 110", "#F1D3BE"), ("Ivory 120", "#E8C3A6"), ("Light Beige 210", "#DDB08D"),
    ("Warm Sand 230", "#D2A07A"), ("Honey 310", "#C08A60"), ("Caramel 330", "#AE774E"),
    ("Almond 410", "#93613D"), ("Espresso 510", "#6E4429"),
]


def _lip(id, name, hexc, texture, price, tier="balanced"):
    vto = {"category": "lip_color", "shape": {"name": "original"}, "style": {"type": "full"},
           "palettes": [{"color": hexc, "texture": texture, "colorIntensity": 80}]}
    if texture in ("gloss", "sheer", "shimmer", "holographic", "metallic"):
        vto["palettes"][0]["gloss"] = 60
    if texture in ("gloss", "sheer", "shimmer"):
        vto["palettes"][0]["transparencyIntensity"] = 35
    if texture in ("shimmer", "holographic", "metallic"):
        vto["palettes"][0].update({"shimmerColor": "#F6D38A", "shimmerIntensity": 40, "shimmerDensity": 40,
                                   "shimmerSize": 30})
    return P(id, name, "Lipstick", "lip", price, "4 g", tier, art={"shape": "lipstick", "color": hexc}, vto=vto)


MAKEUP = [
    _lip("lip_sindoor", "Sindoor Red Matte Lipstick", "#B3132B", "matte", 599),
    _lip("lip_wine", "Wine Velvet Lipstick", "#7A1F2E", "matte", 599),
    _lip("lip_coral", "Haldi Coral Satin Lipstick", "#E2654F", "satin", 499, "essential"),
    _lip("lip_nude", "Nude Rose Gloss", "#C47A7A", "gloss", 449, "essential"),
    _lip("lip_mauve", "Mauve Muse Satin Lipstick", "#A05A6E", "satin", 549),
    _lip("lip_terracotta", "Terracotta Matte Lipstick", "#A8442E", "matte", 549),
    _lip("lip_berry", "Berry Glow Lip Tint", "#8E2A4D", "sheer", 399, "essential"),
    _lip("lip_balm_tint", "Tinted Lip Balm (natural)", "#B97F72", "sheer", 299, "essential"),
    P("kajal_black", "Smudge-proof Kajal", "Eyes", "eyes", 249, "0.35 g", "essential",
      art={"shape": "pencil", "color": "#141414"},
      vto={"category": "eye_liner", "pattern": {"name": "Arabic3"},
           "palettes": [{"color": "#111111", "texture": "matte", "colorIntensity": 85}]}),
    P("kohl_brown", "Soft Brown Kohl", "Eyes", "eyes", 299, "0.35 g", "essential",
      art={"shape": "pencil", "color": "#4A2C1E"},
      vto={"category": "eye_liner", "pattern": {"name": "Arabic3"},
           "palettes": [{"color": "#4A2C1E", "texture": "matte", "colorIntensity": 70}]}),
    P("mascara", "Volume Mascara", "Eyes", "eyes", 449, "8 ml", "essential",
      art={"shape": "mascara", "color": "#151515"},
      vto={"category": "eyelashes", "pattern": {"name": "Natural1"},
           "palettes": [{"color": "#111111", "colorIntensity": 80}]}),
    P("pal_gold", "Gold Dust Eyeshadow Trio", "Eyes", "eyes", 899, "3 x 1.5 g", "balanced",
      art={"shape": "palette", "colors": ["#C9A04B", "#6E4A2E", "#3B2618"]},
      vto={"category": "eye_shadow", "pattern": {"name": "3colors1"}, "palettes": [
          {"color": "#C9A04B", "texture": "shimmer", "colorIntensity": 70, "shimmerColor": "#F6D38A",
           "shimmerIntensity": 60},
          {"color": "#6E4A2E", "texture": "matte", "colorIntensity": 60},
          {"color": "#3B2618", "texture": "matte", "colorIntensity": 55}]}),
    P("pal_rose", "Rose Gold Eyeshadow Trio", "Eyes", "eyes", 899, "3 x 1.5 g", "balanced",
      art={"shape": "palette", "colors": ["#E8C2A8", "#C98B7A", "#9E5F55"]},
      vto={"category": "eye_shadow", "pattern": {"name": "3colors1"}, "palettes": [
          {"color": "#E8C2A8", "texture": "shimmer", "colorIntensity": 65, "shimmerColor": "#F8E1C8",
           "shimmerIntensity": 60},
          {"color": "#C98B7A", "texture": "matte", "colorIntensity": 60},
          {"color": "#9E5F55", "texture": "matte", "colorIntensity": 55}]}),
    P("pal_plum", "Smoky Plum Eyeshadow Trio", "Eyes", "eyes", 899, "3 x 1.5 g", "balanced",
      art={"shape": "palette", "colors": ["#C79FB0", "#7D4B63", "#4A2A3A"]},
      vto={"category": "eye_shadow", "pattern": {"name": "3colors1"}, "palettes": [
          {"color": "#C79FB0", "texture": "shimmer", "colorIntensity": 60, "shimmerColor": "#EBD3DF",
           "shimmerIntensity": 50},
          {"color": "#7D4B63", "texture": "matte", "colorIntensity": 65},
          {"color": "#4A2A3A", "texture": "matte", "colorIntensity": 60}]}),
    P("pal_bronze", "Bronze Olive Eyeshadow Trio", "Eyes", "eyes", 799, "3 x 1.5 g", "balanced",
      art={"shape": "palette", "colors": ["#A57C3C", "#7A6A3A", "#4E4A2C"]},
      vto={"category": "eye_shadow", "pattern": {"name": "3colors1"}, "palettes": [
          {"color": "#A57C3C", "texture": "metallic", "colorIntensity": 65, "shimmerColor": "#E6C27A",
           "shimmerIntensity": 55, "metallicIntensity": 50},
          {"color": "#7A6A3A", "texture": "matte", "colorIntensity": 60},
          {"color": "#4E4A2C", "texture": "matte", "colorIntensity": 55}]}),
    P("blush_peach", "Peach Cheek Tint", "Face", "cheeks", 449, "5 g", "essential",
      art={"shape": "compact", "color": "#E9967A"},
      vto={"category": "blush", "pattern": {"name": "1color1"},
           "palettes": [{"color": "#E9967A", "texture": "matte", "colorIntensity": 45}]}),
    P("blush_rose", "Rose Blush", "Face", "cheeks", 499, "5 g", "balanced",
      art={"shape": "compact", "color": "#D8707C"},
      vto={"category": "blush", "pattern": {"name": "1color1"},
           "palettes": [{"color": "#D8707C", "texture": "satin", "glowStrength": 40, "colorIntensity": 45}]}),
    P("blush_berry", "Berry Blush", "Face", "cheeks", 499, "5 g", "balanced",
      art={"shape": "compact", "color": "#B4566A"},
      vto={"category": "blush", "pattern": {"name": "1color1"},
           "palettes": [{"color": "#B4566A", "texture": "matte", "colorIntensity": 40}]}),
    P("hl_champagne", "Champagne Glow Highlighter", "Face", "glow", 599, "6 g", "balanced",
      art={"shape": "compact", "color": "#F3DDB3"},
      vto={"category": "highlighter", "pattern": {"name": "OvalFace2"},
           "palettes": [{"color": "#F3DDB3", "glowIntensity": 60, "shimmerIntensity": 50, "shimmerDensity": 50,
                         "shimmerSize": 40, "colorIntensity": 50}]}),
    P("hl_golden", "Golden Hour Highlighter", "Face", "glow", 599, "6 g", "balanced",
      art={"shape": "compact", "color": "#E9C27A"},
      vto={"category": "highlighter", "pattern": {"name": "OvalFace2"},
           "palettes": [{"color": "#E9C27A", "glowIntensity": 65, "shimmerIntensity": 55, "shimmerDensity": 50,
                         "shimmerSize": 45, "colorIntensity": 55}]}),
    P("contour_soft", "Soft Contour Stick", "Face", "contour", 549, "6 g", "balanced",
      art={"shape": "stick", "color": "#8C5A3C"},
      vto={"category": "contour", "pattern": {"name": "OvalFace6"},
           "palettes": [{"color": "#8C5A3C", "colorIntensity": 35}]}),
    P("concealer_peach", "Peach Colour Corrector", "Face", "concealer", 449, "6 ml", "essential",
      art={"shape": "wand", "color": "#E9A07D"},
      vto={"category": "concealer", "palettes": [{"color": "#E9A07D", "colorIntensity": 55,
                                                  "colorUnderEyeIntensity": 60, "coverageLevel": 55}]}),
]

FOUNDATIONS = [
    P(f"found_{i}", f"Long-wear Foundation · {name}", "Face", "base", 799, "30 ml", "balanced",
      art={"shape": "bottle", "color": hexc},
      vto={"category": "foundation", "palettes": [{"color": hexc, "colorIntensity": 30, "glowIntensity": 40,
                                                   "coverageIntensity": 50}]})
    for i, (name, hexc) in enumerate(FOUNDATION_SHADES)
]

HAIR = [
    P("hair_burgundy", "Burgundy Wine Hair Colour", "Hair colour", "hair", 549, "kit", "essential",
      art={"shape": "box", "color": "#5E1528", "accent": "#E9C27A"}, vto={"preset": "Burgundy"}),
    P("hair_choco", "Chocolate Brown Hair Colour", "Hair colour", "hair", 549, "kit", "essential",
      art={"shape": "box", "color": "#4B2E22", "accent": "#E9C27A"}, vto={"preset": "Chocolate Brown"}),
    P("hair_copper", "Copper Glow Hair Colour", "Hair colour", "hair", 549, "kit", "essential",
      art={"shape": "box", "color": "#9A3E1F", "accent": "#F3DDB3"}, vto={"preset": "Copper Red"}),
    P("hair_caramel", "Caramel Balayage Kit", "Hair colour", "hair", 899, "kit", "balanced",
      art={"shape": "box", "color": "#A86F3A", "accent": "#3A2418"}, vto={"preset": "Dark Brown/Caramel Blonde"}),
    P("hair_black", "Natural Jet Black Hair Colour", "Hair colour", "hair", 449, "kit", "essential",
      art={"shape": "box", "color": "#16110F", "accent": "#C9A04B"}, vto={"preset": "Jet Black"}),
]

JEWELLERY = [
    P("jhumka_gold", "Gold-tone Temple Jhumkas", "Jewellery", "earring", 1499, "pair", "balanced",
      art={"shape": "image", "src": "/static/jewellery/jhumka_gold.png"},
      vto={"kind": "earring", "ref": "jhumka_gold_ref.jpg"}, role=("bride", "guest")),
    P("chandbali_kundan", "Kundan Chandbalis", "Jewellery", "earring", 2199, "pair", "premium",
      art={"shape": "image", "src": "/static/jewellery/chandbali_kundan.png"},
      vto={"kind": "earring", "ref": "chandbali_kundan_ref.jpg"}, role=("bride", "guest")),
    P("polki_studs", "Polki Flower Studs", "Jewellery", "earring", 999, "pair", "essential",
      art={"shape": "image", "src": "/static/jewellery/polki_studs.png"},
      vto={"kind": "earring", "ref": "polki_studs_ref.jpg"}, role=("bride", "guest")),
    P("pearl_jhumki", "Silver Pearl Jhumkis", "Jewellery", "earring", 1299, "pair", "balanced",
      art={"shape": "image", "src": "/static/jewellery/pearl_jhumki.png"},
      vto={"kind": "earring", "ref": "pearl_jhumki_ref.jpg"}, role=("bride", "guest")),
    P("kundan_choker", "Kundan Choker Necklace", "Jewellery", "necklace", 3999, "piece", "premium",
      art={"shape": "image", "src": "/static/jewellery/kundan_choker.png"},
      vto={"kind": "necklace", "ref": "kundan_choker_ref.jpg"}, role=("bride", "guest")),
    P("temple_haar", "Temple-style Gold-tone Haar", "Jewellery", "necklace", 4499, "piece", "premium",
      art={"shape": "image", "src": "/static/jewellery/temple_haar.png"},
      vto={"kind": "necklace", "ref": "temple_haar_ref.jpg"}, role=("bride", "guest")),
    P("pearl_layers", "Layered Pearl Necklace", "Jewellery", "necklace", 2799, "piece", "balanced",
      art={"shape": "image", "src": "/static/jewellery/pearl_layers.png"},
      vto={"kind": "necklace", "ref": "pearl_layers_ref.jpg"}, role=("bride", "guest")),
]

PRODUCTS = {p["id"]: p for p in SKINCARE + MAKEUP + FOUNDATIONS + HAIR + JEWELLERY}


def get(pid: str) -> dict:
    return PRODUCTS[pid]


def public() -> list[dict]:
    return list(PRODUCTS.values())


def shade_for(rgb: tuple[float, float, float]) -> dict:
    """Nearest foundation shade to an average cheek colour (simple Lab distance)."""
    def lab(c):
        r, g, b = [x / 255.0 for x in c]
        r, g, b = [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in (r, g, b)]
        X = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
        Y = (r * 0.2126 + g * 0.7152 + b * 0.0722)
        Z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
        f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
        return (116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z)))
    target = lab(rgb)
    best = min(FOUNDATIONS, key=lambda p: sum((a - b) ** 2 for a, b in zip(
        lab(tuple(int(p["art"]["color"][i:i + 2], 16) for i in (1, 3, 5))), target)))
    return best
