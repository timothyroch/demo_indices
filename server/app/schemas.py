import re
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.constants.partner_city import PARTNER_CITY_LAVAL, PARTNER_CITY_MONTREAL


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_PHONE_MIN_DIGITS = 10


def _validate_email(v: str) -> str:
    s = v.strip()
    if " " in s or not _EMAIL_RE.match(s):
        raise ValueError("Adresse courriel invalide")
    return s.lower()


def _validate_phone(v: str) -> str:
    digits = "".join(c for c in v if c.isdigit())
    if len(digits) < _PHONE_MIN_DIGITS:
        raise ValueError(
            f"Le numéro doit contenir au moins {_PHONE_MIN_DIGITS} chiffres "
            "(ex. 5145551234 ou +1 514 555-1234)"
        )
    if len(digits) > 15:
        raise ValueError("Numéro de téléphone trop long")
    return v.strip()


EmailStr = Annotated[str, BeforeValidator(_validate_email)]
PhoneStr = Annotated[str, BeforeValidator(_validate_phone)]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8)
    email: EmailStr = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Adresse courriel pour les alertes",
    )
    phone: PhoneStr = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Numéro de téléphone pour les alertes",
    )
    partner_city: Literal[PARTNER_CITY_MONTREAL, PARTNER_CITY_LAVAL]


class UserPasswordUpdate(BaseModel):
    password: str = Field(..., min_length=8)


class UserContactUpdate(BaseModel):
    email: EmailStr = Field(..., min_length=1, max_length=255)
    phone: PhoneStr = Field(..., min_length=1, max_length=64)


class UserPartnerCityUpdate(BaseModel):
    partner_city: Literal[PARTNER_CITY_MONTREAL, PARTNER_CITY_LAVAL]


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    email: str | None = None
    phone: str | None = None
    partner_city: str | None = None

    class Config:
        from_attributes = True


class AlertSettingsResponse(BaseModel):
    """Paramètres d'alertes de l'utilisateur courant."""

    alert_pluvial_enabled: bool = False
    alert_fluvial_enabled: bool = False
    alert_heatwave_enabled: bool = False
    alert_snow_enabled: bool = False
    alert_threshold_pluvial_pct: float | None = None
    alert_threshold_fluvial_pct: float | None = None
    alert_threshold_heatwave_humidex: float | None = None
    alert_threshold_snow_pct: float | None = None
    alert_via_sms: bool = True
    alert_via_email: bool = False
    alert_frequency_hours: int | None = None


class AlertSettingsUpdate(BaseModel):
    """Mise à jour partielle des paramètres d'alertes."""

    alert_pluvial_enabled: bool | None = None
    alert_fluvial_enabled: bool | None = None
    alert_heatwave_enabled: bool | None = None
    alert_snow_enabled: bool | None = None
    alert_threshold_pluvial_pct: float | None = Field(None, ge=0, le=100)
    alert_threshold_fluvial_pct: float | None = Field(None, ge=0, le=100)
    alert_threshold_heatwave_humidex: float | None = Field(None, ge=25, le=55)
    alert_threshold_snow_pct: float | None = Field(None, ge=0, le=100)
    alert_via_sms: bool | None = None
    alert_via_email: bool | None = None
    alert_frequency_hours: int | None = Field(None, ge=4, le=24)


class UserActionJournalCreate(BaseModel):
    action: str = Field(..., min_length=1, max_length=64)
    label: str | None = Field(None, max_length=200)
    route: str | None = Field(None, max_length=200)


class UserActionJournalResponse(BaseModel):
    id: int
    timestamp: str
    log_date: str
    user_id: int
    username: str
    action: str
    label: str | None = None
    route: str | None = None
    payload_json: str | None = None

    class Config:
        from_attributes = True


class JournalReportGenerateRequest(BaseModel):
    """Paramètres pour agréger les logs avant envoi au modèle (Outlines + SIAG)."""

    log_date_from: str | None = Field(
        None,
        description="Début inclus (YYYY-MM-DD), filtre sur log_date",
    )
    log_date_to: str | None = Field(
        None,
        description="Fin inclusive (YYYY-MM-DD)",
    )
    max_entries: int = Field(400, ge=10, le=2000)


class JournalReportMetadata(BaseModel):
    period_covered: str = Field(
        ...,
        description="Libellé période (ex. du AAAA-MM-JJ au AAAA-MM-JJ)",
        max_length=400,
    )
    generated_at: str = Field(
        ...,
        description="Horodatage ISO 8601 de génération du rapport",
        max_length=80,
    )
    generated_by: str = Field(
        ...,
        description="Système automatisé ou libellé du demandeur",
        max_length=200,
    )


class JournalReportUserIdentity(BaseModel):
    """Section 2 — identité auditée (ou mention agrégat multi-utilisateurs)."""

    identifier_line: str = Field(
        ...,
        max_length=500,
        description="ID / nom / courriel ou texte pour rapport agrégé admin",
    )
    role_and_permissions: str = Field(..., max_length=200)
    account_status: str = Field(..., max_length=120)


class DetailedJournalEvent(BaseModel):
    timestamp: str = Field(..., max_length=120)
    event_type: str = Field(..., max_length=200)
    module_or_component: str = Field(..., max_length=200)
    action_details: str = Field(..., max_length=2000)
    operation_status: str = Field(..., max_length=80)


class JournalStructuredReportContent(BaseModel):
    """Sortie produite par le modèle (sans métadonnées serveur ni cadre partenaires)."""

    title: str = Field(..., max_length=200)
    summary: str = Field(..., max_length=12000)
    period_description: str = Field(
        ...,
        description="Période couverte et nombre d'entrées analysées",
        max_length=2000,
    )
    high_risk_events: list[str] = Field(
        default_factory=list,
        description="Faits saillants liés aux risques (modèles, actions carte)",
    )
    user_activity_notes: list[str] = Field(
        default_factory=list,
        description="Observations sur l'activité utilisateurs (actions UI)",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description=(
            "Recommandations par territoire (indicateurs météo, sociaux, territoriaux)"
        ),
    )
    usage_overview_bullets: list[str] = Field(
        default_factory=list,
        description="Synthèse section 3 : sessions, durées, volumes par catégorie",
    )
    detailed_events: list[DetailedJournalEvent] = Field(
        default_factory=list,
        description="Tableau chronologique section 4 à partir des entrées JSON",
    )
    optional_model_data_notes: list[str] = Field(
        default_factory=list,
        description="Données et sources liées aux modèles (section 5 du rapport)",
    )


class JournalStructuredReport(BaseModel):
    metadata: JournalReportMetadata
    subject_identity: JournalReportUserIdentity

    title: str = Field(..., max_length=200)
    summary: str = Field(..., max_length=12000)
    period_description: str = Field(
        ...,
        description="Période couverte et nombre d'entrées analysées",
        max_length=2000,
    )
    high_risk_events: list[str] = Field(
        default_factory=list,
        description="Faits saillants liés aux risques (modèles, actions carte)",
    )
    user_activity_notes: list[str] = Field(
        default_factory=list,
        description="Observations sur l'activité utilisateurs (actions UI)",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description=(
            "Recommandations par territoire (indicateurs météo, sociaux, territoriaux)"
        ),
    )
    usage_overview_bullets: list[str] = Field(
        default_factory=list,
        description="Synthèse section 3",
    )
    detailed_events: list[DetailedJournalEvent] = Field(
        default_factory=list,
        description="Journal détaillé section 4",
    )
    optional_model_data_notes: list[str] = Field(
        default_factory=list,
        description="Données et sources liées aux modèles (section 5 du rapport)",
    )
