# NLP-1 public fixture provenance

Retrieved on 2026-10-12 for reproducible, non-sensitive research and integration testing. The files remain attributable to their public-sector issuers. No blanket redistribution license was identified on the source pages; retain the source links and reassess before publishing the dataset separately.

| File | Issuer/source | Language | Category | Form | Source URL | SHA-256 |
|---|---|---|---|---|---|---|
| `hindi/nfc_recruitment_01_2026_hindi.pdf` | Nuclear Fuel Complex, Department of Atomic Energy, Government of India | Hindi (with English identifiers) | Recruitment advertisement 01/2026 | Digital/searchable, 20 pages | <https://www.nfc.gov.in/pdf/recruitment-advt/2026/adv-no-nfc_01_2026_hind.pdf> | `2face8e0eb902016933910a7930238d67210ec4942fad262a526551b76a38d6a` |
| `telugu/ananthapuramu_anganwadi_recruitment_2025.pdf` | Women Development & Child Welfare Department, Ananthapuramu District, Government of Andhra Pradesh | Telugu (with English identifiers) | Anganwadi recruitment notification, 2025 | Scanned/image-only, 10 pages | <https://cdn.s3waas.gov.in/s333e8075e9970de0cfea955afd4644bb2/uploads/2025/12/17664699117464.pdf> | `6c629a75e959958859931e2a052712e760352bc2a2b261f91dd59f4acf0221b6` |

The Telugu source was linked from the Ananthapuramu District recruitment archive at <https://ananthapuramu.ap.gov.in/te/past-notices/%E0%B0%A8%E0%B0%BF%E0%B0%AF%E0%B0%BE%E0%B0%AE%E0%B0%95/page/3/>. PyMuPDF found zero embedded alphanumeric characters on every page, so it is the required real OCR fixture.

## Manually verified OCR sample

`ground_truth/telugu_page1_title.txt` is a manual transcription of the centered title on page 1 of the Telugu fixture. It is deliberately tiny evaluation scaffolding, not a representative OCR benchmark.
