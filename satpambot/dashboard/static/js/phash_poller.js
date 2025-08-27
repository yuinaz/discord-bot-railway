(function () {
  if (window.__phashPoller) return; // prevent duplicate loads

  const POLL_MS_DEFAULT = 5000;
  let interval = null;
  let abortCtl = null;
  let last = null;

  async function fetchOnce(signal) {
    const res = await fetch('/api/phish/phash', { signal, cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  }

  async function tick() {
    try {
      if (abortCtl) abortCtl.abort();
      abortCtl = new AbortController();
      const data = await fetchOnce(abortCtl.signal);
      if (!data) return;
      last = data;
      window.dispatchEvent(new CustomEvent('phash:update', { detail: data }));
    } catch (e) {
      // swallow
    }
  }

  function start() {
    stop();
    try { tick(); } catch(e) {}
    const ms = (window.__uiConfig && window.__uiConfig.poll_interval_ms) || POLL_MS_DEFAULT;
    interval = setInterval(tick, ms);
  }

  function stop() {
    if (interval) clearInterval(interval);
    interval = null;
    if (abortCtl) abortCtl.abort();
  }

  function requestNow() {
    try { tick(); } catch(e) {}
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') stop();
    else start();
  });
  window.addEventListener('beforeunload', stop);

  start();
  window.__phashPoller = { start, stop, requestNow, getLast: () => last };
})();