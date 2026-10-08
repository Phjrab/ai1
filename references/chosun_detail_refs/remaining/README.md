# Campus building audit, 2026-10-08

## Delivered research
- `building_checklist_62.json`: every one of the existing 62 modeled building records, indexed by official destination ID and OSM footprint ID. Includes photo evidence, floor directory, observed exterior features, entrance-stair evidence, and unresolved details.
- `additional_destinations.json`: 16 official destinations outside those 62 records, including dental research building #139 and dental hospital #166. Not all are buildings to add: #179 duplicates Seoseok Hall and #168 is the sports field.
- `dental_footprints.json`: original official pins and mapped footprints for #139, #152 and #166. #139 and #152 share one compound OSM footprint and must not be independently extruded in full.
- Numbered HTML/JPG files: live official campus-map pages and their reference photos. Photos were opened individually or in labeled contact sheets. Research reference only; do not embed these images as textures or redistribute them in a model package.

## High-priority corrections
Solmaru #143 is a three-floor brick-and-concrete split-level composition with a curved brick corner and large open pale rectangular frames. Haeoreum #128 has two listed occupied floors plus a tall auditorium volume, white stepped cuboids, teal curtain wall and yellow entry frame. They are not generic four-storey office buildings.

Dental Teaching #152 has six listed floors; Dental Research #139 has five. They occupy adjoining parts of one mapped complex. Dental Hospital #166 is a separate five-floor building in a separate OSM footprint, with pale facade, deep upper colonnade and distinctive teal circular side windows. It was explicitly excluded in the original manifest.

Open-air Theater #167 is a low stage/canopy with curved stepped seating, not a four-storey solid. Parking Building #164 is open-sided with bright blue fascia. Experimental Workshop #158 has industrial high-ceiling massing and exterior metal stair/landing. Startup Incubator #153 has a curved full-height glazed entrance bay.

## Limits
Official pages were fetched live; most supplied photo URLs contain 2019 timestamps. Live retrieval does not establish that every facade is unchanged in 2026. Directory floor counts represent listed occupied floors and must be reconciled with visual volume, sloping ground, annexes and high-ceiling halls. In particular, #132 lists 11 levels but its large gym mass should not be stretched arbitrarily.

39 of the 62 building records have a directly inspected, specific official photo (some duplicate physical wings share a destination photo). Five CIT records were reviewed against official group photos #169/#170, without secure individual wing attribution. Eighteen auxiliary OSM records have no secure photo/name correspondence. Those should remain transparently estimated; do not invent exact details to claim complete photo verification.

Stair width, exact riser counts, landing depths and rail dimensions are not survey measurements. Photos clearly support short entrance flights, forecourts, handrails and some external metal staircases, but often vegetation/angle prevents reliable counting. #144 visibly includes an entry ramp with rails. #158 visibly includes one exterior straight flight to an upper landing/connector. Ground alignments and hidden faces remain approximate.
