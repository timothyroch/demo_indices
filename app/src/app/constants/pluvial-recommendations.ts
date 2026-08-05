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

export const pluvialRiskLevelToDecisionSeverity = mapFloodRiskLevelToDecisionSeverity;

const PLUVIAL_MONTREAL_RECO_NONE = section('Risque faible — que faire ?', [
  "Rester à l'affût des prévisions et des avis des autorités",
  'Vérifier que les drains extérieurs et gouttières sont dégagés',
  "Éviter de s'approcher des zones basses susceptibles de s'inonder rapidement",
]);

const PLUVIAL_MONTREAL_RECO_NORMALE_MAIN = section(
  'Inondation pluviale — risque modéré — que faire ?',
  [...SHARED_FLOOD_RECO_NORMALE_MAIN, "Dégager les entrées d'eau pluviale autour du bâtiment"],
);

const PLUVIAL_MONTREAL_RECO_AT_RISK = section("Personnes à risque lors d'inondations pluviales", [
  ...SHARED_FLOOD_AT_RISK_BASE,
  "Personnes en situation d'itinérance",
  'Résidents de sous-sols ou de zones basses inondables',
]);

const PLUVIAL_MONTREAL_RECO_EXTREME_SECTIONS: readonly PublicDecisionRecoSection[] = [
  section('Inondation pluviale extrême — que faire ?', SHARED_FLOOD_EXTREME_IMMEDIATE_ACTIONS_BASE),
  section('Protéger son domicile', [
    ...SHARED_FLOOD_EXTREME_PROTECT_HOME_BASE,
    "Dégager les drains de surface pour faciliter l'écoulement des eaux",
    "Ne pas utiliser les installations sanitaires si le réseau d'égouts est saturé",
  ]),
  section("Surveiller l'état du bâtiment et des environs", [
    'Montée rapide des eaux autour du bâtiment ou dans les sous-sols',
    'Refoulement des égouts ou des drains intérieurs',
    'Présence de courants forts dans les rues ou ruelles',
    "Odeurs de gaz ou fils électriques sous l'eau",
  ]),
  section('Mesures complémentaires', [
    ...SHARED_FLOOD_EXTREME_COMPLEMENTARY_MEASURES_BASE,
    "Éviter tout contact avec l'eau de ruissellement (contamination possible)",
  ]),
  section("Après l'inondation", [
    ...SHARED_FLOOD_EXTREME_AFTER_FLOOD_BASE,
    "Jeter les aliments ayant été en contact avec l'eau de ruissellement",
  ]),
];

const PLUVIAL_LAVAL_RECO_NONE = section('Risque faible — que faire ?', [
  "Rester à l'affût des prévisions et des avis des autorités",
  'Vérifier que les drains extérieurs et gouttières sont dégagés',
  "Éviter de s'approcher des zones basses susceptibles de s'inonder rapidement",
]);

const PLUVIAL_LAVAL_RECO_NORMALE_MAIN = section(
  'Inondation pluviale — risque modéré — que faire ?',
  [...SHARED_FLOOD_RECO_NORMALE_MAIN, "Dégager les entrées d'eau pluviale autour du bâtiment"],
);

const PLUVIAL_LAVAL_RECO_AT_RISK = section("Personnes à risque lors d'inondations pluviales", [
  ...SHARED_FLOOD_AT_RISK_BASE,
  "Personnes en situation d'itinérance",
  'Résidents de sous-sols ou de zones basses inondables',
]);

const PLUVIAL_LAVAL_RECO_EXTREME_SECTIONS: readonly PublicDecisionRecoSection[] = [
  section('Inondation pluviale extrême — que faire ?', SHARED_FLOOD_EXTREME_IMMEDIATE_ACTIONS_BASE),
  section('Protéger son domicile', [
    ...SHARED_FLOOD_EXTREME_PROTECT_HOME_BASE,
    "Dégager les drains de surface pour faciliter l'écoulement des eaux",
    "Ne pas utiliser les installations sanitaires si le réseau d'égouts est saturé",
  ]),
  section("Surveiller l'état du bâtiment et des environs", [
    'Montée rapide des eaux autour du bâtiment ou dans les sous-sols',
    'Refoulement des égouts ou des drains intérieurs',
    'Présence de courants forts dans les rues ou ruelles',
    "Odeurs de gaz ou fils électriques sous l'eau",
  ]),
  section('Mesures complémentaires', [
    ...SHARED_FLOOD_EXTREME_COMPLEMENTARY_MEASURES_BASE,
    "Éviter tout contact avec l'eau de ruissellement (contamination possible)",
  ]),
  section("Après l'inondation", [
    ...SHARED_FLOOD_EXTREME_AFTER_FLOOD_BASE,
    "Jeter les aliments ayant été en contact avec l'eau de ruissellement",
  ]),
];

export const PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL: PublicDecisionRecommendationsContent =
  {
    none: PLUVIAL_MONTREAL_RECO_NONE,
    normale: [PLUVIAL_MONTREAL_RECO_NORMALE_MAIN],
    extreme: PLUVIAL_MONTREAL_RECO_EXTREME_SECTIONS,
    atRisk: PLUVIAL_MONTREAL_RECO_AT_RISK,
  };

export const PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_LAVAL: PublicDecisionRecommendationsContent = {
  none: PLUVIAL_LAVAL_RECO_NONE,
  normale: [PLUVIAL_LAVAL_RECO_NORMALE_MAIN],
  extreme: PLUVIAL_LAVAL_RECO_EXTREME_SECTIONS,
  atRisk: PLUVIAL_LAVAL_RECO_AT_RISK,
};

export const PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS =
  PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL;

export const PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY = {
  montreal: PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL,
  laval: PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_LAVAL,
} as const;
