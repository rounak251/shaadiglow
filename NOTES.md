# NOTES: status, decisions, and what still needs the live key

Deadline **Mon 2 Nov 2026, 22:15 IST**. Aim to submit by **2 Nov, 18:00 IST**. The testing link must stay up until
**20 Nov**.

## Status (23 Oct 2026)

- The app is complete and verified in **demo mode** (no key): every screen, both languages, all seven YouCam
  features, cache, budget guard, deletion. 81 tests pass (`pytest -q`), including the Playwright phone-flow test.
- **Nothing has been sent to the live YouCam API yet** (no key existed). Demo-mode images are simulated locally from
  the licensed sample photos and are labelled "Demo data" in the app. The screenshots and `demo/demo.mp4` were made
  in demo mode and **must be re-made with the live key** before submitting.

## Decisions made after reading the API docs (and why)

| Concept idea | What the docs allowed | What ShaadiGlow does |
|---|---|---|
| Skin report with overlays | AI Skin Analysis v2.1 returns per-concern `ui_score`/`raw_score` and mask URLs; `format=json`; SD and HD can't be mixed; SD tiers 9/12/14/16 units | 12 **SD** concerns (14 units) as JSON with raw masks (`enable_mask_overlay=false`) so each mask can be toggled. HD would need a ≥1080 px short side and 20 units. Eyelid droop, firmness and tear trough are skipped on purpose. |
| Countdown plan | No API; must be ours | Deterministic rules engine (no LLM). |
| "Goal" visual (new) | AI Skin Simulation (0.0–1.0 per concern, 4 units for ≤4) | Wedding-day goal preview at 0.6 intensity, labelled "a preview, not a promise". |
| Makeup try-on | Makeup VTO: many effects in one call, 1 unit; pattern names must match YouCam's catalogues | One request per event look; patterns validated against the official catalogues (`app/youcam/patterns.json`). |
| Hair colour/style | Hair Color (presets/palettes, 1 unit); Hairstyle templates (1–2 units, unknown template set) | Hair Color only; hairstyle templates left as a stretch goal. |
| Jewellery | Earrings and Necklace 2D VTO need a **product reference image**; best with ears/neck visible | Original jewellery art (drawn by `tools/make_jewellery.py`) sent as the reference; a separate head-and-shoulders crop; a guest persona (Meera) whose photo shows ears and neck. |
| Groom beard | Beard Style Generator (templates via API, 2 units, long side < 1024) | Live template list; a 720x960 crop. |
| Foundation shade | Facial Color Tones Analyzer costs 20 units | Shade estimated from cheek pixels (free), always user-adjustable. |
| Guided capture | YouCam JS Camera Kit (CDN) | Integrated. The docs say `window.YMKAsyncInit`, but the SDK calls `window.ymkAsyncInit`, so both are set. The kit rejects virtual/fake cameras, so it can't appear in the headless recording: test it on a real phone. |
| Progress | Same Skin Analysis API | Quick re-scan of the 4 tracked concerns (9 units) with a noise band. |
| Privacy | Task Management API: delete a task and its files | "Delete my photos & results" calls it for every task. |

Webhooks were not used: polling is enough for one instance, and Render's free tier sleeps.

## Do this once the redeem code arrives (in order)

1. **Register** on Devpost (Join hackathon) with your account; the redeem code arrives by email.
2. **Sign up** on the India console https://yce.makeupar.com/ai-api, verify your email, then
   **Account → Redeem Code** → enter the code (1,000 units).
3. **API Keys → create key.** Put it only in your shell: `export YOUCAM_API_KEY=...` (and later in Render).
4. **Verify every endpoint (~19 units):**
   ```bash
   .venv/bin/python scripts/live_smoke.py --dry-run
   .venv/bin/python scripts/live_smoke.py
   ```
   Read the "documented vs charged" table and the JSON in `fixtures/recorded/`. If something fails, see
   "Assumptions to confirm" below; errors are saved as `fixtures/recorded/<feature>_error.json`.
5. **Measure scan noise (18 units):** `scripts/live_smoke.py --noise`, then set `NOISE_BAND` in
   `app/engine/progress.py` to the suggested value.
