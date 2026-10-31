# Devpost form: every field, in page order

Copy the text between the lines into each field. Items marked LATER need the live link, repo or video first.

==================================================================
PAGE 2: PROJECT OVERVIEW
==================================================================

Project name:
ShaadiGlow

Elevator pitch:
An AI skin coach and virtual trial room for India's wedding season: one YouCam skin scan becomes a dated prep plan, every event look is tried on your own face, and it all lands in one cart.

Thumbnail: submission/thumbnail_3x2.png

==================================================================
PAGE 3: PROJECT DETAILS
==================================================================

----- About the project (paste everything down to the next line of dashes) -----
## Inspiration

India's wedding economy runs in short, intense seasons. The Confederation of All India Traders projected 46 lakh weddings worth ₹6.5 lakh crore in just the 1 Nov–14 Dec 2025 window, with jewellery about 15% of the spend. Every one of those weddings has a bride, a groom and dozens of guests who all want to look good on camera.

Anyone who has been part of an Indian wedding knows the pattern: "skin prep" starts three weeks out, a new serum or a first-ever facial gets tried in the final week, threading happens the day before, and lipstick and jewellery are bought from flat product photos across five different apps. The problem isn't a lack of products. It's that nobody turns "what does my skin need?" into "what should I do on which day before *my* wedding, in *my* city's weather, on *my* budget?", and nobody lets you see the look before you buy it.

YouCam's Skin Analysis gives exactly the measurement that's missing, and its try-on APIs let you see the result first. ShaadiGlow connects the two.

## What it does

ShaadiGlow is a mobile web app (phone browser, installable as a PWA) for brides, grooms and guests:

1. **Scan.** A guided selfie (YouCam JS Camera Kit checks light, angle and distance) or an upload goes through the YouCam File API and **AI Skin Analysis v2.1**: 12 concerns a 30–90-day routine can act on, a skin score, skin age, T-zone vs cheeks skin type, and the AI's own masks, which you can tap to see where the AI looked.
2. **See the goal.** **AI Skin Simulation** shows a wedding-day goal for your top concerns, labelled as a preview, not a promise.
3. **Follow a countdown plan.** A deterministic, explainable rules engine turns your scores into an AM/PM routine dated to your wedding, adjusted for your city's humidity, temperature and UV, your budget and safety flags. Every active ingredient comes with a "Why?". It enforces real event-prep rules: actives need runway, one new product at a time after a 48 h patch test, nothing new in the last 14 days, retinol stops at D-7 and acids at D-5, threading at D-4, natural henna only (no PPD "black henna"). Milestones export to your calendar.
4. **Try every look.** Each event (Haldi, Mehendi, Sangeet, Pheras, Reception) is a single **AI Makeup Virtual Try-On** call that stacks lipstick, kohl, eyeshadow, blush, highlighter and a shade-matched foundation, so one unit shows a whole look. **AI Hair Color**, **AI Earrings** and **AI Necklace** cover hair and jewellery, and grooms get the **AI Beard Style Generator**.
5. **Shop the look.** Everything you tried lands in one cart, each item tagged with the concern it treats, with a budget meter and WhatsApp sharing. The store is a clearly labelled sample catalogue of fictional, unbranded products.
6. **Track progress.** Every 14 days a quick re-scan measures only your 4 tracked concerns (9 units instead of 14). Changes inside ±2 points are reported as "steady", not celebrated as progress.

It works in English and Hindi, and "Delete my photos & results" also deletes every task and file on YouCam's side through the Task Management API.

## How I built it

