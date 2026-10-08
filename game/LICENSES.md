# Licenses and attribution

## Map-derived data

© OpenStreetMap contributors. OSM-derived road positions, footprint coordinates and their adapted navigation data are available under the Open Data Commons Open Database License (ODbL) 1.0.

- https://www.openstreetmap.org/copyright
- https://opendatacommons.org/licenses/odbl/1-0/
- Derived navigation dataset: `data/campus-navigation.json`
- Runtime map data: relevant road/footprint coordinate portions of `dist/world-config.js`

This database attribution does not assert that the entire game, original architectural details, character geometry or vehicle geometry is licensed under ODbL. These are separate original reconstruction/game assets. The visual campus model incorporates OSM-derived spatial layout; buildings and terrain are approximate, not an official surveyed BIM.

Official building names and reference directory: https://www3.chosun.ac.kr/campusMap/chosun/view.do

## Three.js

Three.js 0.180.0, MIT. Full license: `dist/vendor/THREE-LICENSE.txt`.
The vendored Octree has a small documented performance patch limiting subdivision to six levels and setting 32 triangles per leaf.

## Meshoptimizer

Meshoptimizer decoder, MIT. Full license: `dist/vendor/MESHOPT-LICENSE.txt`.
Used to decode the compressed campus GLB in the browser.

## Build-time tools

The source compression script uses glTF Transform and meshoptimizer from npm under their respective MIT licenses. Their package licenses are installed with the dependencies. These tools are not remotely loaded by the game.

## Shuttle visual references

Official university publications were used as visual references for original modeled geometry and lettering. Reference photographs/PDFs are not embedded or redistributed in this source package.

- Minju Chosun, published 2025-10-15, page 77: https://eng.chosun.ac.kr/sites/chosun/files/2025_%EB%AF%BC%EC%A3%BC%EC%A1%B0%EC%84%A0_%EA%B5%90%EC%A7%80%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80%EC%9A%A9.pdf
- Chodae Newspaper issue 1178, published 2026-05-11, page 6: https://www3.chosun.ac.kr/magazine/chnews/175/setupFileDownload.do
- Official shuttle route guide: https://mall.chosun.ac.kr/chosun/160/subview.do
- Dated route notice, 2023-04-26: https://csu.chosun.ac.kr/bbs/global/417/250328/artclView.do

Publication dates are not necessarily photograph capture dates. Current fleet-wide appearance, exact stop positions and current service operation are not certified by this game.

## Adapted terrain data

produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved

Source: public Copernicus GLO-30 AWS 2021 release, tile N35 E126. Broad surface-elevation trends were roof-masked, smoothed, converted to the local frame, and modified for building pads and road beds. This is an adapted approximate terrain, not surveyed bare earth or certified access gradients.

- https://registry.opendata.aws/copernicus-dem/
- https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf
