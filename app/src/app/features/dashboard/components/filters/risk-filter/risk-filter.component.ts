import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  FILTER_STRINGS,
  PERCENT_CHECKPOINTS,
  PERCENT_TRACK_GRADIENT,
  RiskKind,
} from '../../../../../constants/dashboard';
import {
  HUMIDEX_BREAKPOINTS,
  HUMIDEX_CHECKPOINTS,
  HUMIDEX_MAX,
  HUMIDEX_MIN,
  HUMIDEX_TRACK_GRADIENT,
} from '../../../../../constants/heatwave';

const SCORE_LEVELS = ['low', 'moderate', 'high', 'danger'] as const;
type ScoreLevel = (typeof SCORE_LEVELS)[number];
type SliderMode = 'percent' | 'humidex';

export interface SliderCheckpoint {
  value: number;
  left: string;
  ariaLabel: string;
}

export interface SliderConfig {
  mode: SliderMode;
  min: number;
  max: number;
  step: number;
  unit: string;
  trackGradient: string;
  checkpoints: SliderCheckpoint[];
  sections: { label: string; cls: string }[];
  minLabel: string;
  maxLabel: string;
}

@Component({
  selector: 'app-risk-filter',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './risk-filter.component.html',
  styleUrl: './risk-filter.component.scss',
})
export class RiskFilterComponent {
  @Input() scoreThreshold = 0;
  @Input() riskKind: RiskKind = 'pluvial';

  @Output() scoreThresholdChange = new EventEmitter<number>();

  readonly strings = FILTER_STRINGS;

  // Manual Input State
  isEditingScoreThreshold = false;
  scoreThresholdInputValue = '';
  private previousScoreThreshold = 0;
  private hasTypedScoreThreshold = false;

  get cfg(): SliderConfig {
    if (this.riskKind === 'canicules') {
      return {
        mode: 'humidex',
        min: HUMIDEX_MIN,
        max: HUMIDEX_MAX,
        step: 1,
        unit: '',
        trackGradient: HUMIDEX_TRACK_GRADIENT,
        checkpoints: HUMIDEX_CHECKPOINTS,
        sections: [
          { label: "Pas/peu d'inconfort", cls: 'humidex-low' },
          { label: 'Un certain inconfort', cls: 'humidex-moderate' },
          { label: "Beaucoup d'inconfort", cls: 'humidex-heavy' },
          { label: 'Danger', cls: 'humidex-danger' },
        ],
        minLabel: String(HUMIDEX_MIN),
        maxLabel: String(HUMIDEX_MAX),
      };
    }

    return {
      mode: 'percent',
      min: 0,
      max: 100,
      step: 0.01,
      unit: '%',
      trackGradient: PERCENT_TRACK_GRADIENT,
      checkpoints: PERCENT_CHECKPOINTS,
      sections: [
        { label: 'Vert - faible', cls: 'slider-risk-section--low' },
        { label: 'Orange - modéré', cls: 'slider-risk-section--moderate' },
        { label: 'Rouge - élevé', cls: 'slider-risk-section--high' },
      ],
      minLabel: this.strings.MIN_BOUND || '0 %',
      maxLabel: this.strings.MAX_BOUND || '100 %',
    };
  }

  get levelClass(): ScoreLevel {
    if (this.riskKind === 'canicules') {
      if (this.scoreThreshold < HUMIDEX_BREAKPOINTS.comfort) return 'low';
      if (this.scoreThreshold < HUMIDEX_BREAKPOINTS.discomfort) return 'moderate';
      if (this.scoreThreshold < HUMIDEX_BREAKPOINTS.heavy) return 'high';
      return 'danger';
    }

    if (this.scoreThreshold <= 20) return SCORE_LEVELS[0];
    if (this.scoreThreshold <= 50) return SCORE_LEVELS[1];
    return SCORE_LEVELS[2];
  }

  // --- NEW GETTERS FOR THE UI ---
  get topTitle(): string {
    return this.cfg.mode === 'humidex' ? 'SEUIL MINIMAL — HUMIDEX' : 'SEUIL MINIMAL — RISQUE';
  }

  get prefixLabel(): string {
    return this.cfg.mode === 'humidex' ? 'Humidex :' : 'Risque :';
  }

