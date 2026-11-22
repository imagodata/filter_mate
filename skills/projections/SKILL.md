---
name: projections
title: Choose the projection of the map
description: the CRS that suits the data and the purpose of the map, or one made for them
metadata:
  version: 1
  plugin_min: 5.2.0
  audience: chat, mcp
  tools: suggest_crs, set_project_crs, map_context, describe_layer, list_layers, export_layers
  risk: change
  trust: builtin
---

# Choose the projection of the map

Every flat map alters the Earth: a projection keeps either the areas (equal-area), the shapes and angles
(conformal), the distances from one point (equidistant), or a compromise (the look of a world map). The map follows
the CRS of the project; the layers are reprojected on the fly and their data never change.

## Method

1. What the map is for, in the user's words:
   - areas, densities, a choropleth, surfaces measured: purpose areas (equal-area);
   - distances, buffers, routes, a radius around a place: purpose distances;
   - a local map, a survey, angles, navigation: purpose shapes (conformal);
   - the whole world: purpose world; a map over web basemaps only: purpose web;
   - nothing said: purpose general (the official system of the country first).
2. suggest_crs with that purpose (layers when the map is about some of them only). It reads where the data lie and
   answers candidates, best first, each with what it keeps and why.
3. Take the first one unless the user said otherwise, set_project_crs with its crs exactly as given (a PROJ: string
   included), and tell the user in one sentence what it keeps and what it alters.
4. A projection made for the data (PROJ: +proj=aea, lcc, laea, aeqd, tmerc, stere) is right for a region no official
   system covers well: several countries, a sea, a range of mountains. Say it is made for this extent.

## Rules of thumb

- France: Lambert-93 (EPSG:2154) for the country; a Lambert CC zone (CC42 to CC50) for a small area where lengths
  matter; overseas territories have their own (Réunion EPSG:2975, Antilles EPSG:5490, Guyane EPSG:2972...).
- Europe: LAEA (EPSG:3035) for statistics and areas, LCC (EPSG:3034) for shapes.
- The world: Equal Earth (EPSG:8857) for thematic maps, Robinson (ESRI:54030) for a general one. Web Mercator
  (EPSG:3857) only under web basemaps: its areas swell towards the poles.
- Degrees (EPSG:4326) are no projection: never for measuring nor for a printed map.
- A file in another CRS is written only when the user asks for files: export_layers with crs.

## What never to do

- Never reproject the data of a layer to change how the map looks: set_project_crs is enough.
- Never choose Web Mercator for areas or distances, nor an equal-area projection for a navigation map.
