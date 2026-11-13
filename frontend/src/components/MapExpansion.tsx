import { useEffect, useRef, useState } from 'react';

export function useMapExpansion() {
  const [expanded, setExpanded] = useState(false);
  const region = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!expanded || !region.current) return;
    const hidden: HTMLElement[] = [];
    for (let el: HTMLElement | null = region.current; el && el !== document.body; el = el.parentElement) {
      for (const sibling of el.parentElement?.children ?? []) {
        if (sibling !== el && sibling instanceof HTMLElement && !sibling.inert) {
          sibling.inert = true;
          hidden.push(sibling);
        }
      }
    }
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') setExpanded(false); };
    document.addEventListener('keydown', escape);
    trigger.current?.focus({preventScroll:true});
    return () => {
      hidden.forEach(el => { el.inert = false; });
      document.removeEventListener('keydown', escape);
      trigger.current?.focus({preventScroll:true});
    };
  }, [expanded]);
  return {expanded, region, trigger, setExpanded};
}

export function ExpandButton({view}: {view: ReturnType<typeof useMapExpansion>}) {
  return <button className="expand-map" ref={view.trigger} aria-pressed={view.expanded}
    onClick={() => view.setExpanded(!view.expanded)}>
    <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d={view.expanded ? 'M3 9h6V3m12 12h-6v6' : 'M9 3H3v6m12 12h6v-6M3 3l6 6m12 12-6-6'}/>
    </svg>{view.expanded ? 'Volver' : 'Ampliar mapa'}
  </button>;
}
