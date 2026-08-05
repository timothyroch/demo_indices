import pdfMake from 'pdfmake/build/pdfmake';
import pdfFonts from 'pdfmake/build/vfs_fonts';
import type { Content, TDocumentDefinitions, TVirtualFileSystem } from 'pdfmake/interfaces';
import type { DetailedJournalEvent, JournalStructuredReport } from './journal-report.service';

/** Polices embarquées (Roboto) — requis pour le français dans le PDF */
pdfMake.addVirtualFileSystem(pdfFonts as TVirtualFileSystem);

export interface JournalReportPdfLabels {
  sectionMetadata: string;
  sectionSubjectIdentity: string;
  sectionPeriod: string;
  sectionSummary: string;
  sectionUsageOverview: string;
  sectionHighRisk: string;
  sectionActivity: string;
  sectionDetailedEvents: string;
  sectionRecommendations: string;
  sectionModelData: string;
  emptyList: string;
  emptyEvents: string;
}

/** Contrôle l’affichage PDF uniquement ; l’analyse SIAG utilise toujours le journal complet. */
export interface JournalReportPdfVisibility {
  /** Synthèse d’usage, activité, journal détaillé. */
  showActionLogSections: boolean;
  /** Section données / requêtes modèles. */
  showModelDataSections: boolean;
}

export const DEFAULT_JOURNAL_REPORT_PDF_VISIBILITY: JournalReportPdfVisibility = {
  showActionLogSections: true,
  showModelDataSections: true,
};

function paragraph(text: string | null | undefined, marginBottom = 8): Content {
  return {
    text: text ?? '',
    margin: [0, 0, 0, marginBottom],
    alignment: 'left',
  };
}

function sectionTitle(title: string): Content {
  return {
    text: title,
    style: 'subheader',
    margin: [0, 12, 0, 6],
  };
}

function bulletBlock(items: string[] | null | undefined, emptyLabel: string): Content[] {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) {
    return [paragraph(emptyLabel, 10)];
  }
  return [
    {
      ul: list,
      margin: [0, 0, 0, 10],
    },
  ];
}

function detailedEventsTable(
  events: DetailedJournalEvent[] | null | undefined,
  emptyLabel: string,
): Content {
  const rows = Array.isArray(events) ? events : [];
  if (!rows.length) {
    return paragraph(emptyLabel, 10);
  }
  const head = ['Horodatage', "Type d'événement", 'Module', 'Détails', 'Statut'];
  const body: unknown[][] = [
    head.map((h) => ({ text: h, bold: true, fontSize: 8 })),
    ...rows.map((e) => [
      { text: e.timestamp, fontSize: 7 },
      { text: e.event_type, fontSize: 7 },
      { text: e.module_or_component, fontSize: 7 },
      { text: e.action_details, fontSize: 7 },
      { text: e.operation_status, fontSize: 7 },
    ]),
  ];
  return {
    table: {
      headerRows: 1,
      widths: [62, 52, 58, '*', 42],
      body: body as never,
    },
    margin: [0, 0, 0, 10],
    layout: 'lightHorizontalLines',
  };
}

export function buildJournalReportPdfDefinition(
  report: JournalStructuredReport,
  labels: JournalReportPdfLabels,
  visibility: JournalReportPdfVisibility = DEFAULT_JOURNAL_REPORT_PDF_VISIBILITY,
): TDocumentDefinitions {
  const content: Content[] = [
    { text: report.title ?? '', style: 'header' },
    sectionTitle(labels.sectionMetadata),
    paragraph(`Période couverte : ${report.metadata.period_covered}`, 4),
    paragraph(`Date et heure de génération (UTC) : ${report.metadata.generated_at}`, 4),
    paragraph(`Généré par : ${report.metadata.generated_by}`, 10),
    sectionTitle(labels.sectionSubjectIdentity),
    paragraph(report.subject_identity.identifier_line, 4),
    paragraph(`Rôle et permissions : ${report.subject_identity.role_and_permissions}`, 4),
    paragraph(`Statut du compte : ${report.subject_identity.account_status}`, 10),
    sectionTitle(labels.sectionHighRisk),
    ...bulletBlock(report.high_risk_events, labels.emptyList),
    sectionTitle(labels.sectionRecommendations),
    ...bulletBlock(report.recommendations, labels.emptyList),
    sectionTitle(labels.sectionSummary),
    paragraph(report.summary, 10),
    sectionTitle(labels.sectionPeriod),
    paragraph(report.period_description, 10),
  ];

  if (visibility.showActionLogSections) {
    content.push(
      sectionTitle(labels.sectionUsageOverview),
      ...bulletBlock(report.usage_overview_bullets, labels.emptyList),
      sectionTitle(labels.sectionActivity),
      ...bulletBlock(report.user_activity_notes, labels.emptyList),
      sectionTitle(labels.sectionDetailedEvents),
      detailedEventsTable(report.detailed_events, labels.emptyEvents),
    );
  }

  if (visibility.showModelDataSections) {
    content.push(
      sectionTitle(labels.sectionModelData),
      ...bulletBlock(report.optional_model_data_notes, labels.emptyList),
    );
  }

  return {
    pageSize: 'A4',
    pageMargins: [48, 48, 48, 56],
    content,
    styles: {
      header: {
        fontSize: 18,
        bold: true,
        color: '#0d2137',
        margin: [0, 0, 0, 16],
      },
      subheader: {
        fontSize: 12,
        bold: true,
        color: '#0d2137',
      },
    },
    defaultStyle: {
      font: 'Roboto',
      fontSize: 10,
      lineHeight: 1.35,
    },
  };
}

export async function downloadJournalReportPdf(
  report: JournalStructuredReport,
  labels: JournalReportPdfLabels,
  fileNameBase = 'rapport-analyse',
  visibility: JournalReportPdfVisibility = DEFAULT_JOURNAL_REPORT_PDF_VISIBILITY,
): Promise<void> {
  const def = buildJournalReportPdfDefinition(report, labels, visibility);
  const safe = fileNameBase.replace(/[^\w\-àâäéèêëïîôùûüç]+/gi, '_').slice(0, 80);
  const stamp = new Date().toISOString().slice(0, 10);
  await pdfMake.createPdf(def).download(`${safe}_${stamp}.pdf`);
}
