# Reference IR captures (protocol ground truth)

Curated, de-duplicated subset of the local capture corpus, copied here from
the gitignored `captures/*.txt` scratch files so the protocol fixtures are
version-controlled. Each file is a real capture of the ActronAir remote
decoded by the ESP8266 + IRremoteESP8266 (see `re-findings.md`).

Selection: one clean, valid-decode capture per documented state. The physical
remote is the only way to regenerate these, so treat them as fixtures —
cross-checked against the `include/bosch144_protocol.h` unit tests.

Notes:
- Temp sweep (`temp-16`..`temp-26`, COOL mode) shares the `3FC0` prefix; the
  temperature nibble varies. Half-degree variants (`16.5`, `18.5`) exercise the
  byte-14 bit-5 half-degree flag.
- `power-on` (3FC0) vs `power-on-2`/`power-button` (BF40) capture different base
  states; both retained intentionally.
- COOLIX commands are discrete toggles: power-off `0xB27BE0`, swing `0xB9F504/5`
  (alternating), boost `0xB9F501`, LED `0xB9F509`.
- No valid `temp-28` capture exists (both bench attempts failed to decode) —
  this is the open item flagged for F1.5 bench verification.

| Fixture | Protocol | Decoded code | Bits | Original capture |
|---------|----------|--------------|------|------------------|
| `boost-button-coolix.txt` | COOLIX | `0xB9F501` | 24 Bits | `20251229_145919_boost-button.txt` |
| `fan-press-1.txt` | BOSCH144 | `0xB24DFF0020DFB24DFF0020DFD514000000E9` | 144 Bits | `20251228_153501_fan-press-1.txt` |
| `fan-press-2.txt` | BOSCH144 | `0xB24D9F6020DFB24D9F6020DFD528000000FD` | 144 Bits | `20251228_153530_fan-press-2.txt` |
| `fan-press-3.txt` | BOSCH144 | `0xB24D5FA020DFB24D5FA020DFD53C00000011` | 144 Bits | `20251228_153548_fan-press-3.txt` |
| `fan-press-4.txt` | BOSCH144 | `0xB24D3FC020DFB24D3FC020DFD55000000025` | 144 Bits | `20251228_153621_fan-press-4.txt` |
| `fan-press-5.txt` | BOSCH144 | `0xB24D3FC020DFB24D3FC020DFD56400000039` | 144 Bits | `20251228_153656_fan-press-5.txt` |
| `fan-press-6-back-to-auto.txt` | BOSCH144 | `0xB24DBF4020DFB24DBF4020DFD5660000003B` | 144 Bits | `20251228_153724_fan-press-6-back-to-auto.txt` |
| `led-button-coolix.txt` | COOLIX | `0xB9F509` | 24 Bits | `20251229_145934_led-button.txt` |
| `mode-press-1-dry.txt` | BOSCH144 | `0xB24D1FE024DBB24D1FE024DBD5650000003A` | 144 Bits | `20251228_153224_mode-press-1.txt` |
| `mode-press-2-heat.txt` | BOSCH144 | `0xB24DBF402CD3B24DBF402CD3D5660000003B` | 144 Bits | `20251228_153253_mode-press-2.txt` |
| `mode-press-3.txt` | BOSCH144 | `0xB24DBF40E41BB24DBF40E41BD5660000003B` | 144 Bits | `20251228_153316_mode-press-3.txt` |
| `mode-press-4.txt` | BOSCH144 | `0xB24D1FE028D7B24D1FE028D7D5650000003A` | 144 Bits | `20251228_153337_mode-press-4.txt` |
| `mode-press-5-back-to-cool.txt` | BOSCH144 | `0xB24DBF4020DFB24DBF4020DFD5660000003B` | 144 Bits | `20251228_153409_mode-press-5-back-to-cool.txt` |
| `power-button.txt` | BOSCH144 | `0xB24DBF4040BFB24DBF4040BFD5662000005B` | 144 Bits | `20251229_145719_power-button.txt` |
| `power-off-coolix.txt` | COOLIX | `0xB27BE0` | 24 Bits | `20251229_145838_power-off.txt` |
| `power-on-2.txt` | BOSCH144 | `0xB24DBF4040BFB24DBF4040BFD5662000005B` | 144 Bits | `20251229_145901_power-on-2.txt` |
| `power-on.txt` | BOSCH144 | `0xB24D3FC040BFB24D3FC040BFD56400000039` | 144 Bits | `20251228_085537_power-on.txt` |
| `swing-test-coolix-a.txt` | COOLIX | `0xB9F504` | 24 Bits | `20251228_155349_swing-test.txt` |
| `swing-test-coolix-b.txt` | COOLIX | `0xB9F505` | 24 Bits | `20251228_155423_swing-test-2.txt` |
| `temp-16.5.txt` | BOSCH144 | `0xB24D3FC000FFB24D3FC000FFD56420100069` | 144 Bits | `20251228_091732_temp-16.5-retry.txt` |
| `temp-16.txt` | BOSCH144 | `0xB24D3FC000FFB24D3FC000FFD56400100049` | 144 Bits | `20251228_091151_temp-16.txt` |
| `temp-18.5.txt` | BOSCH144 | `0xB24D3FC010EFB24D3FC010EFD56420000059` | 144 Bits | `20251228_091832_temp-18.5.txt` |
| `temp-18.txt` | BOSCH144 | `0xB24D3FC010EFB24D3FC010EFD56400000039` | 144 Bits | `20251228_091759_temp-18.txt` |
| `temp-20.txt` | BOSCH144 | `0xB24D3FC020DFB24D3FC020DFD56400000039` | 144 Bits | `20251228_085719_temp-20.txt` |
| `temp-22.txt` | BOSCH144 | `0xB24D3FC0708FB24D3FC0708FD56400000039` | 144 Bits | `20251228_092757_temp-22.txt` |
| `temp-24.txt` | BOSCH144 | `0xB24D3FC040BFB24D3FC040BFD56400000039` | 144 Bits | `20251228_085741_temp-24.txt` |
| `temp-26.txt` | BOSCH144 | `0xB24D3FC0D02FB24D3FC0D02FD56400000039` | 144 Bits | `20251228_092834_temp-26.txt` |
| `temp-max-cool.txt` | BOSCH144 | `0xB24D3FC0B04FB24D3FC0B04FD56400000039` | 144 Bits | `20251228_092000_temp-max-cool.txt` |
