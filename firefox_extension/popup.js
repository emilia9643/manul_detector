const countEl = document.getElementById("count");
const folderInput = document.getElementById("folderInput");
const pathPreview = document.getElementById("pathPreview");
const downloadBtn = document.getElementById("downloadBtn");
const clearBtn = document.getElementById("clearBtn");
const statusEl = document.getElementById("status");

function getDefaultFolder() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `manul_twitter_${yyyy}${mm}${dd}`;
}

function sanitizeFolder(val) {
  let folder = (val || "").trim();
  folder = folder.replace(/^[\\/]+|[\\/]+$/g, "");
  folder = folder.replace(/[<>:"|?*]/g, "_");
  return folder || getDefaultFolder();
}

function updatePreview() {
  const clean = sanitizeFolder(folderInput.value);
  pathPreview.textContent = `Zapis w: ~/Pobrane/${clean}/`;
}

folderInput.addEventListener("input", updatePreview);

async function refreshCount() {
  try {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0 && tabs[0].id) {
      try {
        await browser.tabs.sendMessage(tabs[0].id, { action: "SCAN_NOW" });
      } catch (e) {}
    }

    const response = await browser.runtime.sendMessage({ action: "GET_STATUS" });
    if (response) {
      countEl.textContent = response.count || 0;
      if (response.count === 0) {
        downloadBtn.disabled = true;
      } else {
        downloadBtn.disabled = Boolean(response.isDownloading);
      }

      if (response.isDownloading) {
        statusEl.className = "status";
        statusEl.textContent = "Trwa pobieranie zdjęć...";
      }
    }
  } catch (err) {
    console.error("Błąd odświeżania:", err);
  }
}

async function init() {
  try {
    const data = await browser.storage.local.get("lastFolder");
    if (data && data.lastFolder) {
      folderInput.value = data.lastFolder;
    } else {
      folderInput.value = getDefaultFolder();
    }
  } catch (e) {
    folderInput.value = getDefaultFolder();
  }
  updatePreview();
  await refreshCount();
}

downloadBtn.addEventListener("click", async () => {
  const chosenFolder = sanitizeFolder(folderInput.value);
  folderInput.value = chosenFolder;
  updatePreview();

  await browser.storage.local.set({ lastFolder: chosenFolder });

  downloadBtn.disabled = true;
  clearBtn.disabled = true;
  folderInput.disabled = true;
  statusEl.className = "status";
  statusEl.textContent = "Rozpoczynanie pobierania...";

  try {
    await browser.runtime.sendMessage({
      action: "START_DOWNLOAD",
      folder: chosenFolder
    });
  } catch (err) {
    statusEl.className = "status error";
    statusEl.textContent = "Błąd komunikacji z wtyczką.";
    downloadBtn.disabled = false;
    clearBtn.disabled = false;
    folderInput.disabled = false;
  }
});

clearBtn.addEventListener("click", async () => {
  await browser.runtime.sendMessage({ action: "CLEAR_QUEUE" });
  countEl.textContent = "0";
  downloadBtn.disabled = true;
  statusEl.className = "status";
  statusEl.textContent = "Wyczyszczono listę.";
  setTimeout(() => {
    if (statusEl.textContent === "Wyczyszczono listę.") statusEl.textContent = "";
  }, 2000);
});

browser.runtime.onMessage.addListener((msg) => {
  if (msg.type === "DOWNLOAD_PROGRESS") {
    statusEl.className = "status";
    statusEl.textContent = `Pobieranie: ${msg.current}/${msg.total}...`;
  } else if (msg.type === "DOWNLOAD_COMPLETE") {
    statusEl.className = "status success";
    statusEl.textContent = `✓ Zapisano ${msg.total} zdjęć do folderu!`;
    countEl.textContent = "0";
    downloadBtn.disabled = true;
    clearBtn.disabled = false;
    folderInput.disabled = false;
  } else if (msg.type === "MEDIA_FOUND") {
    setTimeout(refreshCount, 100);
  }
});

init();
