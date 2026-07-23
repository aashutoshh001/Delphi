// ---------------------------------------------------------
// Delphi — Inshorts-style brief cards
//
// Stories are the live hypothesis feed, fetched from the local Hypothesis
// Agent API (see hypothesis_agent/src/hypothesis_agent/server). If that API
// isn't reachable (e.g. the page was opened straight from disk, or the
// server isn't running), a small embedded fallback deck is shown instead so
// the page still works standalone — matching how this site behaved before
// it was wired to a live backend.
// ---------------------------------------------------------

const API_BASE = "http://127.0.0.1:8200";
const INSIGHT_API = "http://127.0.0.1:8300";
const DUMMY_IMAGE = "assets/shl-logo.png";
const DUMMY_URL = "https://www.shl.com/careers/";

const FALLBACK_STORIES = [
  { title: "OpenAI and Hugging Face address security incident during model evaluation", description: "OpenAI and Hugging Face jointly disclosed and remediated a security incident discovered during a routine model evaluation process." },
  { title: "Kimi K3 Is Competitive with Fable; Kimi K3 and Fable Is SoTA", description: "New benchmark results show Kimi K3 matching Fable's performance, with both models setting state-of-the-art scores." },
  { title: "Introduction to Formal Verification with Lean Part 1", description: "The first part of a series introducing formal verification concepts using the Lean theorem prover." },
  { title: "Intel Starts Shipping High-NA EUV Silicon", description: "Intel has begun shipping its first chips manufactured using High-NA EUV lithography technology." },
  { title: "Original Apollo 11 Guidance Computer source code for command and lunar modules", description: "The original assembly source code for the Apollo 11 command and lunar module guidance computers, preserved on GitHub." },
].map((s, i) => ({
  ...s,
  id: `fallback-${i}`,
  imageURL: DUMMY_IMAGE,
  readmoreURL: DUMMY_URL,
  reaction: "none",
}));

let STORIES = [];
let usingFallback = false;

function normalizeStory(entry, index) {
  return {
    id: entry.id || `idx-${index}`,
    title: entry.title || "(untitled)",
    description: entry.description || "",
    imageURL: entry.imageURL || DUMMY_IMAGE,
    readmoreURL: entry.readmoreURL || DUMMY_URL,
    reaction: entry.reaction === "up" || entry.reaction === "down" ? entry.reaction : "none",
    // Set once the Investigation Pipeline (:8300) has produced a full report
    // for this hypothesis — see requestInvestigation() below. Null until then.
    insightId: entry.insightId || null,
  };
}

// "Read more" target for a story: the full insight report if one's been
// generated, otherwise the hypothesis-only detail page rendered at
// generation time.
function readMoreHref(story) {
  return story.insightId
    ? `insight.html?id=${encodeURIComponent(story.insightId)}`
    : story.readmoreURL;
}

