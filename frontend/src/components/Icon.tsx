type Name = 'route' | 'arrow' | 'target' | 'layers' | 'swap' | 'reset' | 'chevron' | 'info' | 'walk' | 'pin' | 'check';
const paths: Record<Name, string> = {
  route: 'M5 19 10 5l4 9 5-5 M16 9h3v3',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  target: 'M12 3v3m0 12v3M3 12h3m12 0h3 M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0',
  layers: 'm3 8 9-5 9 5-9 5-9-5m0 5 9 5 9-5M3 18l9 5 9-5',
  swap: 'M7 4v16m-4-4 4 4 4-4M17 20V4m-4 4 4-4 4 4',
  reset: 'M4 10a8 8 0 1 1 1 8M4 4v6h6',
  chevron: 'm6 9 6 6 6-6',
  info: 'M12 11v6m0-10v.1M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  walk: 'm13 7-3 5-4 2m4-2 4 4-2 5m2-14 3 5 4 1M10 12l-2 9M15 3v.1',
  pin: 'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  check: 'm5 12 4 4L19 6',
};
export function Icon({ name, className = '' }: { name: Name; className?: string }) {
  return <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
