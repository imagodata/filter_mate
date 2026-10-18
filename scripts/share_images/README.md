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