// Loads the live feed. Returns true if it succeeded (so callers know
// whether STORIES reflects real data or the offline fallback deck).
async function fetchStories() {
  const res = await fetch(`${API_BASE}/api/stories`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API returned ${res.status}`);
  const data = await res.json();
  STORIES = data.map(normalizeStory);
  usingFallback = false;
  return true;
}

async function loadInitialStories() {
  try {
    await fetchStories();
  } catch (e) {
    STORIES = FALLBACK_STORIES;
    usingFallback = true;
  }
}

// Called on the periodic poll — never falls back to dummy content on a
// transient failure, just keeps whatever was last successfully loaded.
async function pollStories() {
  if (usingFallback) return; // don't fight a deliberate offline fallback
  try {
    await fetchStories();
  } catch (e) {
    /* API unreachable this cycle — keep showing the last known-good list */
  }
}

const THUMB_SVG = `<svg viewBox="0 0 24 24" fill="none">
  <path d="M8 21H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1h3m0 11V10m0 11h9.28a2 2 0 0 0 1.98-1.7l1.25-8A2 2 0 0 0 18.53 9H14V4.5A1.5 1.5 0 0 0 12.5 3c-.4 0-.78.2-1 .53L8 10"
    stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const FEEDBACK_KEY = "delphi-feedback-v1";

function loadLocalFeedbackCache() {
  try {
    return JSON.parse(localStorage.getItem(FEEDBACK_KEY)) || {};
  } catch (e) {
    return {};
  }
}

function saveLocalFeedbackCache() {
  try {
    localStorage.setItem(FEEDBACK_KEY, JSON.stringify(localFeedbackCache));
  } catch (e) {
    // storage unavailable (e.g. private mode) — local cache just won't persist
  }
}

// The server-stored `reaction` on each story is the source of truth; this
// local cache is an offline-friendly mirror so a reaction still shows after
// reload even if the API is briefly unreachable.
const localFeedbackCache = loadLocalFeedbackCache();

function currentReaction(story) {
  return localFeedbackCache[story.id] || story.reaction || "none";
}

// A story's reaction buttons can exist in two places at once (the Cards
// deck and the Headlines list), since both views are built up front. Look
// up the value fresh rather than trusting the button that was clicked, so
// every rendered copy stays in sync.
async function toggleFeedback(story, value) {
  const next = currentReaction(story) === value ? "none" : value;
  story.reaction = next;
  localFeedbackCache[story.id] = next;
  saveLocalFeedbackCache();

  document.querySelectorAll(`[data-reactions-for="${story.id}"]`).forEach((group) => {
    const upBtn = group.querySelector(".up");
    const downBtn = group.querySelector(".down");
    upBtn.classList.toggle("active", next === "up");
    upBtn.setAttribute("aria-pressed", String(next === "up"));
    downBtn.classList.toggle("active", next === "down");
    downBtn.setAttribute("aria-pressed", String(next === "down"));
  });

  if (usingFallback) return; // nothing to persist server-side
  try {
    await fetch(`${API_BASE}/api/stories/${encodeURIComponent(story.id)}/reaction`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reaction: next }),
    });
  } catch (e) {
    // offline — localFeedbackCache already has it; next successful poll
    // will still show it since we don't overwrite reaction on a poll failure
  }
}

function buildReactionGroup(story) {
  const reaction = currentReaction(story);
  const reactions = document.createElement("div");
  reactions.className = "reaction-group";
  reactions.dataset.reactionsFor = story.id;

  const upBtn = document.createElement("button");
  upBtn.type = "button";
  upBtn.className = "reaction-btn up" + (reaction === "up" ? " active" : "");
  upBtn.setAttribute("aria-label", "Thumbs up");
  upBtn.setAttribute("aria-pressed", String(reaction === "up"));
  upBtn.innerHTML = THUMB_SVG;

  const downBtn = document.createElement("button");
  downBtn.type = "button";
  downBtn.className = "reaction-btn down thumb-down" + (reaction === "down" ? " active" : "");
  downBtn.setAttribute("aria-label", "Thumbs down");
  downBtn.setAttribute("aria-pressed", String(reaction === "down"));
  downBtn.innerHTML = THUMB_SVG;

  upBtn.addEventListener("click", () => toggleFeedback(story, "up"));
  downBtn.addEventListener("click", () => toggleFeedback(story, "down"));

  reactions.appendChild(upBtn);
  reactions.appendChild(downBtn);
  return reactions;
}

// ---------------------------------------------------------

const cardViewport = document.getElementById("cardViewport");
const progressTrack = document.getElementById("progressTrack");
const nextBtn = document.getElementById("nextBtn");
const headlineList = document.getElementById("headlineList");
const layoutToggle = document.getElementById("layoutToggle");
const deviceToggle = document.getElementById("deviceToggle");
const body = document.body;

let currentIndex = 0;
let isAnimating = false;
const ANIM_MS = 420;

function isLogoImage(url) {
  return url.includes("shl-logo.png");
}

