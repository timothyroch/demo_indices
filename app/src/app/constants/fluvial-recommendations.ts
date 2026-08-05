import type {
  PublicDecisionRecoSection,
  PublicDecisionRecommendationsContent,
} from '../interfaces/public-decision-recommendations.model';
import {
  mapFloodRiskLevelToDecisionSeverity,
  section,
  SHARED_FLOOD_AT_RISK_BASE,
  SHARED_FLOOD_EXTREME_AFTER_FLOOD_BASE,
  SHARED_FLOOD_EXTREME_COMPLEMENTARY_MEASURES_BASE,
  SHARED_FLOOD_EXTREME_IMMEDIATE_ACTIONS_BASE,
  SHARED_FLOOD_EXTREME_PROTECT_HOME_BASE,
  SHARED_FLOOD_RECO_NORMALE_MAIN,
} from './recommendations.shared';

export const fluvialRiskLevelToDecisionSeverity = mapFloodRiskLevelToDecisionSeverity;

const FLUVIAL_MONTREAL_RECO_NONE = section('Risque faible — que faire ?', [
  "Rester à l'affût des prévisions et des avis des autorités",
  "Éviter de s'approcher des cours d'eau en période de crue potentielle",
  'Vérifier que les soupapes de refoulement et drains sont en bon état',
]);

const FLUVIAL_MONTREAL_RECO_NORMALE_MAIN = section(
  'Risque modéré — que faire ?',
  SHARED_FLOOD_RECO_NORMALE_MAIN,
);

const FLUVIAL_MONTREAL_RECO_AT_RISK = section("Personnes à risque lors d'inondations fluviales", [
  ...SHARED_FLOOD_AT_RISK_BASE,
  "Personnes en situation d'itinérance près des berges",
  'Résidents de sous-sols ou de zones basses inondables près des berges',
]);

const FLUVIAL_MONTREAL_RECO_EXTREME_SECTIONS: readonly PublicDecisionRecoSection[] = [
  section('Risque élevé — que faire ?', SHARED_FLOOD_EXTREME_IMMEDIATE_ACTIONS_BASE),
  section('Protéger son domicile', [
    ...SHARED_FLOOD_EXTREME_PROTECT_HOME_BASE,
    "Ne pas utiliser les installations sanitaires si le réseau d'égouts est saturé",
  ]),
  section("Surveiller l'état du bâtiment et des environs", [
    'Montée rapide des eaux autour du bâtiment',
    'Affaissement ou fissures des fondations',
    'Présence de débris flottants ou de courants forts',
    "Odeurs de gaz ou fils électriques sous l'eau",
  ]),
  section('Mesures complémentaires', [
    ...SHARED_FLOOD_EXTREME_COMPLEMENTARY_MEASURES_BASE,
    "Éviter tout contact avec l'eau de crue (contamination possible)",
  ]),
  section("Après l'inondation", [
    ...SHARED_FLOOD_EXTREME_AFTER_FLOOD_BASE,
    "Jeter les aliments ayant été en contact avec l'eau de crue",
  ]),
];

const FLUVIAL_LAVAL_RECO_NONE = section('Risque faible — que faire ?', [
  "Rester à l'affût des prévisions et des avis des autorités",
  "Éviter de s'approcher des cours d'eau en période de crue potentielle",
  'Vérifier que les soupapes de refoulement et drains sont en bon état',
]);

const FLUVIAL_LAVAL_RECO_NORMALE_MAIN = section(
  'Risque modéré — que faire ?',
  SHARED_FLOOD_RECO_NORMALE_MAIN,
);

const FLUVIAL_LAVAL_RECO_AT_RISK = section("Personnes à risque lors d'inondations fluviales", [
  ...SHARED_FLOOD_AT_RISK_BASE,
  "Personnes en situation d'itinérance près des berges",
  'Résidents de sous-sols ou de zones basses inondables près des berges',
]);

const FLUVIAL_LAVAL_RECO_EXTREME_SECTIONS: readonly PublicDecisionRecoSection[] = [
  section('Risque élevé — que faire ?', SHARED_FLOOD_EXTREME_IMMEDIATE_ACTIONS_BASE),
  section('Protéger son domicile', [
    ...SHARED_FLOOD_EXTREME_PROTECT_HOME_BASE,
    "Ne pas utiliser les installations sanitaires si le réseau d'égouts est saturé",
  ]),
  section("Surveiller l'état du bâtiment et des environs", [
    'Montée rapide des eaux autour du bâtiment',
    'Affaissement ou fissures des fondations',
    'Présence de débris flottants ou de courants forts',
    "Odeurs de gaz ou fils électriques sous l'eau",
  ]),
  section('Mesures complémentaires', [
    ...SHARED_FLOOD_EXTREME_COMPLEMENTARY_MEASURES_BASE,
    "Éviter tout contact avec l'eau de crue (contamination possible)",
  ]),
  section("Après l'inondation", [
    ...SHARED_FLOOD_EXTREME_AFTER_FLOOD_BASE,
    "Jeter les aliments ayant été en contact avec l'eau de crue",
  ]),
];

export const FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL: PublicDecisionRecommendationsContent =
  {
    none: FLUVIAL_MONTREAL_RECO_NONE,
    normale: [FLUVIAL_MONTREAL_RECO_NORMALE_MAIN],
    extreme: FLUVIAL_MONTREAL_RECO_EXTREME_SECTIONS,
    atRisk: FLUVIAL_MONTREAL_RECO_AT_RISK,
  };

export const FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_LAVAL: PublicDecisionRecommendationsContent = {
  none: FLUVIAL_LAVAL_RECO_NONE,
  normale: [FLUVIAL_LAVAL_RECO_NORMALE_MAIN],
  extreme: FLUVIAL_LAVAL_RECO_EXTREME_SECTIONS,
  atRisk: FLUVIAL_LAVAL_RECO_AT_RISK,
};

export const FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS =
  FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL;

export const FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY = {
  montreal: FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL,
  laval: FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_LAVAL,
} as const;
