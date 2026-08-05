import { CommonModule } from '@angular/common';
import { Component, HostListener, Input, TemplateRef } from '@angular/core';

@Component({
  selector: 'app-info-bubble',
  templateUrl: './info-bubble.component.html',
  styleUrl: './info-bubble.component.scss',
  standalone: true,
  imports: [CommonModule],
})
export class InfoBubbleComponent {
  @Input() message = '';
  @Input() symbol = '?';
  @Input() templateContent?: TemplateRef<unknown>;

  isOpen = false;

  onToggle(): void {
    this.isOpen = !this.isOpen;
  }

  onMouseEnter(): void {
    this.isOpen = true;
  }

  onMouseLeave(): void {
    this.isOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement | null;
    if (!target?.closest('app-info-bubble')) {
      this.isOpen = false;
    }
  }
}
