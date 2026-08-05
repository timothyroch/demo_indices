import type {
  PublicDecisionRecoSection,
  PublicDecisionRecommendationsContent,
} from '../interfaces/public-decision-recommendations.model';
import type { PublicDecisionSeverity } from './dashboard';
import { mapFloodRiskLevelToDecisionSeverity } from './recommendations.shared';
import { SNOW_RISK_CLASSES, snowPredictionValueToRiskLevel } from './snow';

export const snowRiskLevelToDecisionSeverity = mapFloodRiskLevelToDecisionSeverity;

export function snowPredictionValueToDecisionSeverity(
  predictionValue: number | undefined | null,
): PublicDecisionSeverity {
  const band = snowPredictionValueToRiskLevel(predictionValue);
  const riskClass = SNOW_RISK_CLASSES[band];
  return snowRiskLevelToDecisionSeverity(riskClass);
}

const SNOW_MONTREAL_NONE: PublicDecisionRecoSection = {
  title: 'Risque faible — que faire ?',
  bullets: [
    'Rester à l’affût des prévisions et des avis des autorités',
    'Adapter ses déplacements si les conditions deviennent difficiles',
    'Prévoir des vêtements chauds et une conduite prudente en cas de neige',
  ],
};

const SNOW_MONTREAL_NORMALE_MAIN: PublicDecisionRecoSection = {
  title: 'Tempête hivernale normale — que faire ?',
  bullets: [
    'Rester informé des conditions météorologiques et des consignes des autorités',
    'Adapter ses déplacements en fonction des conditions routières',
    'Réduire la vitesse et augmenter les distances de sécurité en voiture',
    'Être vigilant envers les piétons et les zones non déneigées',
    'Porter des vêtements appropriés pour se protéger du froid',
    'Limiter les déplacements non essentiels si les conditions se détériorent',
    'Déneiger les entrées, sorties, balcons et accès de manière sécuritaire',
    'Vérifier que le numéro d’adresse est visible depuis la rue',
    'Faire preuve de prudence lors du pelletage et éviter les efforts excessifs',
    'Maintenir un contact régulier avec ses proches, notamment les personnes vulnérables',
  ],
};

const SNOW_MONTREAL_AT_RISK: PublicDecisionRecoSection = {
  title: 'Personnes à risque lors de tempêtes hivernales',
  bullets: [
    'Personnes âgées, en raison d’une plus grande vulnérabilité au froid et aux chutes',
    'Personnes vivant seules ou en situation d’isolement',
    'Personnes à mobilité réduite ou en situation de handicap',
    'Personnes atteintes de maladies chroniques (cardiaques, respiratoires, etc.)',
    'Enfants en bas âge',
    'Femmes enceintes',
    'Personnes en situation d’itinérance',
    'Personnes dépendantes d’équipements médicaux nécessitant de l’électricité',
    'Travailleurs extérieurs (exposés prolongés au froid)',
    'Personnes ne disposant pas d’un logement adéquat ou mal chauffé',
  ],
};

const SNOW_MONTREAL_EXTREME_SECTIONS: readonly PublicDecisionRecoSection[] = [
  {
    title: 'Tempête hivernale extrême — que faire ?',
    bullets: [
      'Éviter tout déplacement non essentiel et privilégier le télétravail',
      'Suivre strictement les consignes des autorités et des services d’urgence',
      'Se préparer à rester à domicile pendant une période prolongée',
      'Préparer une trousse d’urgence (eau, nourriture, médicaments, lampes, piles)',
      'Prévoir une autonomie en eau potable et en nourriture pour plusieurs jours',
      'Charger tous les appareils électroniques à l’avance',
      'Prévoir des sources de chauffage alternatives sécuritaires',
      'Constituer des réserves de combustible si nécessaire',
    ],
  },
  {
    title: 'Se préparer à une panne d’électricité',
    bullets: [
      'Conserver la chaleur dans le logement',
      'Fermer les pièces inutilisées',
      'Utiliser des couvertures',
    ],
  },
  {
    title: 'Surveiller l’état du bâtiment',
    bullets: [
      'Accumulation de neige sur le toit',
      'Présence de glace et de glaçons dangereux',
      'Signes de surcharge (fissures, craquements, déformations)',
    ],
  },
  {
    title: 'Mesures complémentaires',
    bullets: [
      'Faire appel à des professionnels pour le déneigement des toitures',
      'Déneiger les accès essentiels (sorties de secours, entrées)',
      'Dégager les véhicules si nécessaire',
      'Vérifier régulièrement l’état des proches, en particulier les personnes vulnérables',
      'Porter assistance aux voisins ou personnes isolées si possible',
      'Utiliser les appareils de chauffage de manière sécuritaire',
      'Ne jamais utiliser d’équipements extérieurs à l’intérieur (barbecue, génératrice)',
      'S’assurer du bon fonctionnement des détecteurs de fumée et de monoxyde de carbone',
      'Faire preuve de patience face aux retards de services (déneigement, collectes)',
      'Respecter les opérations municipales et éviter de nuire au travail des équipes',
    ],
  },
  {
    title: 'Après la tempête',
    bullets: [
      'Faire preuve de prudence lors des déplacements',
      'Éviter les zones dangereuses (fils électriques, branches)',
      'Continuer de suivre les consignes des autorités',
    ],
  },
];

