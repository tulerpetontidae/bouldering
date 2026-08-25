/* Pull every bouldering session out of Garmin Connect.
 *
 *   1. log in to Garmin Connect, open any page on connect.garmin.com
 *   2. paste this whole file into the devtools console
 *   3. it downloads garmin-raw.json — drop that next to build_data.py
 *
 * Garmin's internal API is same-origin and needs the connect-csrf-token header
 * that the app itself sends; cookies alone give 403. We read the token off a
 * request the app makes rather than hard-coding it.
 */
(async function () {
  const API = "https://connect.garmin.com/gc-api/";

  // grab the csrf token by watching one of the app's own fetches
  const token = await new Promise((resolve) => {
    const existing = document.cookie.match(/(?:^|;\s*)CSRF-TOKEN=([^;]+)/);
    if (existing) return resolve(decodeURIComponent(existing[1]));
    const orig = window.fetch;
    const timer = setTimeout(() => { window.fetch = orig; resolve(null); }, 8000);
    window.fetch = function (input, init) {
      try {
        const h = (init && init.headers) || {};
        const t = h["connect-csrf-token"] ||
                  (h.get && h.get("connect-csrf-token"));
        if (t) { clearTimeout(timer); window.fetch = orig; resolve(t); }
      } catch (e) { /* ignore */ }
      return orig.apply(this, arguments);
    };
    // nudge the app into making a request
    location.hash = "#_" + Date.now();
  });
  if (!token) throw new Error("no csrf token — navigate around the app and retry");

  const get = async (path) => {
    const r = await fetch(API + path, {
      credentials: "include",
      headers: { "connect-csrf-token": token },
    });
    if (!r.ok) throw new Error(path + " -> " + r.status);
    return r.json();
  };

  // every activity, then keep the climbing ones
  let all = [], start = 0;
  for (;;) {
    const batch = await get(`activitylist-service/activities/search/activities?limit=100&start=${start}`);
    if (!Array.isArray(batch) || !batch.length) break;
    all = all.concat(batch);
    start += batch.length;
    if (batch.length < 100) break;
  }
  const climbing = all
    .filter((a) => /bouldering|indoor_climbing/.test(a.activityType.typeKey))
    .sort((a, b) => new Date(a.startTimeLocal) - new Date(b.startTimeLocal));
  console.log(`${all.length} activities, ${climbing.length} climbing`);

  const sessions = [];
  for (let i = 0; i < climbing.length; i++) {
    const a = climbing[i];
    const ts = await get(`activity-service/activity/${a.activityId}/typedsplits`);
    const sp = (ts && ts.splits) || [];
    sessions.push({
      id: a.activityId, date: a.startTimeLocal, name: a.activityName,
      type: a.activityType.typeKey,
      dur: Math.round(a.duration), elapsed: Math.round(a.elapsedDuration || 0),
      cal: a.calories, bmr: a.bmrCalories, hr: a.averageHR, hrx: a.maxHR,
      ae: a.aerobicTrainingEffect, an: a.anaerobicTrainingEffect,
      load: a.activityTrainingLoad,
      modMin: a.moderateIntensityMinutes || 0, vigMin: a.vigorousIntensityMinutes || 0,
      bb: a.differenceBodyBattery,
      climbs: sp.filter((s) => s.type === "CLIMB_ACTIVE").map((s) => ({
        t: s.startTimeLocal,
        g: s.gradeValue ? s.gradeValue.valueKey : null,
        gs: s.gradeValue ? s.gradeValue.sortOrder : null,
        sc: s.gradeValue ? s.gradeValue.scale : null,
        ok: s.status === "CLIMB_COMPLETED" ? 1 : 0,
        d: Math.round(s.duration), hr: s.averageHR, hrx: s.maxHR, cal: s.calories,
      })),
      rests: sp.filter((s) => s.type === "CLIMB_REST").map((s) => Math.round(s.duration)),
    });
    if (i % 10 === 0) console.log(`  ${i + 1}/${climbing.length}`);
    await new Promise((r) => setTimeout(r, 100));   // be polite
  }

  const out = { generated: new Date().toISOString(), sessions };
  const climbs = sessions.reduce((n, s) => n + s.climbs.length, 0);
  console.log(`done: ${sessions.length} sessions, ${climbs} climbs`);

  const url = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url; link.download = "garmin-raw.json"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
})();
