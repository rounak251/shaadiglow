# Devpost submission: copy-paste fields

Hackathon: **YouCam API Skin AI & eCommerce VTO Hackathon** (youcam-api-skin-ai-ecommerce.devpost.com)
Deadline: **Mon 2 Nov 2026, 22:15 IST** (11:45 am EST). Submit by ~18:00 IST to leave slack.

---

## Project name
ShaadiGlow

## Tagline (≤ 200 characters)
An AI skin coach and virtual trial room for India's wedding season: one YouCam skin scan becomes a dated prep plan, every event look is tried on your own face, and it all lands in one cart.

## Track / topic
Skin AI (with eCommerce VTO). Uses 7 YouCam AI APIs.

---

## Inspiration

India's wedding economy runs in short, intense seasons. The Confederation of All India Traders projected 46 lakh weddings worth ₹6.5 lakh crore in just the 1 Nov–14 Dec 2025 window, with jewellery about 15% of the spend. Every one of those weddings has a bride, a groom and dozens of guests who all want to look good on camera.

Anyone who has been part of an Indian wedding knows the pattern: "skin prep" starts three weeks out, a new serum or a first-ever facial gets tried in the final week, threading happens the day before, and lipstick and jewellery are bought from flat product photos across five different apps. The problem isn't a lack of products. It's that nobody turns "what does my skin need?" into "what should I do on which day before *my* wedding, in *my* city's weather, on *my* budget?", and nobody lets you see the look before you buy it.

YouCam's Skin Analysis gives exactly the measurement that's missing, and its try-on APIs let you see the result first. ShaadiGlow connects the two.

## What it does

ShaadiGlow is a mobile web app (phone browser, installable as a PWA) for brides, grooms and guests:

1. **Scan.** A guided selfie (YouCam JS Camera Kit checks light, angle and distance) or an upload with an oval crop goes through the YouCam File API and **AI Skin Analysis v2.1**. We request the 12 concerns a 30–90-day routine can act on (14-unit tier) and get back a skin score, skin age, T-zone vs cheeks skin type, and the AI's own masks, which you can tap to see where the AI looked.
2. **See the goal.** **AI Skin Simulation** shows a realistic wedding-day goal for your top concerns, labelled as a preview, not a promise.
3. **Follow a countdown plan.** A deterministic, explainable rules engine maps your scores to ingredients and an AM/PM routine for your wedding date, adjusted for your city's month-by-month humidity, temperature and UV, your budget (₹/₹₹/₹₹₹), and safety flags. Every step has a "Why?". It enforces real event-prep rules: actives need runway (retinol only with 8+ weeks), one new product at a time after a 48 h patch test, nothing new in the last 14 days, retinol stops at D-7 and acids at D-5, threading at D-4, natural henna only (no PPD "black henna"), and a season switch when your city turns dry before the wedding. Milestones export to your calendar (.ics).
4. **Try every look.** In the look studio, each event (Haldi, Mehendi, Sangeet, Pheras, Reception) is a single **AI Makeup Virtual Try-On** call that stacks lipstick, kohl, eyeshadow, blush, highlighter and a foundation matched to your shade, so one unit shows a complete look. **AI Hair Color**, **AI Earrings** and **AI Necklace** try-ons cover hair and jewellery (jhumkas, chandbalis, kundan choker…), and grooms get the **AI Beard Style Generator**.
5. **Shop the look.** Everything you tried (routine, look products, jewellery) lands in one cart, each item tagged with the concern it treats, with a budget meter and WhatsApp sharing. The store is a clearly labelled sample catalogue of fictional, unbranded products.
6. **Track progress.** Every 14 days a quick re-scan measures only your 4 tracked concerns (9 units instead of 14), and changes inside ±3 points are reported as "steady" rather than celebrated as progress.

It works in English and Hindi, and "Delete my photos & results" also deletes every task and file on YouCam's side through the Task Management API.

## How we built it

- **Backend:** Python FastAPI with an async httpx client that implements the documented YouCam flow end to end: `POST /s2s/v2.0/file` → `PUT` to the pre-signed URL → `POST /s2s/v2.x/task/<feature>` → poll `task_status` → download results immediately (result URLs expire after 2 hours). 429 back-off, engine error codes mapped to user-facing hints, and the Unit API (`credit`, `feature-cost`) and Task Delete API.
- **Unit discipline (1,000 free units):** a disk cache keyed by `sha256(image) + feature + parameters` (a repeat is free); a read-only seed cache shipped in the repo so the sample models cost 0 units on a fresh deploy; a budget guard that checks the real balance, keeps a reserve and caps units per visitor; and a ledger. Every button shows its cost.
- **Mock that speaks the contract:** before I had a key, I built an httpx transport that answers the same endpoints with the same JSON shapes as the docs (contract-tested against the documentation's own examples) and the same validation (SD/HD mixing, makeup pattern labels from YouCam's catalogues, template ids, image limits). Setting `YOUCAM_API_KEY` swaps the transport; nothing else changes.
- **Rules engine:** hand-written knowledge base of ingredients (targets, runway, stop dates, pregnancy/sensitive-skin flags) and bilingual rules, a greedy concern-coverage selector, 16-city climate bands, budget tiers, and phase scheduling. No LLM, so the same inputs always give the same plan.
- **Frontend:** vanilla JavaScript modules and hand-written CSS (no build step), self-hosted fonts, Devanagari typography, vector product art, a before/after compare slider, and the YouCam JS Camera Kit for guided capture.
- **Quality:** 81 automated tests, including contract tests, a test proving the pre-warm script fills exactly the cache keys the app looks up, and a Playwright smoke test of the whole journey on a phone viewport. Deployed as a Docker web service on Render.

