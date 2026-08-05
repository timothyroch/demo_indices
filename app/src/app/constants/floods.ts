export const FLOOD_STRINGS = {
  PLUVIAL_SECTION_TITLE: 'Inondations pluviales',
  FLUVIAL_SECTION_TITLE: 'Crues fluviales',
  ERROR_MESSAGE: 'Prévision indisponible',
  PLUVIAL_FORECAST_SUBTITLE: "Probabilité d'inondation pluviale prévue selon les données météo",
  FLUVIAL_FORECAST_SUBTITLE:
    "Probabilité de crues prévue selon les niveaux d'eau et les données météo",
  DATE_HEADER: 'Date',
  TEMP_HEADER: 'Température moyenne (°C)',
  PREC_HEADER: 'Précipitation (mm)',
  WATER_LEVEL_HEADER: "Niveau de l'eau",
  FLUVIAL_PROB_HEADER: 'Probabilité de crue',
  PLUVIAL_PROB_HEADER: 'Probabilité inondation',
  INFOBUBBLE_PLUVIAL_PROBABILITY:
    'Cette probabilité est une estimation produite par un modèle XGBoost préentraîné sur des données météorologiques historiques (2015 à 2026) et des cas d’inondation pluviale observés. Les variables retenues ont été sélectionnées selon leur pertinence statistique. La valeur affichée est ensuite ajustée à l’aide de l’indice de vulnérabilité de la zone afin de mieux représenter le risque local.',
  INFOBUBBLE_FLUVIAL_PROBABILITY:
    'Cette probabilité est une estimation basée sur les niveaux d’eau observés et les conditions météorologiques historiques (2015 à 2026). Chaque variable (niveau d’eau, pluie sur 3 jours, température moyenne et variations de température) est pondérée selon son influence statistique sur les crues fluviales, puis combinée pour produire un score. Ce score est ensuite transformé en probabilité via une fonction sigmoïde afin de refléter le risque de crue dans la zone sélectionnée. La valeur affichée est ensuite ajustée à l’aide de l’indice de vulnérabilité de la zone afin de mieux représenter le risque local.',

  // Info-bulles : TEXTES QUALITATIFS
  ZONE_IS_FLOODABLE: 'Cette zone est située dans un secteur inondable ou à risque de crues.\n\n',
  ZONE_NOT_FLOODABLE: "ℹ️ Cette zone n'est pas située dans un secteur inondable répertorié.\n\n",
  SOCIAL_CONTEXT_INTRO: 'Contexte social et vulnérabilité :',
  PHYSICAL_INDICATORS_INTRO: 'Indicateurs physiques/géographiques :',
  INFOBUBBLE_RISK_PLUV_MTL:
    'Le score de risque est calculé à partir des données sur les cuvettes de rétention d’eau, le niveau de minéralisation des sols et les caractéristiques sociales propres à la ville de Montréal.',
  INFOBUBBLE_RISK_SOCIAL:
    'Le score de risque est calculé à partir des données sur les caractéristiques sociales de la ville.',
  INFOBUBBLE_RISK_FLUV_MTL:
    'Le score de risque est calculé à partir des données sur les zones inondables et les caractéristiques sociales de la ville de Montréal.',

  // Fonctions de formatage pour les info-bulles
  SOCIAL_COMP_AGE: (age65: string, compAge: string, cityLabel: string, avgAge: number) =>
    `\n• La proportion des 65 ans et plus (${age65}%) est ${compAge} à la moyenne ${cityLabel} (${avgAge}%).`,
  SOCIAL_COMP_INCOME: (income: number, compIncome: string, avgIncome: number) =>
    `\n• Le revenu médian des ménages (${income}$) est ${compIncome} à la moyenne (${avgIncome}$).`,
  SOCIAL_COMP_REPAIRS: (majorRepairs: string, compRepairs: string, avgRepairs: number) =>
    `\n• La part de logements nécessitant des réparations majeures (${majorRepairs}%) y est ${compRepairs} à la moyenne (${avgRepairs}%).`,

  // Synthèses de vulnérabilité
  SOCIAL_SYNTHESIS_HIGH_VULN:
    "\n\n👉 Cette zone présente une vulnérabilité sociale prononcée (population plus âgée et revenus plus faibles), ce qui peut complexifier l'évacuation et la résilience post-crue.",
  SOCIAL_SYNTHESIS_MED_VULN:
    '\n\n👉 La zone présente certains facteurs de vulnérabilité qui invitent à une vigilance particulière en cas de sinistre.',
  SOCIAL_SYNTHESIS_LOW_VULN:
    "\n\n👉 Économiquement et démographiquement, la zone semble disposer d'une meilleure capacité de résilience globale comparativement à la moyenne régionale.",
} as const;