function buildCard(index) {
  const story = STORIES[index];
  const card = document.createElement("div");
  card.className = "card";

  const media = document.createElement("div");
  media.className = "card-media" + (isLogoImage(story.imageURL) ? " logo-image" : "");

  const img = document.createElement("img");
  img.src = story.imageURL;
  img.alt = story.title;
  media.appendChild(img);

  const tag = document.createElement("span");
  tag.className = "card-tag";
  tag.textContent = "SHL Careers";
  media.appendChild(tag);

  const count = document.createElement("span");
  count.className = "card-count";
  count.textContent = `${index + 1} / ${STORIES.length}`;
  media.appendChild(count);

  const bodyEl = document.createElement("div");
  bodyEl.className = "card-body";

  const title = document.createElement("h2");
  title.className = "card-title";
  title.textContent = story.title;

  const desc = document.createElement("p");
  desc.className = "card-desc";
  desc.textContent = story.description;

  const footer = document.createElement("div");
  footer.className = "card-footer";

  const source = document.createElement("span");
  source.className = "source-tag";
  source.textContent = "shl.com";

  const link = document.createElement("a");
  link.className = "read-more";
  link.href = readMoreHref(story);
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.innerHTML = `Read more
    <svg viewBox="0 0 24 24" fill="none">
      <path d="M7 17L17 7M17 7H9M17 7V15" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;

  const actions = document.createElement("div");
  actions.className = "footer-actions";
  actions.appendChild(buildReactionGroup(story));
  actions.appendChild(link);

  footer.appendChild(source);
  footer.appendChild(actions);

  bodyEl.appendChild(title);
  bodyEl.appendChild(desc);
  bodyEl.appendChild(footer);

  card.appendChild(media);
  card.appendChild(bodyEl);

  return card;
}

function renderProgress() {
  progressTrack.innerHTML = "";
  STORIES.forEach((_, i) => {
    const seg = document.createElement("div");
    seg.className = "progress-seg" + (i <= currentIndex ? " filled" : "");
    const fill = document.createElement("div");
    fill.className = "fill";
    seg.appendChild(fill);
    progressTrack.appendChild(seg);
  });
}

function buildEmptyState() {
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.innerHTML = `<h3>No hypotheses yet</h3>
    <p>Click "+ Generate hypothesis" above to run the Hypothesis Agent and populate the feed.</p>`;
  return empty;
}

function initCards() {
  cardViewport.innerHTML = "";
  if (STORIES.length === 0) {
    cardViewport.appendChild(buildEmptyState());
    renderProgress();
    return;
  }
  if (currentIndex >= STORIES.length) currentIndex = 0;
  const card = buildCard(currentIndex);
  cardViewport.appendChild(card);
  renderProgress();
}

function buildHeadlineItem(index) {
  const story = STORIES[index];

  const item = document.createElement("div");
  item.className = "headline-item";

  const rank = document.createElement("span");
  rank.className = "headline-rank";
  rank.textContent = `${index + 1}.`;

  const main = document.createElement("div");
  main.className = "headline-main";

  const titleRow = document.createElement("div");
  titleRow.className = "headline-title-row";

  const title = document.createElement("a");
  title.className = "headline-title";
  title.href = readMoreHref(story);
  title.target = "_blank";
  title.rel = "noopener noreferrer";
  title.textContent = story.title;

  const domain = document.createElement("span");
  domain.className = "headline-domain";
  domain.textContent = "(shl.com)";

  titleRow.appendChild(title);
  titleRow.appendChild(domain);

  const desc = document.createElement("p");
  desc.className = "headline-desc";
  desc.textContent = story.description;

  const meta = document.createElement("div");
  meta.className = "headline-meta";
  meta.appendChild(buildReactionGroup(story));

  main.appendChild(titleRow);
  main.appendChild(desc);
  main.appendChild(meta);

  item.appendChild(rank);
  item.appendChild(main);

  return item;
}

function renderHeadlines() {
  headlineList.innerHTML = "";
  if (STORIES.length === 0) {
    headlineList.appendChild(buildEmptyState());
    return;
  }
  STORIES.forEach((_, index) => {
    headlineList.appendChild(buildHeadlineItem(index));
  });
}

function goTo(nextIndex, direction) {
  // direction: "next" -> new card enters from bottom, old exits top
  //            "prev" -> new card enters from top, old exits bottom
  if (isAnimating || STORIES.length === 0) return;
  isAnimating = true;

  const outgoing = cardViewport.querySelector(".card");
  const incoming = buildCard(nextIndex);

  incoming.classList.add(direction === "next" ? "entering-from-bottom" : "entering-from-top");
  cardViewport.appendChild(incoming);

  // force reflow so the entering class transition applies
  void incoming.offsetWidth;

  outgoing.classList.add(direction === "next" ? "leaving-to-top" : "leaving-to-bottom");
  incoming.classList.remove("entering-from-bottom", "entering-from-top");

  currentIndex = nextIndex;
  renderProgress();

  setTimeout(() => {
    outgoing.remove();
    isAnimating = false;
  }, ANIM_MS);
}

function next() {
  const nextIndex = (currentIndex + 1) % STORIES.length;
  goTo(nextIndex, "next");
}

function prev() {
  const prevIndex = (currentIndex - 1 + STORIES.length) % STORIES.length;
  goTo(prevIndex, "prev");
}

// ---------------- Controls ----------------

nextBtn.addEventListener("click", next);

document.addEventListener("keydown", (e) => {
  if (["ArrowDown", "PageDown", " "].includes(e.key)) {
    e.preventDefault();
    next();
  } else if (["ArrowUp", "PageUp"].includes(e.key)) {
    e.preventDefault();
    prev();
  }
});

let wheelCooldown = false;
cardViewport.addEventListener(
  "wheel",
  (e) => {
    if (wheelCooldown) return;
    if (Math.abs(e.deltaY) < 12) return;
    wheelCooldown = true;
    if (e.deltaY > 0) next();
    else prev();
    setTimeout(() => (wheelCooldown = false), ANIM_MS + 80);
  },
  { passive: true }
);

let touchStartY = null;
cardViewport.addEventListener(
  "touchstart",
  (e) => {
    touchStartY = e.touches[0].clientY;
  },
  { passive: true }
);

cardViewport.addEventListener(
  "touchend",
  (e) => {
    if (touchStartY === null) return;
    const deltaY = touchStartY - e.changedTouches[0].clientY;
    if (Math.abs(deltaY) > 60) {
      if (deltaY > 0) next();
      else prev();
    }
    touchStartY = null;
  },
  { passive: true }
);

// ---------------- Toggle pills (Cards/Headlines, Web/Mobile) ----------------

function setupPillToggle(toggle, onChange) {
  toggle.addEventListener("click", (e) => {
    const btn = e.target.closest(".toggle-option");
    if (!btn) return;
    const value = btn.dataset.value;
    if (toggle.dataset.active === value) return;

    toggle.dataset.active = value;
    toggle.querySelectorAll(".toggle-option").forEach((opt) => {
      opt.setAttribute("aria-pressed", opt.dataset.value === value ? "true" : "false");
    });

    onChange(value);
  });
}

setupPillToggle(layoutToggle, (layout) => {
  body.classList.toggle("layout-cards", layout === "cards");
  body.classList.toggle("layout-headlines", layout === "headlines");
});

setupPillToggle(deviceToggle, (mode) => {
  body.classList.toggle("mode-web", mode === "web");
  body.classList.toggle("mode-mobile", mode === "mobile");
});

// ---------------- Generate button ----------------

const generateBtn = document.getElementById("generateBtn");

generateBtn.addEventListener("click", async () => {
  generateBtn.disabled = true;
  const originalLabel = generateBtn.textContent;
  generateBtn.textContent = "Generating…";
  let res;
  try {
    res = await fetch(`${API_BASE}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}), // server defaults organization_id to whatever it seeded
    });
  } catch (e) {
    generateBtn.textContent = "API unreachable — is the server running?";
    setTimeout(() => (generateBtn.textContent = originalLabel), 4000);
    generateBtn.disabled = false;
    return;
  }
  if (!res.ok) {
    let detail = null;
    try {
      detail = (await res.json()).detail;
    } catch (_) {
      // body wasn't JSON — fall back to the generic message below
    }
    generateBtn.textContent = detail || `Request failed (${res.status})`;
    setTimeout(() => (generateBtn.textContent = originalLabel), 4000);
    generateBtn.disabled = false;
    return;
  }
  let story;
  try {
    const rawRes = await fetch(`${API_BASE}/api/stories`, { cache: "no-store" });
    const rawStories = await rawRes.json();
    story = rawStories[rawStories.length - 1]; // just-generated entry
    await fetchStories(); // refresh the normalized deck used by the card/headline views
    currentIndex = STORIES.length - 1;
    initCards();
    renderHeadlines();
  } catch (e) {
    generateBtn.textContent = "Generated, but failed to refresh — reload the page";
    setTimeout(() => (generateBtn.textContent = originalLabel), 4000);
    generateBtn.disabled = false;
    return;
  }

  // Best-effort: also run the new hypothesis through the Investigation
  // Pipeline (:8300) so "Read more" opens the full analytics/root-cause/
  // narrative/chart report instead of just the mechanism+critique page.
  // Several real LLM calls plus real analytics/plotting, so this can take
  // a few minutes. If the pipeline API isn't running, or the run fails
  // (e.g. every requested column is missing from the dataset), the
  // hypothesis itself is still generated fine — only this enrichment step
  // is skipped, and "Read more" falls back to the hypothesis-only page.
  if (story) {
    generateBtn.textContent = "Investigating… (a few minutes)";
    try {
      await requestInvestigation(story);
      await fetchStories(); // pick up the insightId just recorded
      initCards();
      renderHeadlines();
    } catch (e) {
      console.warn("Investigation Pipeline enrichment skipped:", e);
    }
  }

  generateBtn.textContent = originalLabel;
  generateBtn.disabled = false;
});

