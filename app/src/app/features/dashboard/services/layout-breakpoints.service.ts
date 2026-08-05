import { Injectable, NgZone, inject, signal } from '@angular/core';

export const COMPARISON_LAYOUT_MIN_WIDTH_PX = 1280;

@Injectable({ providedIn: 'root' })
export class LayoutBreakpointsService {
  private readonly zone = inject(NgZone);

  readonly comparisonAllowed = signal(
    typeof window !== 'undefined'
      ? window.matchMedia(`(min-width: ${COMPARISON_LAYOUT_MIN_WIDTH_PX}px)`).matches
      : true,
  );

  constructor() {
    if (typeof window === 'undefined') {
      return;
    }
    const mql = window.matchMedia(`(min-width: ${COMPARISON_LAYOUT_MIN_WIDTH_PX}px)`);
    const onChange = (e: MediaQueryListEvent) => {
      this.zone.run(() => this.comparisonAllowed.set(e.matches));
    };
    mql.addEventListener('change', onChange);
  }
}
