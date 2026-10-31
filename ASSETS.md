# Assets and licences

## Sample model photos (Unsplash License)

All three are free-to-use photos under the [Unsplash License](https://unsplash.com/license) (commercial use
allowed, no permission needed; attribution given anyway). They are stock photos of consenting models, not private
individuals. They are cropped and resized by `tools/prepare_personas.py`; in demo mode the app shows *simulated*
fixture results on them, clearly labelled "Demo data". Live-mode results are the YouCam API's output.

| Persona in app | Photo page | Photographer | Image file used |
|---|---|---|---|
| Ananya (sample bride) | https://unsplash.com/photos/Bg3JaBhnrg4 | Andre Styles (@lovedisorder) | `images.unsplash.com/photo-1609371497456-3a55a205d5eb` |
| Arjun (sample groom), scan 1 | https://unsplash.com/photos/a-man-in-a-white-turtle-neck-sweater-FKLesO1D3Sk | ARTO SURAJ (@artosuraj) | `images.unsplash.com/photo-1712425718085-cdd2b2298669` |
| Arjun (sample groom), re-scan | https://unsplash.com/photos/a-man-in-a-white-shirt-smiling-for-the-camera-a26KbF2Mz1I | ARTO SURAJ (@artosuraj) | `images.unsplash.com/photo-1712425718137-491250cfde88` |
| Meera (sample guest) | https://unsplash.com/photos/a-woman-poses-in-a-purple-dress-VRa27T5quqs | Himanshu Dewangan (@himanshudewangan) | `images.unsplash.com/photo-1747264465820-87d6c1a0692c` |

Licence checked on each photo page on 23 Oct 2026 ("Free to use under the Unsplash License"; none is Unsplash+).
Derived files: `app/static/personas/<id>/{face,beard,portrait}.jpg` plus landmark/mask files used only by the mock.

## Fonts (SIL Open Font License 1.1)

Self-hosted from Google Fonts in `app/static/fonts/`: **Playfair Display**, **Plus Jakarta Sans**, **Mukta**
(Devanagari). OFL permits bundling and redistribution with software.

## Original work in this repository (MIT, see LICENSE)

- Jewellery artwork (`app/static/jewellery/*.png`, `*_ref.jpg`): drawn procedurally by `tools/make_jewellery.py`.
- Product "packshots": vector SVGs generated in the browser by `app/static/js/art.js`. No brand names or logos.
- App icon, logo, toran/mandala decorations, beard template thumbnails (`app/static/img/`).
- Architecture diagram (`docs/architecture.svg`).
- Demo video narration: macOS `say` text-to-speech. **No music.**

## Data derived from the YouCam documentation

- `fixtures/docs/*.json`: example responses copied verbatim from the YouCam API reference (docs.perfectcorp.com,
  v1.16) to contract-test the mock. Each file names its source.
- `app/youcam/patterns.json`: the list of valid makeup pattern labels from YouCam's public pattern catalogues
  (`plugins-media.makeupar.com/wcm-saas/patterns/*.json`), used to validate look requests.
- The YouCam JS Camera Kit is loaded at runtime from YouCam's CDN; it is not copied into the repo.

## Facts quoted in the submission

- Wedding-season figures: Confederation of All India Traders press release, 30 Oct 2025,
  https://cait.in//images/press-release/pdf_1762754341.pdf (46 lakh weddings, ₹6.5 lakh crore, 1 Nov–14 Dec 2025;
  jewellery 15%, apparel 10% of spend).
- Climate bands in `app/engine/climate.py` are rounded, hand-encoded indicative values, not a forecast.

YouCam, YouCam API and Perfect Corp. are trademarks of Perfect Mobile Corp. ShaadiGlow is an independent entry.
