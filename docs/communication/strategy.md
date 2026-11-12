# FilterMate communication strategy

## Objective

Increase qualified discovery and trial of FilterMate by showing how its spatial filtering system solves recognizable QGIS tasks. Treat the first articles as experiments: test which use cases attract the right readers before committing to a long publishing calendar.

## Positioning

**FilterMate connects a spatial source to one or more target layers — across vectors, rasters and LiDAR — with an explicit spatial relationship and inspectable settings.**

Lead with the spatial question and visible result. Explain the mechanism behind it: source, target, predicate, buffer, coverage or filter combination. Present FilterMate as the means to reproduce the workflow, not as the story by itself.

## Website marketing: from question to final deliverable

The strongest differentiator to bring forward is the **workflow**, not another list of supported layer types:

> **Ask a spatial question. Chain the filters. Export the answer.**

Show how a GIS analyst can progressively refine a project across multiple filtering steps, inspect each state, undo or redo, and export the final visible results as deliverable layers. The value is avoiding a trail of manually created and exported intermediate datasets just to move from one step to the next.

### Suggested English homepage copy

**Headline:** From spatial question to finished deliverable.

**Subhead:** Chain spatial filters across your QGIS layers, inspect and refine every step, then export only the results your analysis needs.

**Supporting line:** Keep the workflow in your QGIS project—not in a folder full of intermediate exports.

**Primary CTA:** See a chained workflow  
**Secondary CTA:** Install FilterMate

### Suggested French copy

**Titre :** De la question spatiale au livrable final.

**Sous-titre :** Enchaînez les filtres dans votre projet QGIS, vérifiez et affinez chaque étape, puis exportez les seules couches qui répondent à votre question.

**Phrase d’appui :** Gardez le fil de l’analyse dans votre projet, sans multiplier les exports intermédiaires.

**CTA principal :** Voir un workflow enchaîné  
**CTA secondaire :** Installer FilterMate

### Homepage story and visual sequence

Build one new flagship demonstration specifically around a multi-step question; do not repackage any existing published use case. The page should tell the workflow in four visible states:

1. **The question** — state the practical decision the analysis should inform.
2. **The chain** — show each source, target, predicate, and AND / OR / AND NOT choice in order; explain what each step adds or removes.
3. **The living project** — show intermediate filter states in the same QGIS project, with results inspectable and Undo / Redo available. Make clear these are filtered views of the project layers, not a series of manually exported copies.
4. **The answer** — show the final map and export of only the final filtered layers, optionally as a GeoPackage with styles and the QGIS project embedded.

Use an animated or short screen-recorded before/during/after sequence rather than a static feature matrix alone. Pair it with a compact flow diagram:

`Question → source selection → chained filters → inspect / refine → final filtered layers → export`

The example must demonstrate actual successive FilterMate operations and clearly identify which layers are filtered at each step. The current Kathmandu SRTM + OSM draft proposes a two-stage workflow, but it is not proof until it has been run and captured in QGIS. Validate the actual source and target selections before producing the homepage hero demonstration.

### Claim accuracy

Avoid the unqualified claim **“everything stays in memory”** or **“all processing is in-memory.”** For vector layers, FilterMate applies subset filters through the data provider; features are not copied or deleted during filtering. Raster and point-cloud filters are clipped to temporary files while active. Prefer **“no manually exported intermediate layers”** or **“keep intermediate filter states in the QGIS project”**; explain the raster / point-cloud temporary-file behavior where relevant.

The final export is a deliberate materialization step: it writes the currently visible, filtered features of the selected layers to the chosen output format. Do not imply that filtering alone creates a permanent result layer or that source data have been altered.

## Favorites, shared filter library, and field delivery

Market the reusable-workflow story as a second proof point for the same end-to-end promise:

1. **Save a filter as a project favorite.** A favorite stores a reusable filter configuration (source, selection, predicates, buffer, targets and related settings). Favorites can be scoped to the current project or made global, and project favorites travel with the QGIS project. Describe them as **saved filter recipes** or **bookmarks for spatial questions**; do not imply one favorite automatically captures an arbitrary multi-step history.
2. **Share a curated library.** Users can import/export favorites as JSON. With the optional QGIS Resource Sharing plugin, teams can browse shared Git-backed collections, fork a recipe into the current project, and publish favorites to a configured collection. Explain that this is a QGIS desktop workflow and that the Resource Sharing plugin is an optional dependency.
3. **Take the filtered deliverable to the field.** The optional QFieldCloud extension exports the currently filtered layers, builds a QFieldSync-compatible project and pushes the package to QFieldCloud, where it can be prepared for QField clients. This is not FilterMate running inside the QField mobile app; describe it as a bridge from desktop filtering to field delivery.

### Suggested website message

**Headline:** Save the filter. Share the recipe. Take the result to the field.

