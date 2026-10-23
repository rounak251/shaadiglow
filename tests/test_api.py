"""HTTP API in mock mode: the whole journey plus input hardening."""
import io

from PIL import Image

from app.mock.personas import variant_bytes


def test_full_bride_journey(app_client):
    c = app_client
    cfg = c.get("/api/config").json()
    assert cfg["mode"] == "mock" and len(cfg["personas"]) == 3 and cfg["costs"]
    r = c.post("/api/scan", json={"image_ref": "persona:ananya", "profile_id": "test-profile-123"}).json()
    assert r["units_charged"] == 14 and r["api"] == "AI Skin Analysis"
    scan = r["scan"]
    assert c.get(scan["concerns"][0]["mask"]).status_code == 200
    plan = c.post("/api/plan", json={"scan": scan, "wedding_date": "2026-12-20", "city": "mumbai",
                                     "today": "2026-10-23"}).json()
    assert plan["days_left"] == 58 and plan["phases"]
    ics = c.post("/api/plan.ics", json={"scan": scan, "wedding_date": "2026-12-20", "city": "mumbai",
                                        "today": "2026-10-23"})
    assert ics.headers["content-type"].startswith("text/calendar") and "BEGIN:VEVENT" in ics.text
    shade = c.post("/api/shade", json={"image_ref": "persona:ananya"}).json()
    mk = c.post("/api/tryon/makeup", json={"image_ref": "persona:ananya", "look_id": "pheras_red",
                                           "shade_id": shade["product"]}).json()
    assert mk["units_charged"] == 1 and c.get(mk["url"]).status_code == 200 and "lip_sindoor" in mk["products"]
    again = c.post("/api/tryon/makeup", json={"image_ref": "persona:ananya", "look_id": "pheras_red",
                                              "shade_id": shade["product"]}).json()
    assert again["cached"] and again["units_charged"] == 0
    assert c.post("/api/tryon/hair", json={"image_ref": "persona:ananya", "product_id": "hair_burgundy"}).status_code == 200
    j = c.post("/api/tryon/jewellery", json={"image_ref": "persona:meera", "product_id": "kundan_choker"}).json()
    assert j["api"] == "AI Necklace Virtual Try-On"
    sim = c.post("/api/simulate", json={"image_ref": "persona:ananya", "focus": ["oiliness", "radiance"]}).json()
    assert sim["units_charged"] == 4 and set(sim["params"]) == {"oiliness", "radiance"}
    units = c.get("/api/units").json()
    assert units["spent"] == 14 + 1 + 1 + 1 + 4


def test_groom_beard_and_progress(app_client):
    c = app_client
    tpl = c.get("/api/tryon/beard/templates").json()["templates"]
    b = c.post("/api/tryon/beard", json={"image_ref": "persona:arjun", "template_id": tpl[0]["id"]}).json()
    assert b["units_charged"] == 2
    assert c.post("/api/tryon/beard", json={"image_ref": "persona:arjun", "template_id": "x"}).status_code == 404
    prog = c.get("/api/demo/progress/arjun").json()
    assert prog["latest"]["units_charged"] == 9 and len(prog["tracked"]) == 4
    assert prog["compare"]["rows"] and "noise_band" in prog["compare"]


def test_upload_scan_and_delete(app_client):
    c = app_client
    face = variant_bytes("meera", "face")
    r = c.post("/api/photo", files={"face": ("f.jpg", face, "image/jpeg")}, data={"source": "upload"}).json()
    ref = r["image_ref"]
    assert ref.startswith("upload:") and c.get(r["urls"]["portrait"]).status_code == 200
    s = c.post("/api/scan", json={"image_ref": ref, "profile_id": "pid-12345678"}).json()
    assert s["scan"]["concerns"]
    q = c.post("/api/scan", json={"image_ref": ref, "profile_id": "pid-12345678", "kind": "quick",
                                  "concerns": ["acne", "pore"]}).json()
    assert q["units_charged"] == 9
    prof = c.get("/api/profile/pid-12345678").json()
    assert len(prof["scans"]) == 2 and "compare" in prof
    d = c.post("/api/profile/pid-12345678/delete").json()
    assert d["youcam_tasks_deleted"] == 2 and d["uploads_deleted"] == 1
    assert c.get(r["urls"]["face"]).status_code == 404


def test_rejects_bad_input(app_client):
    c = app_client
    assert c.post("/api/scan", json={"image_ref": "upload:../../etc/passwd"}).status_code == 400
    assert c.post("/api/scan", json={"image_ref": "persona:ananya", "kind": "quick"}).status_code == 400
    assert c.get("/media/mock/..%2F..%2Fapp/main.py").status_code == 404
    b = io.BytesIO()
    Image.new("RGB", (200, 200)).save(b, "PNG")
    r = c.post("/api/photo", files={"face": ("tiny.png", b.getvalue(), "image/png")})
    assert r.status_code == 400 and "small" in r.json()["message"]
    r = c.post("/api/photo", files={"face": ("x.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 400
    assert c.post("/api/tryon/makeup", json={"image_ref": "persona:ananya", "look_id": "nope"}).status_code == 404
    assert c.post("/api/plan", json={"scan": {}, "wedding_date": "2026-12-01", "city": "atlantis"}).status_code == 400


def test_index_and_static(app_client):
    assert "ShaadiGlow" in app_client.get("/").text
    assert app_client.get("/static/js/app.js").status_code == 200
    assert app_client.get("/manifest.webmanifest").status_code == 200