6. **Pre-warm the sample journeys (~89 units):** `scripts/live_smoke.py --prewarm core`, then
   `git add cache_seed && git commit -m "Live results for sample models"`.
7. **Walk the app in live mode:** `.venv/bin/uvicorn app.main:app`, open http://127.0.0.1:8000 at phone width,
   do all three personas. Check every image. If earrings look wrong on Ananya (hair covers her ears), keep jewellery
   for Meera only.
8. **Re-shoot screenshots (0 units if pre-warmed):** `.venv/bin/python scripts/make_screenshots.py`.
9. **Re-record the video:** `.venv/bin/python scripts/record_demo.py` → watch all of it → upload to YouTube as
   **Public** (no music is used). Optional: splice in a short real-phone clip of the Camera Kit capture.
10. **Deploy** (DEPLOY.md), set `YOUCAM_API_KEY` as a Render secret, test `/api/health` shows `"mode":"live"`.
11. **Push the repo** public with the LICENSE (DEPLOY.md step 0).
12. **Fill the placeholders in SUBMISSION.md** (Render URL, GitHub URL, YouTube URL, your @nitp.ac.in email),
    personalise "Inspiration" if you like, opt in to **Rising Star**, upload the six screenshots, and submit.

## Assumptions to confirm with the first live calls

- Base URL: India keys with `https://yce-api-01.makeupar.com` (docs default). If you get 401, try
  `YOUCAM_REGION=global` (`yce-api-01.perfectcorp.com`).
- File API response: `data.files[0].file_id` and `requests[0].{url,headers,method}`; the client also accepts the
  un-wrapped shape.
- Skin Analysis JSON: SD entries may or may not carry `region`; skin-type entries use the field `skin_type`. The
  parser handles both; confirm in `fixtures/recorded/skin_analysis_response.json`.
- Masks: expected PNG with alpha (raw). If they arrive as opaque JPEGs, they still display; consider
  `enable_mask_overlay=true` then.
- Makeup / Hair Color size limit: we send 768x1024 (height < 1080). Beard: 720x960 (long side < 1024).
- Earrings: our reference shows a **pair**; the docs say a pair is auto-detected and worn on both ears. Confirm it is
  charged 1 unit (not 2 "stacked") and looks right; otherwise switch to a single-earring reference.
- Skin Simulation poll response: we read `results.url` (also tolerant of other shapes).
- `pf_camera_kit: true` is sent with v2.1 scans when the photo came from the Camera Kit.
- The JS Camera Kit loads from YouCam's CDN without a key in our tests; if it shows a licence/permission error on
  your deployed domain, set `SG_CAMERA_KIT=false` on Render to hide the button (upload still works).
- Prices: 14 / 9 / 4 / 1 / 1 / 1 / 1 / 2 units as in the docs; the Unit API's `feature-cost` list is saved by the
  smoke run.

## Unit plan (1,000 free units)

| Use | Units |
|---|---|
| Live smoke (every endpoint once) | ~19 |
| Noise check | 18 |
| Pre-warm sample journeys (core) | ~89 |
| Your own testing (2 full journeys) | ~72 |
| Left for judges' own photos | ~800 |

Guardrails on the server: 60-unit reserve, 60 units per visitor per day, real balance checked before each call.
Optional +500 units per platform (max 2) from the social-sharing bonus (rules in SUBMISSION.md).

## Remaining nice-to-haves

- Personalise the SUBMISSION "Inspiration" text with your own experience (it is written in a neutral voice).
- A 10-second real-phone screen recording of the guided camera for the video.
- Stretch features if units allow: Hairstyle templates (bridal buns), Nail VTO (mehendi-ready nails), Eye Color Lens.
- More cities and languages.

## Known limitations

- Demo-mode visuals are approximations rendered locally; only live mode shows YouCam's output.
- Climate bands are rounded indicative values, not weather data.
- The store is a fictional sample; checkout is a demo.
- Render free instances sleep after 15 minutes idle and have an ephemeral disk (see DEPLOY.md).
- If Playwright says a browser is missing: `.venv/bin/python -m playwright install chromium`.
