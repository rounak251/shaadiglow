"""The mock layer must speak exactly the documented YouCam contract.

Docs examples live in fixtures/docs/ (copied verbatim from the API reference);
every mock response is checked against their structure, and the real client is
exercised end to end against the simulator.
"""
import asyncio

import httpx
import pytest

from app.engine.concerns import normalise
from app.mock.personas import variant_bytes
from app.youcam.client import YouCamClient, result_urls
from app.youcam.errors import YouCamEngineError, YouCamError
from app.youcam.features import FULL_SCAN
from conftest import contains_shape, docs_fixture, shape

run = asyncio.run
BASE = "https://yce-api-01.makeupar.com"


def raw(mock, method, path, **kw):
    req = httpx.Request(method, BASE + path, headers={"Authorization": "Bearer test-key-123456"}, **kw)
    return mock.handler(req)


def test_file_create_matches_docs(mock_api):
    mock, _ = mock_api
    r = raw(mock, "POST", "/s2s/v2.0/file", json={"files": [{"content_type": "image/jpeg", "file_name": "a.jpg",
                                                            "file_size": 1234}]})
    assert r.status_code == 200
    assert contains_shape(shape(r.json()), shape(docs_fixture("file_create_200.json")))


def test_task_create_poll_and_vto_success_match_docs(mock_api):
    mock, client = mock_api
    fid = run(client.upload(variant_bytes("ananya", "face")))
    r = raw(mock, "POST", "/s2s/v2.0/task/makeup-vto", json={"src_file_id": fid, "version": "1.0", "effects": [
        {"category": "lip_color", "shape": {"name": "original"}, "style": {"type": "full"},
         "palettes": [{"color": "#B3132B", "texture": "matte", "colorIntensity": 80}]}]})
    assert contains_shape(shape(r.json()), shape(docs_fixture("task_create_200.json")))
    tid = r.json()["data"]["task_id"]
    first = raw(mock, "GET", f"/s2s/v2.0/task/makeup-vto/{tid}").json()
    assert first == docs_fixture("task_running.json")
    done = raw(mock, "GET", f"/s2s/v2.0/task/makeup-vto/{tid}").json()
    assert contains_shape(shape(done), shape(docs_fixture("vto_success.json")))


def test_skin_analysis_json_matches_docs_and_normalises(mock_api):
    mock, client = mock_api
    fid = run(client.upload(variant_bytes("ananya", "face")))
    res = run(client.run("skin_analysis", {"src_file_id": fid, "dst_actions": FULL_SCAN, "format": "json",
                                           "miniserver_args": {"enable_mask_overlay": False}}))
    doc = docs_fixture("skin_analysis_success_json.json")["data"]
    # same entry kinds as the documented example: scored concerns, skin_type, skin_age, all, resize_image
    kinds = {o["type"] if o["type"] in ("skin_age", "all", "resize_image") else "concern" for o in doc["results"]["output"]}
    got = {o["type"] if o["type"] in ("skin_age", "all", "resize_image") else "concern" for o in res.data["results"]["output"]}
    assert kinds <= got
    scored = [o for o in res.data["results"]["output"] if "ui_score" in o]
    assert contains_shape(shape(scored[0]), {"type": "string", "raw_score": "number", "ui_score": "number",
                                             "mask_urls": ["string"]})
    scan = normalise(res.data["results"])
    assert len(scan["concerns"]) == 11 and scan["skin_type"]["whole"]["type"] == "Combination"
    assert [c["rank"] for c in scan["concerns"]] == list(range(1, 12))


def test_normalise_reads_the_documented_hd_example():
    scan = normalise(docs_fixture("skin_analysis_success_json.json")["data"]["results"])
    ids = {c["id"] for c in scan["concerns"]}
    assert ids == {"wrinkle", "pore", "acne"}          # HD sub-regions collapse to the whole-face score
    assert scan["skin_type"]["t_zone"]["type"] == "Oily" and scan["skin_age"] == 29


def test_documented_validation_errors(mock_api):
    mock, client = mock_api
    fid = run(client.upload(variant_bytes("ananya", "face")))
    r = raw(mock, "POST", "/s2s/v2.1/task/skin-analysis", json={"src_file_id": fid, "dst_actions": ["hd_pore", "acne"]})
    assert r.status_code == 400 and r.json() == docs_fixture("error_mixed_hd_sd.json")
    r = raw(mock, "POST", "/s2s/v2.1/task/skin-analysis", json={"src_file_id": fid, "dst_actions": ["abc123"]})
    assert r.json() == docs_fixture("error_unknown_action.json")
    r = mock.handler(httpx.Request("GET", BASE + "/s2s/v1.0/client/credit"))
    assert r.status_code == 401
    r = raw(mock, "POST", "/s2s/v2.0/task/makeup-vto", json={"src_file_id": fid, "effects": [
        {"category": "blush", "pattern": {"name": "NotAPattern"}, "palettes": [{"color": "#FF0000"}]}]})
    assert r.status_code == 400 and r.json()["error_code"] == "InvalidStyle"
    r = raw(mock, "POST", "/s2s/v2.0/task/beard-style", json={"src_file_id": fid, "template_id": "nope"})
    assert r.status_code == 400


