AUTH_ERROR_USER_NOT_FOUND = "Utilisateur introuvable."
AUTH_ERROR_NOT_AUTHENTICATED = "Non authentifié."
AUTH_ERROR_INVALID_OR_EXPIRED_TOKEN = "Jeton invalide ou expiré."
AUTH_ERROR_INVALID_TOKEN = "Jeton invalide."
AUTH_ERROR_ADMIN_REQUIRED = "Accès administrateur requis."
AUTH_ERROR_PARTNER_CITY_ADMIN_USER = (
    "La ville partenaire ne s'applique pas aux comptes administrateur."
)
AUTH_ERROR_PARTNER_CITY_UPDATE = "Impossible de mettre à jour la ville partenaire."
AUTH_ERROR_INVALID_CREDENTIALS = "Nom d'utilisateur ou mot de passe invalide."
AUTH_ERROR_USERNAME_EXISTS = "Ce nom d'utilisateur existe déjà."
AUTH_ERROR_CREATE_USER_SERVER = (
    "Erreur serveur lors de la création du compte. Réessayez."
)
AUTH_ERROR_CHANGE_PASSWORD = "Erreur lors du changement de mot de passe."
AUTH_ERROR_UPDATE_CONTACT = "Erreur lors de la mise à jour du courriel ou du téléphone."

AUTH_ERROR_PARTNER_CITY_NOT_ASSIGNED = (
    "Aucune ville partenaire valide n'est assignée à ce compte."
)
AUTH_ERROR_OUTSIDE_PARTNER_ZONE = (
    "Coordonnées ou zone hors de la ville autorisée pour ce compte."
)

ALERT_ERROR_NO_PHONE = "Aucun numéro de téléphone enregistré pour les alertes."
ALERT_ERROR_SMS_UNAVAILABLE = "Envoi SMS indisponible (Twilio non configuré ou erreur)."

ALERT_ERROR_NO_EMAIL = "Aucune adresse courriel enregistrée pour les alertes."
ALERT_ERROR_EMAIL_UNAVAILABLE = (
    "Envoi email indisponible (SendGrid non configuré ou erreur)."
)

REPORT_ERROR_BACKEND = (
    "Génération de rapport indisponible : vérifiez JOURNAL_REPORT_BACKEND "
    "et GEMINI_API_KEY."
)