const SNOW_LAVAL_NONE: PublicDecisionRecoSection = {
  title: 'Risque faible — que faire ?',
  bullets: [
    'Rester à l’affût des prévisions et des avis des autorités',
    'Adapter ses déplacements si les conditions deviennent difficiles',
    'Prévoir des vêtements chauds et une conduite prudente en cas de neige',
  ],
};

const SNOW_LAVAL_NORMALE_MAIN: PublicDecisionRecoSection = {
  title: 'Tempête hivernale normale — que faire ?',
  bullets: [
    'Rester informé des conditions météorologiques et des consignes des autorités',
    'Adapter ses déplacements en fonction des conditions routières',
    'Réduire la vitesse et augmenter les distances de sécurité en voiture',
    'Être vigilant envers les piétons et les zones non déneigées',
    'Porter des vêtements appropriés pour se protéger du froid',
    'Limiter les déplacements non essentiels si les conditions se détériorent',
    'Déneiger les entrées, sorties, balcons et accès de manière sécuritaire',
    'Vérifier que le numéro d’adresse est visible depuis la rue',
    'Faire preuve de prudence lors du pelletage et éviter les efforts excessifs',
    'Maintenir un contact régulier avec ses proches, notamment les personnes vulnérables',
  ],
};

const SNOW_LAVAL_AT_RISK: PublicDecisionRecoSection = {
  title: 'Personnes à risque lors de tempêtes hivernales',
  bullets: [
    'Personnes âgées, en raison d’une plus grande vulnérabilité au froid et aux chutes',
    'Personnes vivant seules ou en situation d’isolement',
    'Personnes à mobilité réduite ou en situation de handicap',
    'Personnes atteintes de maladies chroniques (cardiaques, respiratoires, etc.)',
    'Enfants en bas âge',
    'Femmes enceintes',
    'Personnes en situation d’itinérance',
    'Personnes dépendantes d’équipements médicaux nécessitant de l’électricité',
    'Travailleurs extérieurs (exposés prolongés au froid)',
    'Personnes ne disposant pas d’un logement adéquat ou mal chauffé',
  ],
};

const SNOW_LAVAL_EXTREME_SECTIONS: readonly PublicDecisionRecoSection[] = [
  {
    title: 'Tempête hivernale extrême — que faire ?',
    bullets: [
      'Éviter tout déplacement non essentiel et privilégier le télétravail',
      'Suivre strictement les consignes des autorités et des services d’urgence',
      'Se préparer à rester à domicile pendant une période prolongée',
      'Préparer une trousse d’urgence (eau, nourriture, médicaments, lampes, piles)',
      'Prévoir une autonomie en eau potable et en nourriture pour plusieurs jours',
      'Charger tous les appareils électroniques à l’avance',
      'Prévoir des sources de chauffage alternatives sécuritaires',
      'Constituer des réserves de combustible si nécessaire',
    ],
  },
  {
    title: 'Se préparer à une panne d’électricité',
    bullets: [
      'Conserver la chaleur dans le logement',
      'Fermer les pièces inutilisées',
      'Utiliser des couvertures',
    ],
  },
  {
    title: 'Surveiller l’état du bâtiment',
    bullets: [
      'Accumulation de neige sur le toit',
      'Présence de glace et de glaçons dangereux',
      'Signes de surcharge (fissures, craquements, déformations)',
    ],
  },
  {
    title: 'Mesures complémentaires',
    bullets: [
      'Faire appel à des professionnels pour le déneigement des toitures',
      'Déneiger les accès essentiels (sorties de secours, entrées)',
      'Dégager les véhicules si nécessaire',
      'Vérifier régulièrement l’état des proches, en particulier les personnes vulnérables',
      'Porter assistance aux voisins ou personnes isolées si possible',
      'Utiliser les appareils de chauffage de manière sécuritaire',
      'Ne jamais utiliser d’équipements extérieurs à l’intérieur (barbecue, génératrice)',
      'S’assurer du bon fonctionnement des détecteurs de fumée et de monoxyde de carbone',
      'Faire preuve de patience face aux retards de services (déneigement, collectes)',
      'Respecter les opérations municipales et éviter de nuire au travail des équipes',
    ],
  },
  {
    title: 'Après la tempête',
    bullets: [
      'Faire preuve de prudence lors des déplacements',
      'Éviter les zones dangereuses (fils électriques, branches)',
      'Continuer de suivre les consignes des autorités',
    ],
  },
];

export const SNOW_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL: PublicDecisionRecommendationsContent = {
  none: SNOW_MONTREAL_NONE,
  normale: [SNOW_MONTREAL_NORMALE_MAIN],
  extreme: SNOW_MONTREAL_EXTREME_SECTIONS,
  atRisk: SNOW_MONTREAL_AT_RISK,
};

export const SNOW_PUBLIC_DECISION_RECOMMENDATIONS_LAVAL: PublicDecisionRecommendationsContent = {
  none: SNOW_LAVAL_NONE,
  normale: [SNOW_LAVAL_NORMALE_MAIN],
  extreme: SNOW_LAVAL_EXTREME_SECTIONS,
  atRisk: SNOW_LAVAL_AT_RISK,
};

export const SNOW_PUBLIC_DECISION_RECOMMENDATIONS = SNOW_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL;

export const SNOW_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY = {
  montreal: SNOW_PUBLIC_DECISION_RECOMMENDATIONS_MONTREAL,
  laval: SNOW_PUBLIC_DECISION_RECOMMENDATIONS_LAVAL,
} as const;
