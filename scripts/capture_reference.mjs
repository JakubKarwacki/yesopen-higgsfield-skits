// Capture a reference short for private analysis: metadata, frames every `step` seconds and
// the transcript. Runs inside Ego Browser's embedded Node runtime, which does not see the shell's
// environment, so start it with the launcher next to this file:
//
//   scripts/capture-reference "https://www.youtube.com/watch?v=<id>" <project>/reference/private [--step 1.25] [--start 0.2] [--space ID]
//
// The launcher prepends `const REF = {url, out, step, start, space};` to this file and pipes it to
// `ego-browser nodejs`. Writes <out>/metadata.json, <out>/frames/f_<centiseconds>.jpg and
// <out>/transcript.txt. Keep <out> out of git and never publish it: it is someone else's video.
const fs = await import("node:fs/promises");
const cfg = (typeof REF !== "undefined" && REF) || {
  url: process.env.REF_URL, out: process.env.REF_OUT, step: process.env.REF_STEP,
  start: process.env.REF_START, space: process.env.REF_SPACE,
};
const url = cfg.url;
const out = cfg.out;
if (!url || !out) {
  console.log("no url or output folder: start this file with scripts/capture-reference <url> <out>");
  process.exit(2);
}
const step = Number(cfg.step || 1.25);
const start = Number(cfg.start || 0.2);
await fs.mkdir(`${out}/frames`, { recursive: true });

const task = cfg.space ? await taskSpace(Number(cfg.space)) : await taskSpace("Reference short capture");
const page = task.page("p1");
console.log({ taskSpaceId: task.spaceId });
// Background tabs throttle video decoding; pretend the tab is focused and active.
await page.cdp("Emulation.setFocusEmulationEnabled", { enabled: true });
await page.cdp("Page.setWebLifecycleState", { state: "active" });
// Keep the user's speakers quiet.
await page.cdp("Page.addScriptToEvaluateOnNewDocument", {
  source: `(() => { const p = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function (...a) { try { this.muted = true; } catch (e) {} return p.apply(this, a); }; })();`,
});
const watchUrl = url.replace(/youtube\.com\/shorts\/([A-Za-z0-9_-]+)/, "youtube.com/watch?v=$1");
await page.goto(watchUrl);
await page.waitForLoadState();
await page.waitForTimeout(3000);

const meta = await page.evaluate(() => {
  const r = window.ytInitialPlayerResponse;
  if (!r) return { error: "no ytInitialPlayerResponse", url: location.href };
  const v = r.videoDetails || {};
  const m = r.microformat?.playerMicroformatRenderer || {};
  const tracks = r.captions?.playerCaptionsTracklistRenderer?.captionTracks || [];
  return {
    url: location.href, videoId: v.videoId, title: v.title, author: v.author, channelId: v.channelId,
    lengthSeconds: Number(v.lengthSeconds), viewCount: Number(v.viewCount), keywords: v.keywords,
    description: v.shortDescription, publishDate: m.publishDate, category: m.category,
    captionTracks: tracks.map((t) => ({ lang: t.languageCode, kind: t.kind || "manual", name: t.name?.simpleText })),
  };
});
meta.capturedAt = new Date().toISOString();
await fs.writeFile(`${out}/metadata.json`, JSON.stringify(meta, null, 1));
console.log({ title: meta.title, author: meta.author, seconds: meta.lengthSeconds, views: meta.viewCount });

// Wait out a pre-roll ad (skip it when the button appears).
for (let i = 0; i < 90; i++) {
  const ad = await page.evaluate(() => {
    const mp = document.querySelector("#movie_player");
    const showing = !!mp?.classList.contains("ad-showing");
    if (showing) document.querySelector(".ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern")?.click();
    return showing;
  });
  if (!ad) break;
  await page.waitForTimeout(1000);
}

// Frames: seek, wait for the decoded frame, draw it to a canvas.
const duration = await page.evaluate(() => {
  const mp = document.querySelector("#movie_player");
  try { mp.mute(); mp.pauseVideo(); } catch (e) {}
  return mp?.getDuration?.() || 0;
});
let saved = 0;
for (let t = start; t < (duration || meta.lengthSeconds || 60) - 0.1; t += step) {
  const r = await page.evaluate(async (t) => {
    const mp = document.querySelector("#movie_player");
    const v = document.querySelector("video");
    mp.pauseVideo();
    await new Promise((resolve) => {
      const done = () => { v.removeEventListener("seeked", done); resolve(); };
      v.addEventListener("seeked", done);
      mp.seekTo(t, true);
      setTimeout(done, 8000);
    });
    for (let i = 0; i < 60 && v.readyState < 2; i++) await new Promise((r) => setTimeout(r, 100));
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext("2d").drawImage(v, 0, 0);
    try { return { data: c.toDataURL("image/jpeg", 0.85), ct: v.currentTime, w: c.width, h: c.height }; }
    catch (e) { return { err: String(e) }; }
  }, +t.toFixed(2));
  if (r.err) { console.log("frame error at", t, r.err); break; }
  const name = `f_${String(Math.round(t * 100)).padStart(5, "0")}.jpg`;
  await fs.writeFile(`${out}/frames/${name}`, Buffer.from(r.data.split(",")[1], "base64"));
  saved++;
}
console.log({ frames: saved, step });

// Transcript: the "Show transcript" panel under the description; caption scraping as a fallback.
const opened = await page.evaluate(async () => {
  document.querySelector("#movie_player")?.pauseVideo();
  document.querySelector("tp-yt-paper-button#expand, #description-inline-expander #expand")?.click();
  await new Promise((r) => setTimeout(r, 800));
  const btn = [...document.querySelectorAll("button, ytd-button-renderer, yt-button-shape")]
    .find((b) => /show transcript|pokaż transkrypcję|transkrypcj|transkript/i.test(b.textContent || b.getAttribute("aria-label") || ""));
  if (!btn) return false;
  (btn.querySelector("button") || btn).click();
  return true;
});
let lines = [];
for (let i = 0; i < 30 && opened && lines.length === 0; i++) {
  await page.waitForTimeout(500);
  lines = await page.evaluate(() => [...document.querySelectorAll("ytd-transcript-segment-renderer, transcript-segment-view-model")]
    .map((s) => s.innerText.replace(/\s+/g, " ").trim()));
}
if (!lines.length) {
  await page.evaluate(() => document.querySelector(".ytp-subtitles-button[aria-pressed='false']")?.click());
  let last = "";
  for (let t = 0; t <= (duration || 60); t += 0.5) {
    const cap = await page.evaluate(async (t) => {
      const mp = document.querySelector("#movie_player");
      const v = document.querySelector("video");
      await new Promise((res) => { const d = () => { v.removeEventListener("seeked", d); res(); }; v.addEventListener("seeked", d); mp.seekTo(t, true); setTimeout(d, 4000); });
      await new Promise((r) => setTimeout(r, 250));
      return [...document.querySelectorAll(".ytp-caption-segment")].map((s) => s.textContent).join(" | ");
    }, +t.toFixed(1));
    if (cap && cap !== last) { lines.push(`${t.toFixed(1)}s ${cap}`); last = cap; }
  }
}
await fs.writeFile(`${out}/transcript.txt`, lines.join("\n") + "\n");
console.log({ transcriptLines: lines.length, source: opened && lines.length ? "transcript panel" : "caption scrape" });

await task.finish({ keep: [] });
console.log({ out });
