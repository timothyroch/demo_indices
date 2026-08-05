import type { PublicDecisionRecoSection } from '../interfaces/public-decision-recommendations.model';
import {
  PUBLIC_DECISION_SEVERITY,
  RISK_BAND_CLASS,
  type PublicDecisionSeverity,
} from './dashboard';

export const RECO_DAY_ID_TODAY = 'today' as const;

export function mapFloodRiskLevelToDecisionSeverity(
  riskLevelClass: string | undefined,
): PublicDecisionSeverity {
  if (riskLevelClass === RISK_BAND_CLASS.ORANGE) return PUBLIC_DECISION_SEVERITY.Normale;
  if (riskLevelClass === RISK_BAND_CLASS.RED) return PUBLIC_DECISION_SEVERITY.Extreme;
  return PUBLIC_DECISION_SEVERITY.None;
}

export function coerceProbabilityValue(raw: unknown): number {
  if (raw == null || raw === '') return Number.NaN;
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw;
  const n = Number(String(raw).trim().replace(',', '.'));
  return Number.isFinite(n) ? n : Number.NaN;
}

export function normalizeProbability(value: unknown): number {
  const n = coerceProbabilityValue(value);
  if (Number.isNaN(n)) return -1;
  if (n > 1) return n / 100;
  return n;
}

export function probabilityToRiskLevelClass(p: unknown): string {
  const p01 = normalizeProbability(p);
  if (p01 < 0 || Number.isNaN(p01)) return '';
  const pct = p01 * 100;
  if (pct <= 20) return RISK_BAND_CLASS.GREEN;
  if (pct <= 50) return RISK_BAND_CLASS.ORANGE;
  return RISK_BAND_CLASS.RED;
}

export function section(title: string, bullets: readonly string[]): PublicDecisionRecoSection {
  return { title, bullets: [...bullets] };
}

export const SHARED_FLOOD_AT_RISK_BASE = [
  "Personnes âgées, en raison d'une plus grande vulnérabilité physique",
  "Personnes vivant seules ou en situation d'isolement",
  'Personnes à mobilité réduite ou en situation de handicap',
  'Personnes atteintes de maladies chroniques nécessitant des soins réguliers',
  'Enfants en bas âge',
  'Femmes enceintes',
  "Personnes dépendantes d'équipements médicaux nécessitant de l'électricité",
  'Personnes ne disposant pas de moyens de transport pour évacuer',
];

export const SHARED_FLOOD_RECO_NORMALE_MAIN = [
  "Suivre les bulletins météorologiques et les avis d'inondation des autorités",
  'Éviter de circuler à pied ou en voiture dans les zones inondées',
  "Ne jamais tenter de traverser un cours d'eau en crue",
  'Éloigner les biens de valeur des zones basses du domicile',
  "Vérifier l'état des drains, soupapes de refoulement et pompes de puisard",
  "Préparer une trousse d'urgence de base (eau, médicaments, documents importants)",
  "Rester informé et prêt à évacuer rapidement si les autorités l'ordonnent",
  'Maintenir un contact régulier avec ses proches, notamment les personnes vulnérables',
];

export const SHARED_FLOOD_EXTREME_IMMEDIATE_ACTIONS_BASE = [
  "Évacuer immédiatement si les autorités l'ordonnent — ne pas attendre",
  "Suivre strictement les consignes des services d'urgence",
  'Ne jamais circuler en voiture ou à pied dans les zones inondées',
  "Couper l'électricité et le gaz si l'eau menace d'entrer dans le bâtiment",
  "Monter aux étages supérieurs si l'évacuation est impossible",
  "Emporter la trousse d'urgence (eau, nourriture, médicaments, documents, lampes)",
  'Prévoir une autonomie en eau potable et en nourriture pour plusieurs jours',
  "Charger tous les appareils électroniques à l'avance",
] as const;

export const SHARED_FLOOD_EXTREME_PROTECT_HOME_BASE = [
  'Déplacer les biens de valeur et documents importants aux étages supérieurs',
  'Installer des batardeaux ou sacs de sable aux entrées si possible',
  'Débrancher les appareils électriques dans les zones menacées',
] as const;

export const SHARED_FLOOD_EXTREME_COMPLEMENTARY_MEASURES_BASE = [
  'Communiquer sa position aux proches et aux autorités',
  "Porter assistance aux voisins ou personnes isolées si c'est sans danger",
  'Ne pas retourner dans un bâtiment inondé sans autorisation des autorités',
  'Documenter les dommages avec des photos pour les assurances',
  "Faire preuve de patience face aux délais d'intervention des services",
  'Respecter les périmètres de sécurité établis par les autorités',
] as const;

export const SHARED_FLOOD_EXTREME_AFTER_FLOOD_BASE = [
  "Ne réintégrer le bâtiment qu'avec l'accord des autorités",
  'Aérer et assécher le domicile dès que possible pour éviter les moisissures',
  'Faire inspecter les installations électriques avant de rétablir le courant',
  'Continuer de suivre les consignes des autorités',
] as const;
