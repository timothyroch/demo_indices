import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FOOTER_STRINGS } from '../../../../constants/dashboard';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.css'],
})
export class FooterComponent {
  currentYear = new Date().getFullYear();
  readonly strings = FOOTER_STRINGS;
}
