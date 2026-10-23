# Navigation and country exploration

Accepted choices (23 October 2026): `1C 2A 3A 4A 5A 6A 7A 8A 9A 10A 11A 12A 13A 14C 15A 16A 17C 18A 19A 20C`.

- Entry: choose between reading the research and exploring mobility; retain the galaxy and rounded visual language.
- Desktop: labelled left sidebar. Continuous page with anchors; Research, Explore mobility, Data & methods. Only the active group's topics expand automatically.
- Mobile: the same navigation and country selector in a keyboard-accessible drawer.
- One selected-country control, pinned above navigation. No default or remembered country on a fresh visit. An explicit shared URL restores its country.
- Outgoing and incoming views use the same original flow records; incoming partners are origin countries. GDP gaps retain their original destination-minus-origin meaning.
- Europe overview is independent of country selection. Mobility totals retain the source records, including observations with missing country codes. Country counts use available codes.
- Local university/partner filters update the compatible map, partner chart, table and scatter. National context, grants, research estimates and the separate historical panel keep explicit unfiltered scope labels.
- Filters combine with AND. Changing country or direction clears unsupported filter values and keeps compatible ones. Reset clears filters while retaining country and direction.
- Salary follows the selected country unless the visitor chooses a clearly labelled comparison override. Missing coverage is an empty state with available alternatives, never a silent country substitution.
- Share links contain country, direction, section, endpoint filters, table aggregation, row search, and salary override/unit. Browser Back/Forward restores these states. Country choice is not saved in local storage.
- Data tables lead with primary columns; additional economic fields, university names and text evidence expand into full-width detail rows.

## Implementation and validation

`dashboard/ui/mobility.js` contains pure state/aggregation helpers. `dashboard/ui/explorer.js` owns the UI state, scope labels, navigation and renderers. `dashboard/ui/explorer.css` owns the sidebar and responsive presentation. The Python builder inlines these into the self-contained HTML; no frontend runtime dependency or extra deployment service was added.

The original country-flow, university-flow and historical-panel snapshots are separate datasets. University filters switch compatible views to explicitly labelled university records; they do not rewrite the national baseline or imply university-level grants/history. Research coefficients are never re-estimated by choosing a country.

Node checks: `node tests/mobility.cjs` and `node tests/dashboard-presentation.cjs`. Browser acceptance covers initial no-country state, both directions, arithmetic against the source payload, filters, missing salary coverage, row expansion, URL reload and history, country changes, Europe entry, mobile drawer, responsive overflow, and payload immutability. Repository and production payloads must be preserved independently when rendering/deploying.
