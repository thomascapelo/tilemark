# tilemark — brand assets

Copy this folder to `docs/brand/` in the repo.

## Files

| File | Use |
|---|---|
| `logo.svg` / `logo-dark.svg` | README header (light / dark theme) |
| `icon.svg` / `icon-light.svg` | Symbol alone, for light / dark backgrounds |
| `favicon.svg` | Simplified symbol (larger bars) for 16–32 px |
| `png/favicon-16.png`, `png/favicon-32.png` | PNG favicons |
| `png/apple-touch-icon.png` | 180 × 180 |
| `png/icon-512.png` | Avatar, app icon |
| `png/logo-2x.png`, `png/logo-dark-2x.png` | Raster lockups |
| `png/social-preview.png` | GitHub social preview, 1280 × 640 |

All SVGs are self-contained: the wordmark is outlined, so no font is needed.

## README header

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/logo-dark.svg">
    <img src="docs/brand/logo.svg" alt="tilemark" height="64">
  </picture>
</p>
```

## Social preview

GitHub → repo **Settings** → **General** → **Social preview** → upload `png/social-preview.png`.

## Favicon (future site)

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
```

## Palette

- Ink `#101419`
- Paper `#fbfaf8`
- Accent `#e2553a`

Typeface: Geist SemiBold, tracking −4.5 %. Bars rotated −30°, matching the watermark angle.
