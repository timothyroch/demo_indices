export interface PublicDecisionRecoSection {
  readonly title: string;
  readonly bullets: readonly string[];
}

export interface PublicDecisionRecommendationsContent {
  readonly none: PublicDecisionRecoSection;
  readonly normale: readonly PublicDecisionRecoSection[];
  readonly extreme: readonly PublicDecisionRecoSection[];
  readonly atRisk: PublicDecisionRecoSection;
}

export interface PublicDecisionRecommendationsByCity {
  readonly montreal: PublicDecisionRecommendationsContent;
  readonly laval: PublicDecisionRecommendationsContent;
}