## Challenges we ran into

- **Building before the key existed.** I designed the mock as a faithful simulator of the documented contract rather than canned JSON, then wrote `scripts/live_smoke.py` to verify each endpoint once with the cheapest legal request (~19 units) and record the real responses as fixtures.
- **Spending 1,000 units wisely.** The SD skin tiers are 9/12/14/16 units for 4/8/12/16 concerns, so I dropped eyelid droop, firmness and tear trough (nothing topical fixes them before a wedding) and landed in the 14-unit tier. Re-scans track only 4 concerns (9 units), and one makeup request renders a whole look.
- **Different photo rules per API.** Skin analysis needs the face to fill over 60% of the width; makeup and hair try-on reject frames taller than ~1080 px; beard styles need a long side under 1024 px; jewellery needs ears and neck visible. The backend builds a separate, correctly sized variant of the same photo for each API.
- **Honest progress.** Two photos of the same face never score identically, so re-scans only call a change "better" when it exceeds a noise band; the live smoke script can measure that band from two scans of the same photo.

## Accomplishments that we're proud of

- A real product loop, not a wrapper: measure → plan → preview → try → buy → re-measure.
- Every recommendation is explainable and dated, with event-specific safety rules (patch tests, last-14-days freeze, PPD henna warning).
- Seven YouCam AI APIs plus the File, Unit and Task Management APIs and the JS Camera Kit, each in a place where it changes a decision.
- A complete Hindi experience.
- Unit-aware engineering: cache, seed cache, budget guard, and visible costs on every button.

## What we learned

- How YouCam's skin scores are built (`ui_score` is calibrated for shoppers, `raw_score` is the model's estimate) and why ranking by the raw score is more honest.
- That good event-prep advice is mostly about *time*: when to start, when to stop, and when to change nothing.
- How much a documented-contract mock speeds up a build: the client, cache and UI were finished and tested before the first paid call.

## What's next for ShaadiGlow

- Run the live smoke and pre-warm with the hackathon units, then a small pilot with brides in Patna and Delhi.
- A white-label version for beauty and jewellery retailers: the countdown plan is a 30–90-day engagement loop that ends in a high-intent basket.
- Makeup-artist mode: share the saved looks with your MUA before the trial.
- More languages (Bengali, Tamil, Marathi) and Fitzpatrick-aware sunscreen advice.

---

## Built with
python, fastapi, uvicorn, httpx, pillow, numpy, javascript, html5, css3, youcam-api, youcam-skin-analysis, youcam-makeup-vto, playwright, pytest, docker, render

## "Try it out" links
- Live app: `https://<your-service>.onrender.com` (no login needed; sample models are free to use)
- Code: `https://github.com/<you>/shaadiglow` (public, MIT licence)

## Video demo link
`https://youtu.be/<id>` (public; 2:30; narrated; no music)

## Testing instructions (paste into the form)
Open the live link on a phone (or a desktop browser at phone width). Tap **Ananya** (sample bride) → **Continue** to run the full journey with pre-computed YouCam results (0 units). To try your own selfie, tap **Start with my selfie**, tick the consent box, and use **Guided camera** or **Upload a photo** (live YouCam calls; capped per visitor). The ⓘ button shows the mode, units used and the API cost table. "Delete my photos & results" removes your data, including on YouCam's side.

## New or significantly updated after 29 Sep 2026?
New. ShaadiGlow was created from scratch for this hackathon between 23 Oct and 2 Nov 2026; the git history starts on 23 Oct 2026. No earlier version exists.

## Special award opt-in: Rising Star Award (Student Only)
Opt in. I am a currently enrolled 3rd-year B.Tech student at the National Institute of Technology Patna. School-issued email for verification: **`<your-roll-or-name>@nitp.ac.in`** (fill in your actual @nitp.ac.in address on the form).

## Team
Solo: Rounak Choudhary (NIT Patna, India).

## Screenshots (upload in this order)
1. `screenshots/01-welcome.png` – Who's getting ready? Sample models cost 0 units.
2. `screenshots/02-skin-report.png` – AI Skin Analysis report with the oil-control mask.
3. `screenshots/03-wedding-day-goal.png` – AI Skin Simulation before/after.
4. `screenshots/04-countdown-plan.png` – D-58 countdown with climate, phases and routine.
5. `screenshots/05-look-studio.png` – "Pheras Classic Red" via AI Makeup Virtual Try-On.
6. `screenshots/06-shop-the-look.png` – One cart for routine, look and jewellery.

## Optional: social sharing bonus (+500 units per platform, max 2)
Post the demo video from an account created before 29 Sep 2026, tag **@YouCam API**, say which APIs it uses, add the line **"Received API credits for sharing"**, keep it public for 30 days, then submit https://forms.gle/JwMFYMpaExckupEk7 before the deadline.