// Builds a HypothesisPackage-shaped payload from a raw stories.json entry
// (mirrors insight_pipeline/examples/run_investigation_from_server.py),
// POSTs it to the Investigation Pipeline API, then records the resulting
// InsightPackage id back on the story via the Hypothesis Agent API so
// future page loads know to link "Read more" straight to the full report.
async function requestInvestigation(story) {
  const hypothesisPackage = {
    package_id: story.id, // ties the InsightPackage back to this exact story
    organization_id: story.organization_id,
    hypothesis_statement: story.statement,
    mechanism_explanation: story.mechanism,
    business_lens: story.lens,
    target_constructs: story.target_constructs || [],
    scorecard: story.scorecard,
    critique: story.critique,
    search_stats: story.search_stats,
    headline: story.title || "",
    summary: story.description || "",
  };
  const res = await fetch(`${INSIGHT_API}/api/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hypothesis_package: hypothesisPackage }),
  });
  if (!res.ok) throw new Error(`Investigation Pipeline API returned ${res.status}`);
  const result = await res.json();
  await fetch(`${API_BASE}/api/stories/${encodeURIComponent(story.id)}/insight`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ insight_package_id: result.insight_package_id }),
  });
}

// ---------------- Init ----------------

async function init() {
  await loadInitialStories();
  initCards();
  renderHeadlines();
  setInterval(async () => {
    await pollStories();
    renderHeadlines();
    if (cardViewport.querySelector(".empty-state") && STORIES.length > 0) initCards();
  }, 15000);
}

init();