- **Backend:** Python FastAPI with an async httpx client for the documented YouCam flow: `POST /s2s/v2.0/file` → `PUT` to the pre-signed URL → `POST` the task → poll `task_status` → download results right away (result URLs expire after 2 hours). 429 back-off, engine error codes mapped to user-facing hints, plus the Unit API and Task Delete API.
- **Unit discipline:** a disk cache keyed by `sha256(image) + feature + parameters`, a seed cache shipped in the repo so the sample models cost 0 units on a fresh deploy, and a budget guard that reads the real balance, keeps a reserve and caps units per visitor. Every button shows its cost.
- **A mock that speaks the contract:** before I had a key I built an httpx transport that answers the same endpoints with the same JSON shapes and validation as the docs. Setting `YOUCAM_API_KEY` swaps the transport; nothing else changes. When the key arrived, a smoke script verified every endpoint against the live API and recorded the real responses as test fixtures.
- **Rules engine:** a hand-written ingredient knowledge base (targets, runway, stop dates, pregnancy and sensitive-skin flags), bilingual rules, 16-city climate bands and phase scheduling. No LLM, so the same inputs always give the same plan.
- **Frontend:** vanilla JavaScript and hand-written CSS, Devanagari typography, vector product art, a before/after slider, and the YouCam JS Camera Kit.
- **Quality:** 81 automated tests, including contract tests and a Playwright run of the whole journey on a phone viewport. Deployed as a Docker web service on Render.

## Challenges I ran into

- **Building before the key existed.** I made the mock a faithful simulator of the documented contract instead of canned JSON. On the first live run, every billed cost matched the docs exactly.
- **Spending 1,000 units wisely.** SD skin tiers are 9/12/14/16 units for 4/8/12/16 concerns, so I dropped concerns nothing topical can fix before a wedding and landed in the 14-unit tier. Re-scans track 4 concerns (9 units), and one makeup request renders a whole look.
- **Different photo rules per API.** Skin analysis wants the face to fill the frame; makeup and hair reject frames taller than about 1080 px; beard needs a long side under 1024 px; jewellery needs ears and neck visible. The backend builds a correctly sized variant of the same photo for each API.
- **Honest progress.** I scanned the same photo twice on the live API: the four tracked scores differed by at most 1 point. So re-scans only call a change "better" when it moves more than 2 points.

## Accomplishments that I'm proud of

- A real product loop, not a wrapper: measure → plan → preview → try → buy → re-measure.
- Every recommendation is explainable and dated, with event-specific safety rules.
- Seven YouCam AI APIs plus the File, Unit and Task Management APIs and the JS Camera Kit, each where it changes a decision.
- A complete Hindi experience.
- Unit-aware engineering: cache, seed cache, budget guard and visible costs.

## What I learned

- How YouCam's skin scores are built (`ui_score` is calibrated for shoppers, `raw_score` is the model's estimate) and why ranking by the raw score is more honest.
- Good event-prep advice is mostly about *time*: when to start, when to stop, and when to change nothing.
- A documented-contract mock makes a build fast: the client, cache and UI were finished and tested before the first paid call.

## What's next for ShaadiGlow

- A small pilot with brides in Patna and Delhi this wedding season.
- A white-label version for beauty and jewellery retailers: the countdown plan is a 30–90-day engagement loop that ends in a high-intent basket.
- Makeup-artist mode: share saved looks with your MUA before the trial.
- More languages (Bengali, Tamil, Marathi).
----------------------------------------------------------------------

Built with (type each, press Enter):
python, fastapi, uvicorn, httpx, pillow, numpy, javascript, html5, css3, youcam-api, playwright, pytest, docker, render

"Try it out" links (LATER):
1. https://<your-service>.onrender.com
2. https://github.com/rounak251/shaadiglow

Image gallery (LATER, in this order): screenshots/01-welcome.png ... 06-shop-the-look.png

Video demo link (LATER): https://youtu.be/<id>

==================================================================
PAGE 4: ADDITIONAL INFO
==================================================================

Upload a file: leave empty.

Sponsor / Special Prizes: select **Rising Star Award (Student Only)** (and anything else you are eligible for).
If it asks for a school email: your @nitp.ac.in address.

Submitter type: **Student** if listed, otherwise **Individual**.

Country of residence: **India**

App Status: **New** (built for this hackathon). Leave "If Existing" empty.

----- Text description: features, functionality, consumer or retail value -----
ShaadiGlow turns one selfie into a wedding-ready plan and a shopping basket.

