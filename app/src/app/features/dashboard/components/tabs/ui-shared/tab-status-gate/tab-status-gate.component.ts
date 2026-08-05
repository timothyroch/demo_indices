import { Component, Input } from '@angular/core';
import { LOADING_LABEL, LoadingStatus } from '../../../../../../constants/dashboard';

@Component({
  selector: 'app-tab-status-gate',
  imports: [],
  templateUrl: './tab-status-gate.component.html',
  styleUrl: './tab-status-gate.component.scss',
})
export class TabStatusGateComponent {
  @Input() status: LoadingStatus = 'loading';
  @Input() errorMessage: string | null = null;

  readonly loadingLabel: string = LOADING_LABEL;
}