def test_forgetting_the_presigned_put_fails_like_the_docs_warn(mock_api):
    mock, _ = mock_api
    r = raw(mock, "POST", "/s2s/v2.0/file", json={"files": [{"content_type": "image/jpeg", "file_name": "a.jpg",
                                                            "file_size": 10}]})
    fid = r.json()["data"]["files"][0]["file_id"]
    r = raw(mock, "POST", "/s2s/v2.0/task/hair-color", json={"src_file_id": fid, "preset": "Burgundy"})
    assert r.status_code == 404


def test_engine_error_is_raised_and_not_charged(mock_api):
    mock, client = mock_api
    from PIL import Image
    import io
    b = io.BytesIO()
    Image.new("RGB", (400, 400), (200, 160, 140)).save(b, "JPEG")
    fid = run(client.upload(b.getvalue()))
    before = mock.balance
    with pytest.raises(YouCamEngineError) as e:
        run(client.run("skin_analysis", {"src_file_id": fid, "dst_actions": ["acne"], "format": "json"}))
    assert e.value.code == "error_below_min_image_size" and "small" in e.value.hint.lower()
    assert mock.balance == before


def test_credit_insufficiency_surfaces_as_youcam_error(mock_api):
    mock, client = mock_api
    mock.balance = 3
    fid = run(client.upload(variant_bytes("ananya", "face")))
    with pytest.raises(YouCamError) as e:
        run(client.run("skin_analysis", {"src_file_id": fid, "dst_actions": FULL_SCAN, "format": "json"}))
    assert e.value.code == "CreditInsufficiency"


def test_utilities_cost_nothing(mock_api):
    mock, client = mock_api
    assert run(client.credit()) == 1000.0
    skus = run(client.feature_costs())
    assert any("Skin Analysis" in s["description"] and s["amount"] == 14 for s in skus)
    tpl = run(client.templates("beard_style"))
    assert tpl and {"id", "title", "thumb"} <= set(tpl[0])
    assert mock.charged == []


def test_units_charged_per_documented_table(mock_api):
    mock, client = mock_api
    face = run(client.upload(variant_bytes("ananya", "face")))
    portrait = run(client.upload(variant_bytes("meera", "portrait")))
    beard = run(client.upload(variant_bytes("arjun", "beard")))
    ref = run(client.upload((__import__("pathlib").Path("app/static/jewellery/jhumka_gold_ref.jpg")).read_bytes()))
    run(client.run("skin_analysis", {"src_file_id": face, "dst_actions": FULL_SCAN, "format": "json"}))
    run(client.run("skin_analysis", {"src_file_id": face, "dst_actions": FULL_SCAN[:4], "format": "json"}))
    run(client.run("skin_simulation", {"src_file_id": face, "radiance": 0.6, "pores": 0.6}))
    run(client.run("hair_color", {"src_file_id": portrait, "preset": "Burgundy"}))
    run(client.run("earring", {"src_file_id": portrait, "ref_file_ids": [ref], "source_info": {"name": portrait},
                               "object_infos": [{"name": ref}]}))
    tid = run(client.templates("beard_style"))[0]["id"]
    run(client.run("beard_style", {"src_file_id": beard, "template_id": tid}))
    assert mock.charged == [("skin_analysis", 14), ("skin_analysis", 9), ("skin_simulation", 4), ("hair_color", 1),
                            ("earring", 1), ("beard_style", 2)]


def test_result_urls_handles_documented_variants():
    assert result_urls({"results": {"url": "u1"}}) == ["u1"]
    assert result_urls({"results": [{"download_url": "u2"}]}) == ["u2"]
    assert result_urls({"results": "u3"}) == ["u3"]


def test_client_retries_429(mock_api):
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"status": 429, "error": "Too many requests"})
        return httpx.Response(200, json={"status": 200, "results": [{"amount_dec": 5.5}]})

    async def go():
        async def nosleep(_):
            return None
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            c = YouCamClient("k-123456789", BASE, http, sleep=nosleep)
            return await c.credit()
    assert run(go()) == 5.5 and calls["n"] == 3
