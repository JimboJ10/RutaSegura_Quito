export const sizes = [
  { width: 360, height: 800 }, { width: 390, height: 844 }, { width: 430, height: 932 },
  { width: 768, height: 1024 }, { width: 1024, height: 768 },
  { width: 1280, height: 800 }, { width: 1920, height: 1080 },
];
export async function expandPanel(page) {
  const toggle = page.locator('.panel-toggle');
  if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'false') await toggle.click();
}
export async function collapsePanel(page) {
  const toggle = page.locator('.panel-toggle');
  if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'true') await toggle.click();
}
export async function measure(page) {
  return page.evaluate(() => {
    const rect = element => {
      if (!element) return null;
      const r = element.getBoundingClientRect();
      return { x: r.x, y: r.y, width: r.width, height: r.height, bottom: r.bottom, right: r.right };
    };
    // Chromium puede dar rectángulos a hijos de <details> cerrado: no están pintados.
    const visible = element => element?.checkVisibility({ visibilityProperty: true }) ?? false;
    const clippedRect = element => {
      const r = rect(element);
      let parent = element.parentElement;
      while (parent) {
        const css = getComputedStyle(parent), p = parent.getBoundingClientRect();
        if (/(auto|scroll|hidden|clip)/.test(css.overflowY)) { r.y = Math.max(r.y, p.top); r.bottom = Math.min(r.bottom, p.bottom); }
        if (/(auto|scroll|hidden|clip)/.test(css.overflowX)) { r.x = Math.max(r.x, p.left); r.right = Math.min(r.right, p.right); }
        parent = parent.parentElement;
      }
      r.width = Math.max(0, r.right - r.x); r.height = Math.max(0, r.bottom - r.y);
      return r;
    };
    const controls = [...document.querySelectorAll('button, select, summary, .leaflet-control-zoom a, .switch-label')].filter(visible)
      .map(el => {
        const clipped = clippedRect(el);
        const top = document.elementFromPoint(clipped.x + clipped.width / 2, clipped.y + clipped.height / 2);
        return { name: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 75), rect: rect(el), clipped,
          hit: !!top && (el === top || el.contains(top)), disabled: !!el.disabled };
      }).filter(el => el.clipped.width > 1 && el.clipped.height > 1 && el.clipped.y >= 0 && el.clipped.bottom <= innerHeight);
    const overlaps = [];
    for (let i = 0; i < controls.length; i++) for (let j = i + 1; j < controls.length; j++) {
      const a = controls[i], b = controls[j];
      const x = Math.min(a.clipped.right, b.clipped.right) - Math.max(a.clipped.x, b.clipped.x);
      const y = Math.min(a.clipped.bottom, b.clipped.bottom) - Math.max(a.clipped.y, b.clipped.y);
      if (x > 1 && y > 1) overlaps.push([a.name, b.name, Math.round(x * y)]);
    }
    const attribution = document.querySelector('.leaflet-control-attribution');
    const ar = attribution?.getBoundingClientRect();
    const hit = ar && document.elementFromPoint(ar.x + ar.width / 2, ar.y + ar.height / 2);
    const panel = document.querySelector('.panel-content');
    return {
      viewport: { width: innerWidth, height: innerHeight }, documentWidth: document.documentElement.scrollWidth,
      horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
      panelHorizontalOverflow: !!panel && panel.scrollWidth > panel.clientWidth,
      map: rect(document.querySelector('.map-canvas')), panel: rect(document.querySelector('.journey-panel')),
      predictionLegendVisible: !!visible(document.querySelector('.prediction-legend')),
      attribution: { rect: rect(attribution), visible: !!visible(attribution), unobstructed: !!hit && (hit === attribution || attribution.contains(hit)) },
      smallControls: controls.filter(c => !c.disabled && (c.rect.width < 43.5 || c.rect.height < 43.5)),
      // Un borde parcial bajo el scroll no es una obstrucción; los botones se
      // desplazan hasta quedar visibles antes de probar su interacción real.
      blockedControls: controls.filter(c => !c.disabled && !c.hit && c.clipped.width >= c.rect.width - 0.5 && c.clipped.height >= c.rect.height - 0.5),
      overlaps,
      loadedTiles: [...document.querySelectorAll('img.leaflet-tile')].filter(img => img.complete && img.naturalWidth > 0).length,
      selectedRoutes: [...document.querySelectorAll('.route-card[aria-pressed="true"]')].map(el => el.textContent.trim()),
      routeStrokes: [...document.querySelectorAll('.route-line, .leaflet-overlay-pane path[fill="none"]')].map(el => ({ color: el.getAttribute('stroke'), width: el.getAttribute('stroke-width'), opacity: el.getAttribute('stroke-opacity') })),
    };
  });
}
