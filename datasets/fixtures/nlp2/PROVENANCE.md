# NLP-2 public fixture provenance

Retrieved on 2026-10-12 and 2026-10-13 for reproducible, non-sensitive
research and evaluation. These documents remain attributable to their public
sector issuers. No blanket redistribution licence was identified on the source
pages; retain these links and reassess licensing before publishing the corpus
separately.

NLP-2 reuses the two official NLP-1 fixtures rather than duplicating their
bytes. Together, the two tables below form the ten-document NLP-2 fixture set:
five Hindi and five Telugu notices.

| File | Issuer/source | Language | Category | Form | Source URL | SHA-256 |
|---|---|---|---|---|---|---|
| `hindi/du_ncweb_admission_2024_hindi.pdf` | Non-Collegiate Women's Education Board, University of Delhi | Hindi | Admission | Digital/searchable, 23 pages | <https://admission.uod.ac.in/userfiles/downloads/02052024_UG-BOI-NCWEB_compressed.pdf> | `d2558ed06f6a7a1733abf9971e97517399984718291bc1ae1588f61142e4222c` |
| `hindi/kvs_admission_2025_hindi.pdf` | Kendriya Vidyalaya Sangathan, Ministry of Education | Hindi and English | Admission | Image-only, 1 page | <https://cdnbbsr.s3waas.gov.in/s3kv05ac1b53741fac7deb8b0ec49bb694/uploads/2025/03/2025030546.pdf> | `42dbb686075bb86b1942143d199e151d6006fb9d2da897fb4e2d11006986aece` |
| `hindi/scert_haryana_nmmss_2025_hindi.pdf` | SCERT Haryana | Hindi | Scholarship examination | Digital/searchable, 3 pages | <https://cdnbbsr.s3waas.gov.in/s323d2e1578544b172cca332ff74bddf5f/uploads/2025/09/202509051500147525.pdf> | `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2` |
| `hindi/uttarakhand_residential_school_exam_2025_hindi.pdf` | Uttarakhand Board of School Education | Hindi | Admission examination | Image-only, 9 pages | <https://cdnbbsr.s3waas.gov.in/s32dbf21633f03afcf882eaf10e4b5caca/uploads/2025/06/202506031033173496.pdf> | `181d39783474ea218a9a66f7547cd745c258394cb27152c493befee4a1bb9cd1` |
| `telugu/kv_kadapa_admission_2025_telugu.pdf` | PM SHRI Kendriya Vidyalaya Kadapa | Telugu | Admission | Digital/searchable, 4 pages | <https://cdnbbsr.s3waas.gov.in/s3kv01e8ad71f19b15f13fec3bc3a9094f/uploads/2025/03/2025031593.pdf> | `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc` |
| `telugu/kv_kothuru_admission_2025_telugu.pdf` | Kendriya Vidyalaya Kothuru | Telugu | Admission | Digital/searchable, 3 pages | <https://cdnbbsr.s3waas.gov.in/s3kv01953ce312e6b0ea48522bf39cbe62/uploads/2025/05/2025051620.pdf> | `3b87a2b47bc4fa2f76ed4f533b34b223c1353514bc6039144470b41a449d177d` |
| `telugu/kv_ramagundam_admission_2025_telugu.pdf` | Kendriya Vidyalaya NPS Ramagundam | Telugu | Admission | Digital/searchable, 2 pages | <https://cdnbbsr.s3waas.gov.in/s3kv01cba59a60eb0eb005eba81049fb22/uploads/2025/05/2025051590.pdf> | `8fee85de2250fc45c3c1f96f4d10f6d2151e768e35bcb59dff30cb2a2a085849` |
| `telugu/tsemrs_admission_2024_telugu.pdf` | Telangana State Eklavya Model Residential Schools Society | Telugu | Admission examination | Image-only, 10 pages | <https://tsemrs.telangana.gov.in/openfile.php?f=160> | `72b08072c1d648df1570cf6fab5c408ca0a1ebacf3df3ce0f7be20491e41efbc` |

Reused from `datasets/fixtures/nlp1`:

| File | Issuer/source | Language | Category | Form | SHA-256 |
|---|---|---|---|---|---|
| `../nlp1/hindi/nfc_recruitment_01_2026_hindi.pdf` | Nuclear Fuel Complex, Department of Atomic Energy | Hindi | Recruitment | Digital/searchable, 20 pages | `2face8e0eb902016933910a7930238d67210ec4942fad262a526551b76a38d6a` |
| `../nlp1/telugu/ananthapuramu_anganwadi_recruitment_2025.pdf` | Women Development & Child Welfare Department, Ananthapuramu District | Telugu | Recruitment | Image-only, 10 pages | `6c629a75e959958859931e2a052712e760352bc2a2b261f91dd59f4acf0221b6` |

## Verification boundary

Content signature, page count, native-text availability, byte length and
SHA-256 were checked locally after download. Gold annotations separately mark
each field as complete, partial, unverified or template-only. A fixture being
real and official does not imply that all of its fields have been annotated.
