import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FILTER_STRINGS } from '../../../../../constants/dashboard';
import { SocialFilter } from '../../../../../interfaces/social-filters';

@Component({
  selector: 'app-social-filter',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './social-filter.component.html',
  styleUrl: './social-filter.component.scss',
})
export class SocialFilterComponent {
  @Input() socialFilter!: SocialFilter;
  @Output() socialFilterChange = new EventEmitter<SocialFilter>();

  readonly strings = FILTER_STRINGS;

  onSocialFilterChange(): void {
    this.socialFilterChange.emit(this.socialFilter);
  }
}
