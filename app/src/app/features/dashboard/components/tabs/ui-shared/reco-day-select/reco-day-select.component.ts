import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-reco-day-select',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reco-day-select.component.html',
  styleUrl: './reco-day-select.component.scss',
})
export class RecoDaySelectComponent {
  private static _idSeq = 0;
  readonly controlId = `reco-day-select-${RecoDaySelectComponent._idSeq++}`;

  @Input({ required: true }) options!: { id: string; label: string }[];
  @Input({ required: true }) selectedId!: string;

  @Output() selectedIdChange = new EventEmitter<string>();

  onChange(value: string): void {
    this.selectedIdChange.emit(value);
  }
}