Features: YouCam AI Skin Analysis (12 concerns, skin age, skin type, tappable masks); AI Skin Simulation for a wedding-day goal preview; a dated countdown routine adjusted for city climate, budget and safety rules; one-call event looks with AI Makeup VTO; AI Hair Color, AI Earrings, AI Necklace and AI Beard Style try-ons; a single cart for routine, makeup and jewellery; 14-day re-scans that only report real change; English and Hindi; one-tap deletion of all photos and results, including on YouCam's side.

Consumer value: a bride, groom or guest gets a personal, dated plan instead of last-minute guesswork, sees every look on their own face before buying, and avoids the classic mistakes (new actives in the final week, untested products, black henna).

Retail value: India has tens of lakhs of weddings per season, and jewellery and beauty are a large share of the spend. ShaadiGlow starts 30–90 days before the event, keeps the shopper engaged with milestones and re-scans, and ends in a high-intent basket where every product is tied to a measured concern or a look the shopper already tried. A retailer can white-label it with their own catalogue.
----------------------------------------------------------------------

Code repository URL (LATER): https://github.com/rounak251/shaadiglow

----- Was there a moment where the API surprised you? -----
Two, one each way. The good one: when my key arrived, I ran every endpoint once, and the units charged matched the documentation exactly for all features (Skin Analysis 9, Skin Simulation 4, Makeup 1, Hair Color 1, Necklace 1, Beard 2). I had built my whole budget guard expecting surprises and there were none. I also scanned the same photo twice and the four tracked scores moved by at most 1 point, which is more stable than I expected and let me tighten the app's "no real change" band from ±3 to ±2.

The frustrating one: AI Earrings rejected my sample guest photo with "earlobe alignment not confident", because her hair covers part of the ear. It makes sense, but nothing in the request tells you in advance whether a photo will pass, so I turned that engine error into a friendly hint in the app ("tuck your hair behind your ears and retake") instead of a failed screen.
----------------------------------------------------------------------

----- Industries or use cases nobody is talking about yet? -----
1. Jewellery rental and gold showrooms in India. Many families rent or buy heavy bridal sets for one day. Earring and necklace try-on on the customer's own photo, sent over WhatsApp before a showroom visit, would cut wasted trips and help small jewellers compete with big chains.
2. Cosmetic "in-use" claim testing. Brands run 4–8 week consumer trials to support claims like "reduces dark circles". Repeated Skin Analysis scans with a measured noise band (like ShaadiGlow's re-scan) could give cheap, objective before/after evidence at home instead of in a lab.
3. Makeup artists and salons. MUAs spend a paid trial session just to agree on a look. Letting the client try looks on their own face first, then share them with the artist, turns the trial into a refinement session and is a natural lead source for salon bookings.
----------------------------------------------------------------------

----- Where did you hit a wall technically? How did you work around it? -----
The biggest wall was building for a paid API before I had a key. I didn't want to guess, so I wrote a mock transport that follows the documented contract field by field, contract-tested against the docs' own example responses, including validation like SD/HD mixing and makeup pattern labels. The real client, cache, budget guard and UI were built and tested against it. When the key arrived, a smoke script verified every endpoint with the cheapest legal request and saved the real responses as fixtures.

The second wall was photo requirements: each API wants something different (face filling the frame for skin analysis, under ~1080 px tall for makeup and hair, long side under 1024 px for beard, visible ears and neck for jewellery). The backend now makes a separate correctly sized variant of the same photo for each feature, and engine errors such as "earlobe alignment not confident" are mapped to plain retake hints.

The third was the 1,000-unit budget: a content-addressed cache (a repeat request is free), a seed cache shipped in the repo so judges' sample journeys cost 0 units, and a guard that reads the real balance and caps units per visitor.
----------------------------------------------------------------------

Social post link: optional. If you post the demo video (tag @YouCam API, list the APIs, add "Received API credits for sharing"), paste that post's link here.
