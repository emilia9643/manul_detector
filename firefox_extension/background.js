const collectedImages = new Map();
let isDownloading = false;

browser.browserAction.setBadgeBackgroundColor({ color: "#e68c1e" });

function parseTwitterMedia(urlStr) {
  try {
    const url = new URL(urlStr);
    if (url.hostname !== "pbs.twimg.com") return null;
    if (!url.pathname.startsWith("/media/")) return null;

    let filename = url.pathname.replace(/^\/media\//, "");
    if (!filename) return null;

    let mediaId = filename;
    let format = "jpg";

    if (filename.includes(".")) {
      const parts = filename.split(".");
      mediaId = parts[0];
      format = parts[1].split(":")[0];
    }

    if (url.searchParams.has("format")) {
      format = url.searchParams.get("format");
    }

    const highResUrl = `https://pbs.twimg.com/media/${mediaId}?format=${format}&name=orig`;

    return { mediaId, format, highResUrl };
  } catch (e) {
    return null;
  }
}

function addImage(urlStr) {
  const parsed = parseTwitterMedia(urlStr);
  if (parsed && !collectedImages.has(parsed.mediaId)) {
    collectedImages.set(parsed.mediaId, parsed);
    updateBadge();
  }
}

function updateBadge() {
  const count = collectedImages.size;
  browser.browserAction.setBadgeText({
    text: count > 0 ? String(count) : ""
  });
  browser.browserAction.setBadgeBackgroundColor({ color: "#e68c1e" });
}

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message) return;

  if (message.type === "MEDIA_FOUND" && message.url) {
    addImage(message.url);
    return;
  }

  if (message.action === "GET_STATUS") {
    sendResponse({
      count: collectedImages.size,
      isDownloading: isDownloading
    });
    return;
  }

  if (message.action === "CLEAR_QUEUE") {
    collectedImages.clear();
    updateBadge();
    sendResponse({ success: true });
    return;
  }

  if (message.action === "START_DOWNLOAD") {
    handleBatchDownload(message.folder);
    sendResponse({ started: true });
    return;
  }
});

browser.webRequest.onBeforeRequest.addListener(
  (details) => {
    addImage(details.url);
  },
  { urls: ["*://pbs.twimg.com/media/*"] }
);

function injectIntoOpenTabs() {
  browser.tabs.query({ url: ["*://*.twitter.com/*", "*://*.x.com/*"] }).then((tabs) => {
    for (const tab of tabs) {
      browser.tabs.executeScript(tab.id, { file: "content.js" }).catch(() => {});
    }
  }).catch(() => {});
}

injectIntoOpenTabs();

async function handleBatchDownload(targetFolder) {
  if (isDownloading) return;
  const count = collectedImages.size;
  if (count === 0) return;

  isDownloading = true;

  let folder = (targetFolder || "").trim().replace(/^[\\/]+|[\\/]+$/g, "");
  if (!folder) {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, "0");
    const dd = String(now.getDate()).padStart(2, "0");
    folder = `manul_twitter_${yyyy}${mm}${dd}`;
  }

  const items = Array.from(collectedImages.values());
  collectedImages.clear();

  const total = items.length;
  const padLength = Math.max(3, String(total).length);

  browser.browserAction.setBadgeBackgroundColor({ color: "#2563eb" });

  for (let i = 0; i < total; i++) {
    const item = items[i];
    const indexStr = String(i + 1).padStart(padLength, "0");
    const filename = `${folder}/img_${indexStr}.${item.format}`;

    browser.browserAction.setBadgeText({ text: `${i + 1}` });
    browser.runtime.sendMessage({
      type: "DOWNLOAD_PROGRESS",
      current: i + 1,
      total: total
    }).catch(() => {});

    try {
      await browser.downloads.download({
        url: item.highResUrl,
        filename: filename,
        saveAs: false,
        conflictAction: "uniquify"
      });
    } catch (err) {
      console.error(`Błąd pobierania zdjęcia ${item.highResUrl}:`, err);
    }

    await new Promise((resolve) => setTimeout(resolve, 60));
  }

  browser.browserAction.setBadgeBackgroundColor({ color: "#16a34a" });
  browser.browserAction.setBadgeText({ text: "✓" });

  browser.runtime.sendMessage({
    type: "DOWNLOAD_COMPLETE",
    total: total,
    folder: folder
  }).catch(() => {});

  setTimeout(() => {
    browser.browserAction.setBadgeText({ text: "" });
    updateBadge();
    isDownloading = false;
  }, 3500);
}