  get currentSectionLabel(): string {
    if (this.levelClass === 'low') return this.cfg.sections[0].label;
    if (this.levelClass === 'moderate') return this.cfg.sections[1].label;
    if (this.levelClass === 'high') return this.cfg.sections[2].label;
    if (this.levelClass === 'danger') return this.cfg.sections[3]?.label ?? '';
    return '';
  }

  get trackStyle(): string {
    return `background: ${this.cfg.trackGradient}`;
  }

  // ... (Keep all your existing manual entry / onSliderInput methods exactly as they are) ...
  onSliderInput(event: Event) {
    const value = Number.parseFloat((event.target as HTMLInputElement).value);
    this.apply(value);
  }

  setPreset(value: number): void {
    this.apply(value);
  }

  onManualChange(value: number | string | null): void {
    if (value === null || value === '') {
      this.scoreThresholdInputValue = '';
      return;
    }

    this.hasTypedScoreThreshold = true;
    this.scoreThresholdInputValue = String(value);

    const parsedValue = typeof value === 'number' ? value : this.parseManualThresholdValue(value);

    if (!Number.isFinite(parsedValue)) return;
    this.apply(parsedValue);
  }

  onManualKeydown(event: KeyboardEvent): void {
    const allowedControlKeys = new Set([
      'Backspace',
      'Delete',
      'Tab',
      'Enter',
      'ArrowLeft',
      'ArrowRight',
      'Home',
      'End',
    ]);
    if (allowedControlKeys.has(event.key) || event.ctrlKey || event.metaKey) return;

    const isDigit = /^\d$/.test(event.key);
    const isDecimalSeparator = event.key === '.' || event.key === ',';
    const inputElement =
      event.currentTarget instanceof HTMLInputElement ? event.currentTarget : null;

    if (!inputElement) {
      event.preventDefault();
      return;
    }

    const hasSeparator = /[.,]/.test(inputElement.value);
    if (!isDigit && !(isDecimalSeparator && !hasSeparator)) {
      event.preventDefault();
      return;
    }

    const nextRawValue = this.computeNextInputValue(inputElement, event.key);
    const parsedNextValue = this.parseManualThresholdValue(nextRawValue);

    if (Number.isFinite(parsedNextValue) && parsedNextValue > this.cfg.max) {
      event.preventDefault();
    }
  }

  onManualFocus(): void {
    this.isEditingScoreThreshold = true;
    this.previousScoreThreshold = this.scoreThreshold;
    this.scoreThresholdInputValue = '';
    this.hasTypedScoreThreshold = false;
  }

  onManualBlur(): void {
    if (!this.hasTypedScoreThreshold || this.scoreThresholdInputValue.trim() === '') {
      this.apply(this.previousScoreThreshold);
    }
    this.isEditingScoreThreshold = false;
    this.scoreThresholdInputValue = '';
    this.hasTypedScoreThreshold = false;
  }

  onManualPaste(event: ClipboardEvent): void {
    const pastedText = event.clipboardData?.getData('text') ?? '';
    const parsedValue = this.parseManualThresholdValue(pastedText);

    if (!Number.isFinite(parsedValue) || parsedValue < this.cfg.min || parsedValue > this.cfg.max) {
      event.preventDefault();
    }
  }

  private apply(value: number) {
    const v = Math.min(this.cfg.max, Math.max(this.cfg.min, value));
    const normalizedValue = Number.isFinite(v) ? Number(v.toFixed(2)) : 0;

    this.scoreThresholdChange.emit(normalizedValue);
  }

  private parseManualThresholdValue(value: string): number {
    const normalized = value.replace(',', '.').replaceAll(/[^\d.]/g, '');
    const firstDotIndex = normalized.indexOf('.');
    const safeValue =
      firstDotIndex >= 0
        ? `${normalized.slice(0, firstDotIndex + 1)}${normalized
            .slice(firstDotIndex + 1)
            .replaceAll('.', '')}`
        : normalized;

    return Number.parseFloat(safeValue);
  }

  private computeNextInputValue(inputElement: HTMLInputElement, key: string): string {
    const selectionStart = inputElement.selectionStart ?? inputElement.value.length;
    const selectionEnd = inputElement.selectionEnd ?? inputElement.value.length;
    const normalizedKey = key === ',' ? '.' : key;

    return `${inputElement.value.slice(0, selectionStart)}${normalizedKey}${inputElement.value.slice(selectionEnd)}`;
  }
}
