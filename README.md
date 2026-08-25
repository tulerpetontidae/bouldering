# Bouldering progress log

A single static page tracking every boulder my Garmin has recorded — grades tried,
grades sent, and whether the level is actually moving.

Live at **https://tulerpetontidae.github.io/bouldering/**

## Files

| File | What it is |
|---|---|
| `index.html` | The whole site. No build step, no dependencies. |
| `data.json` | What the page reads. Generated — don't hand-edit. |
| `garmin-raw.json` | Raw scrape from Garmin Connect, one record per climb. |
| `build_data.py` | `garmin-raw.json` → `data.json`. |
| `scrape.js` | Browser snippet that produces `garmin-raw.json`. |

## Refreshing the data

Garmin has no usable public API for this, and its internal one needs the
browser's session, so the scrape runs in the browser:

1. Log in to Garmin Connect and open any page on `connect.garmin.com`.
2. Paste `scrape.js` into the devtools console. It walks every activity, pulls
   the per-climb splits, and downloads `garmin-raw.json`.
3. Drop that file in here and run:

   ```
   python3 build_data.py
   ```

4. Commit `garmin-raw.json` and `data.json`.

## What Garmin actually records

The `bouldering` activity type logs one split per climb, which is what makes any
of this possible:

```json
{ "type": "CLIMB_ACTIVE", "status": "CLIMB_COMPLETED",
  "gradeValue": { "valueKey": "V4", "sortOrder": 5, "scale": "VERMIN" },
  "duration": 28.2, "averageHR": 122, "maxHR": 139, "calories": 3 }
```

Rests come through as `CLIMB_REST` splits, so time-on-wall vs time-resting is
real rather than inferred.

## Grades

Almost everything is V-scale (`VERMIN`). One session (28 Nov 2025) was logged at
a gym grading in Japanese kyu; those are converted with the standard table in
`build_data.py` (5級→V2, 4級→V3, 3級→V4) and marked 🇯🇵 on the page. The
conversion is approximate and gym-dependent.

Roped climbing (`indoor_climbing`, YDS) is excluded — different scale, different
sport.

## Colour

Chart colours come from a validated palette rather than taste. The two
categorical hues (`#2a78d6` / `#eb6834` light, `#3987e5` / `#d95926` dark) pass
the lightness-band, chroma, colour-vision-deficiency separation, normal-vision
and contrast checks against this page's own surfaces. The heatmap and the grade
bands use a single-hue sequential ramp, light→dark, so darker always means more.

Dark mode is a selected set of steps for the dark surface, not an inverted
light palette.
