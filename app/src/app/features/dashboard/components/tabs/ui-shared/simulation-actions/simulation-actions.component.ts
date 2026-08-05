import { Component, EventEmitter, Input, Output } from '@angular/core';
import { SIMULATION_STRINGS } from '../../../../../../constants/side-panel';

@Component({
  selector: 'app-simulation-actions',
  imports: [],
  templateUrl: './simulation-actions.component.html',
  styleUrl: './simulation-actions.component.scss',
})
export class SimulationActionsComponent {
  @Input() isLoading = false;

  @Output() applySimulation = new EventEmitter<void>();
  @Output() resetSimulation = new EventEmitter<void>();

  simulationStrings = SIMULATION_STRINGS;
}