**Body:** Keep reusable filters with a QGIS project, browse and share team recipes through Resource Sharing, then send the filtered layers to QFieldCloud for field work.

**Visual sequence:** choose a project favorite → apply and inspect the filtered layers → browse/fork a shared recipe (optional Resource Sharing) → export and push the filtered project to QFieldCloud (optional QFieldSync/QFieldCloud) → open the prepared project in QField.

Keep the optional dependencies visible in the copy and CTA. A concise link can lead to setup instructions for the two extensions. Use distinct labels for the three things users are saving or sharing: a filter favorite, the exported dataset/project, and the QFieldCloud mobile project.

## Audience hypotheses

- GIS analysts and consultants who repeat spatial selection and data-preparation tasks.
- Local authorities and infrastructure teams who need to inspect or prepare geographically scoped data.
- Advanced QGIS users working with mixed vector, raster and point-cloud data.

These are starting hypotheses, not validated audience research.

## Editorial series: “One spatial question, one filter”

Each article should make one capability tangible through a **new, original case**, not reuse a scenario, result, or screenshots already published on the website or in existing communication assets. Before drafting, choose a distinct audience problem and verify that the underlying data and workflow can support it.

The first article uses a **global, openly accessible data workflow outside France**: SRTM terrain around Kathmandu, Nepal, to filter OpenStreetMap roads on a slope threshold, then use those filtered roads to find nearby OSM schools. The draft is in `medium/01-open-data-srtm-osm.md`. It demonstrates an actual two-step filtering story and ends with exporting only the final filtered layers. The counts and new QGIS screenshots remain pending a fresh, end-to-end run; do not publish results before that validation. Data acquisition is documented in the draft and publication guide; SRTM is free to download through EarthExplorer (free account required), and QuickOSM provides an area-scoped route to OSM features.

### Companion video — first master delivered

The new Kathmandu example now has a screen-recorded master at `medium/kathmandu-demo/video/Kathmandu_FilterMate_Walkthrough.mp4` and a production record in `medium/video-storyboard.md`.

- The 55.5-second, 16:9, 1080p video was captured from the actual QGIS / FilterMate window on screen 1.
- It shows **Single selection**, **Multiple selection**, and **Custom selection / expression** as alternative source modes, plus the Zoom and Selecting preview pushbuttons.
- It shows the verified chain **SRTM-derived raster → OSM roads → filtered roads → OSM schools**, then exports a GeoPackage containing the final results.
- The captured example returned 4 roads and 4 schools from the bundled study extent; these are example counts, not a general claim.
- English captions are burned in; French subtitles are supplied separately. There is no narration or music.
- A voice-over version and a 30–45 second social edit remain optional follow-up work.

The article and publication guide list the video, screenshots, project and final GeoPackage. Keep the selection modes presented as alternatives, preserve the OSM / SRTM credits, and do not describe the illustrative settings as access, hazard or safety standards.

Further directions to develop into genuinely new cases:

- A multi-stage workflow combining a spatial filter with attribute criteria and a saved/reusable filter.
- A new vector-to-raster or raster-to-vector operational question, using a distinct dataset and measured outcome.
- A project-specific investigation where AND / OR / AND NOT changes which targets are retained.
- A repeatable Processing/model workflow that applies a new filter configuration to a fresh study area.

These are ideas only, not claims that a demonstration or result already exists. Do not draft an article until a new case and its data have been selected and validated. Never combine separate demonstrations into a claim that they were one operation.

## Distribution workflow

For each article based on an approved, new case:

1. Publish a useful, self-contained English explainer on Medium; link to the relevant guide, use case and repository.
2. Create one LinkedIn post with the strongest result and a direct link to the article.
3. Recut the same material into a short screen recording showing the source, target, key filter setting and result.
4. Share selectively in relevant QGIS/GIS communities, following each community's rules and leading with the tutorial rather than a promotional pitch.
5. Keep article, captions and social copy factually consistent; adapt length and format, not the underlying claim. Avoid reusing previously published examples and images.

Start with one article, observe its performance, then aim for one new use case every two to three weeks if the workflow is sustainable. Reuse verified screenshots and data rather than creating new assets for every channel.

## Measurement

Record per article, where the platform exposes the data:

- views and reads / read ratio;
- reactions, comments and useful practitioner feedback;
- clicks to the FilterMate guide and repository;
- attributable repository engagement or installs only when a reliable measure exists.

Do not treat views alone as successful adoption. Use reader questions and link activity to choose the next use case. If links are tagged for analytics, keep the same canonical destination and document the campaign parameters.

## Editorial guardrails

- Prefer verified counts, settings and screenshots from the new case; label one-off timings as observations, not benchmarks.
- State the target scope, data context and relevant limitations.
- Do not overstate a screening result as a diagnosis, safety finding or intervention recommendation.
- Attribute source datasets and retain their applicable licence notices.
- Make the next step clear: reproduce the workflow, read the guide, or try FilterMate.
