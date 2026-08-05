import { Component, EventEmitter, Input, Output } from '@angular/core';
import { SIMULATION_STRINGS } from '../../../../../../constants/side-panel';

@Component({
  selector: 'app-simulation-mode-toggle',
  imports: [],
  templateUrl: './simulation-mode-toggle.component.html',
  styleUrl: './simulation-mode-toggle.component.scss',
})
export class SimulationModeToggleComponent {
  @Input() isSimulationOpen!: boolean;

  @Output() forecastClick = new EventEmitter<void>();
  @Output() simulationClick = new EventEmitter<void>();

  simulationStrings = SIMULATION_STRINGS;
}
