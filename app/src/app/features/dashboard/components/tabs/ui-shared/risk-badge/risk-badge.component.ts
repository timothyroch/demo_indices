import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-risk-badge',
  imports: [CommonModule],
  templateUrl: './risk-badge.component.html',
  styleUrl: './risk-badge.component.scss',
})
export class RiskBadgeComponent {
  @Input() riskLevelClass = '';
  @Input() riskLevelLabel = '';
}
