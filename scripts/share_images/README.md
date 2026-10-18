# Share images

Standalone HTML sources of the images in `website/img/share/`, rendered with a headless browser at the page size set in each file's CSS:

| Source | Output | Size | Use |
| --- | --- | --- | --- |
| `directions.html` | `website/img/share/directions.png` | 1200 × 630 | `og:image` of the home pages and the roadmap (link previews) |
| `directions-4x5.html` | `website/img/share/directions-4x5.png` | 1080 × 1350 | LinkedIn post, English |
| `directions-4x5.fr.html` | `website/img/share/directions-4x5.fr.png` | 1080 × 1350 | LinkedIn post, French |

Render (Edge or Chrome, the fonts come from Google Fonts so the browser needs the network):

```
msedge --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=8000 --window-size=1200,630 --screenshot=directions.png directions.html
```

From WSL, copy the HTML to a Windows folder first and pass `wslpath -w` paths to `msedge.exe`.

## LinkedIn scenarios (captures of the real dock)

`scripts/fm5_linkedin_shots.py` drives the dock in QGIS 4.2 on the Estavar test data and saves one full-window
capture per scenario (`ln_<n>_<slug>.png`, 1760 × 1040 at 1.5×, the map rendered off-canvas) plus the dock alone
(`-panel.png`). `linkedin_shots.example.bat` is the Windows launcher used (isolated profile, minimised window,
the checkout copied as the plugin through `FM_REPO`); `linkedin_resize.py` (run with `python-qgis.bat`) makes the
1600 px JPEG and WebP in `website/img/share/linkedin/`; `linkedin_carousel.py <folder>` writes `carousel.html`
and `carousel.fr.html` (seven 1080 × 1350 pages) that Edge prints to `filtermate5-scenarios[.fr].pdf`:

```
msedge --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=10000 --print-to-pdf=carousel.fr.pdf carousel.fr.html
```

| Scenario | Source → targets | Result on the test tile |
| --- | --- | --- |
| 1 `routes_batiments` | main roads (`"importance" = '4'`, 15 segments), 50 m → buildings, parcels | 39 buildings, 11 parcels |
| 2 `eglise_mnt_lidar` | the church, 50 m → DTM, LiDAR HD | clipped VRT, derived COPC |
| 3 `pente_parcelles` | DTM slope ≥ 20 % → parcels, coverage 50 % | 2 parcels |
| 4 `ndvi_parcelles` | CIR orthophoto, NDVI > 0.3 → parcels, coverage 50 % | 7 parcels |
| 5 `vegetation_routes` | LiDAR class 5, 3 m → road segments | 100 of 131 segments |
