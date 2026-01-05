document.addEventListener('DOMContentLoaded', () => {
  const importBtn = document.getElementById('import-btn');
  const copyBtn = document.getElementById('copy-btn');
  const clearBtn = document.getElementById('clear-btn');
  const statusDiv = document.getElementById('status');
  const queueListDiv = document.getElementById('queue-list');

  let currentQueue = [];

  // Load saved queue
  chrome.storage.local.get(['ytmusic_queue'], (result) => {
    if (result.ytmusic_queue) {
      currentQueue = result.ytmusic_queue;
      renderQueue();
    }
  });

  importBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url.includes('music.youtube.com')) {
      statusDiv.textContent = 'Error: Not on YouTube Music!';
      return;
    }

    statusDiv.textContent = 'Scraping queue...';
    
    try {
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'scrapeQueue' });
      
      if (response && response.items) {
        // Merge logic: avoid duplicates by video_id
        let addedCount = 0;
        const existingIds = new Set(currentQueue.map(i => i.video_id));
        
        response.items.forEach(item => {
          if (!existingIds.has(item.video_id)) {
            currentQueue.push(item);
            existingIds.add(item.video_id);
            addedCount++;
          }
        });

        chrome.storage.local.set({ ytmusic_queue: currentQueue });
        renderQueue();
        statusDiv.textContent = `Added ${addedCount} tracks. Total: ${currentQueue.length}`;
      } else {
        statusDiv.textContent = 'Failed to scrape queue.';
      }
    } catch (err) {
      console.error(err);
      statusDiv.textContent = 'Error: Could not communicate with page.';
    }
  });

  copyBtn.addEventListener('click', () => {
    if (currentQueue.length === 0) {
      statusDiv.textContent = 'Queue is empty!';
      return;
    }

    const payload = {
      schema_version: 1,
      source: 'ytmusic',
      type: 'queue',
      name: 'Now Playing Queue',
      exported_at: new Date().toISOString(),
      items: currentQueue
    };

    navigator.clipboard.writeText(JSON.stringify(payload, null, 2)).then(() => {
      statusDiv.textContent = 'JSON copied to clipboard!';
      setTimeout(() => statusDiv.textContent = 'Ready.', 2000);
    });
  });

  clearBtn.addEventListener('click', () => {
    currentQueue = [];
    chrome.storage.local.set({ ytmusic_queue: [] });
    renderQueue();
    statusDiv.textContent = 'List cleared.';
  });

  function renderQueue() {
    queueListDiv.innerHTML = '';
    if (currentQueue.length === 0) {
      queueListDiv.innerHTML = '<div style="text-align: center; color: #666; padding: 10px;">List is empty</div>';
      return;
    }

    currentQueue.forEach((item, index) => {
      const div = document.createElement('div');
      div.className = 'queue-item';
      
      const info = document.createElement('span');
      info.textContent = `${index + 1}. ${item.title} - ${item.artist}`;
      info.title = item.title;
      
      const removeBtn = document.createElement('span');
      removeBtn.className = 'remove-btn';
      removeBtn.textContent = '×';
      removeBtn.onclick = () => {
        currentQueue.splice(index, 1);
        chrome.storage.local.set({ ytmusic_queue: currentQueue });
        renderQueue();
      };

      div.appendChild(info);
      div.appendChild(removeBtn);
      queueListDiv.appendChild(div);
    });
  }
});
