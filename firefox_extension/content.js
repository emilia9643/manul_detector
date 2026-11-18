if (!window.__manulExtractorLoaded) {
  window.__manulExtractorLoaded = true;

  const sentUrls = new Set();

  function sendImageIfMedia(url) {
    if (!url || typeof url !== "string") return;
    if (!url.includes("pbs.twimg.com/media/")) return;
    if (sentUrls.has(url)) return;

    sentUrls.add(url);

    try {
      browser.runtime.sendMessage({
        type: "MEDIA_FOUND",
        url: url
      }).catch(() => {});
    } catch (e) {}
  }

  function scanPerformanceResources() {
    try {
      const resources = performance.getEntriesByType("resource");
      for (let i = 0; i < resources.length; i++) {
        sendImageIfMedia(resources[i].name);
      }
    } catch (e) {}
  }

  function scanDOM() {
    try {
      const imgs = document.querySelectorAll('img[src*="pbs.twimg.com/media/"]');
      for (let i = 0; i < imgs.length; i++) {
        sendImageIfMedia(imgs[i].src);
      }

      const divs = document.querySelectorAll('div[style*="pbs.twimg.com/media/"]');
      for (let i = 0; i < divs.length; i++) {
        const bg = divs[i].style.backgroundImage;
        if (bg) {
          const match = bg.match(/url\(["']?(https:\/\/pbs\.twimg\.com\/media\/[^"']+)["']?\)/);
          if (match && match[1]) {
            sendImageIfMedia(match[1]);
          }
        }
      }
    } catch (e) {}
  }

  scanPerformanceResources();
  scanDOM();

  try {
    const perfObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      for (let i = 0; i < entries.length; i++) {
        sendImageIfMedia(entries[i].name);
      }
    });
    perfObserver.observe({ entryTypes: ["resource"] });
  } catch (e) {}

  let mutationTimeout = null;
  const domObserver = new MutationObserver(() => {
    if (mutationTimeout) return;
    mutationTimeout = setTimeout(() => {
      scanDOM();
      scanPerformanceResources();
      mutationTimeout = null;
    }, 200);
  });

  if (document.body) {
    domObserver.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      domObserver.observe(document.body, { childList: true, subtree: true });
    });
  }

  browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request && request.action === "SCAN_NOW") {
      scanPerformanceResources();
      scanDOM();
      sendResponse({ count: sentUrls.size, urls: Array.from(sentUrls) });
    }
  });
}
