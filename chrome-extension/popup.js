const STORAGE_KEY = "savedItems";

function parseTabUrl(url) {
  try {
    const parsed = new URL(url);
    if (!parsed.hostname.includes("music.youtube.com")) return null;

    const listId = parsed.searchParams.get("list");
    const videoId = parsed.searchParams.get("v");

    if (listId && !videoId) {
      return { type: "list", listId };
    }
    if (videoId) {
      return { type: "watch", videoId, listId: listId || undefined };
    }
    // music.youtube.com/watch/VIDEO_ID path style
    const match = parsed.pathname.match(/watch\\/([\\w-]{11})/);
    if (match) {
      return { type: "watch", videoId: match[1], listId: listId || undefined };
    }
  } catch (err) {
    console.error(err);
  }
  return null;
}

async function loadItems() {
  const result = await chrome.storage.local.get(STORAGE_KEY);
  return result[STORAGE_KEY] || [];
}

async function saveItems(items) {
  await chrome.storage.local.set({ [STORAGE_KEY]: items });
}

function renderItems(items) {
  const list = document.getElementById("items-list");
  list.innerHTML = "";
  items.forEach((item, idx) => {
    const li = document.createElement("li");
    const badge = document.createElement("span");
    badge.className = "item-badge";
    badge.textContent = item.type === "list" ? "list" : "watch";
    const label = document.createElement("span");
    label.textContent =
      item.type === "list"
        ? `listId=${item.listId}`
        : `videoId=${item.videoId}${item.listId ? ` (listId=${item.listId})` : ""}`;

    const left = document.createElement("div");
    left.style.display = "flex";
    left.style.alignItems = "center";
    left.appendChild(badge);
    left.appendChild(label);

    const controls = document.createElement("div");
    controls.className = "item-controls";

    const up = document.createElement("button");
    up.textContent = "▲";
    up.title = "Up";
    up.onclick = async () => {
      if (idx === 0) return;
      const newItems = [...items];
      [newItems[idx - 1], newItems[idx]] = [newItems[idx], newItems[idx - 1]];
      await saveItems(newItems);
      renderItems(newItems);
    };

    const down = document.createElement("button");
    down.textContent = "▼";
    down.title = "Down";
    down.onclick = async () => {
      if (idx === items.length - 1) return;
      const newItems = [...items];
      [newItems[idx + 1], newItems[idx]] = [newItems[idx], newItems[idx + 1]];
      await saveItems(newItems);
      renderItems(newItems);
    };

    const remove = document.createElement("button");
    remove.textContent = "삭제";
    remove.onclick = async () => {
      const newItems = items.filter((_, i) => i !== idx);
      await saveItems(newItems);
      renderItems(newItems);
    };

    controls.appendChild(up);
    controls.appendChild(down);
    controls.appendChild(remove);

    li.appendChild(left);
    li.appendChild(controls);
    list.appendChild(li);
  });
}

async function init() {
  const statusEl = document.getElementById("status");
  const addBtn = document.getElementById("add-btn");
  const copyBtn = document.getElementById("copy-btn");
  const clearBtn = document.getElementById("clear-btn");
  const currentInfo = document.getElementById("current-info");

  let currentItem = null;
  const items = await loadItems();
  renderItems(items);

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    currentItem = parseTabUrl(tab.url);
    if (currentItem) {
      const text =
        currentItem.type === "list"
          ? `감지됨: playlist listId=${currentItem.listId}`
          : `감지됨: watch videoId=${currentItem.videoId}${
              currentItem.listId ? ` / listId=${currentItem.listId}` : ""
            }`;
      currentInfo.textContent = text;
      addBtn.disabled = false;
    } else {
      currentInfo.textContent = "music.youtube.com 탭이 아니거나 listId/videoId를 찾을 수 없습니다.";
    }
  });

  addBtn.onclick = async () => {
    if (!currentItem) return;
    const updated = [...(await loadItems()), currentItem];
    await saveItems(updated);
    renderItems(updated);
    statusEl.textContent = "현재 탭이 목록에 추가되었습니다.";
  };

  clearBtn.onclick = async () => {
    await saveItems([]);
    renderItems([]);
    statusEl.textContent = "모든 항목을 삭제했습니다.";
  };

  copyBtn.onclick = async () => {
    const saved = await loadItems();
    const payload = {
      version: 2,
      items: saved,
      createdAt: new Date().toISOString(),
      source: "ytmusic-extension",
    };
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    statusEl.textContent = "JSON이 클립보드에 복사되었습니다.";
  };
}

document.addEventListener("DOMContentLoaded", init);
