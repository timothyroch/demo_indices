import { Component, Input } from '@angular/core';
import { Explainability } from '../../../../../../interfaces/flood.model';
import { SECTION_STRINGS } from '../../../../../../constants/dashboard';

@Component({
  selector: 'app-explainability-content',
  imports: [],
  templateUrl: './explainability-content.component.html',
  styleUrl: './explainability-content.component.scss',
})
export class ExplainabilityContentComponent {
  @Input() explainability: Explainability[] | null = null;

  readonly sectionTitle = SECTION_STRINGS.EXPLAINABILITY_TITLE;
}
