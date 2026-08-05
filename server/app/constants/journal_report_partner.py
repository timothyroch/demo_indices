PARTNER_REPORT_LLM_INSTRUCTIONS = "\n".join(
    [
        "## Demandes partenaires",
        "",
        "Personnalisation du rapport de reddition de compte.",
        "",
        "- Génération d'un rapport de prévision.",
        "- Données utilisées par les modèles et indicateurs techniques.",
        "",
        "Référence pour la structure type journal d'événements "
        "(exemples de fichiers de logs) :",
        "https://docs.aws.amazon.com/awscloudtrail/latest/userguide/"
        "cloudtrail-log-file-examples.html",
        "",
        "### 1. Métadonnées du rapport",
        "",
        "Cette section contextuelle permet de savoir exactement ce que l'on regarde.",
        "",
        "- **Période couverte :** (ex. du 2026-03-01 au 2026-03-23)",
        "- **Date et heure de génération du rapport**",
        (
            "- **Généré par :** (Système automatisé ou identifiant de "
            "l'administrateur ayant demandé le rapport)"
        ),
        "",
        "### 2. Identité et contexte de l'utilisateur",
        "",
        "Les informations de base sur la personne dont on audite les activités.",
        "",
        "- **Identifiant unique (UUID) et Nom/Courriel**",
        "- **Rôle et niveau de permission :** (ex. Administrateur, Éditeur, Lecteur)",
        "- **Statut du compte :** (Actif, Suspendu, Archivé)",
        "",
        "### 3. Synthèse de l'utilisation (Vue d'ensemble)",
        "",
        "Un résumé exécutif rapide des statistiques clés pour la période donnée.",
        "",
        "- **Nombre total de sessions (connexions)**",
        "- **Durée totale ou moyenne d'utilisation**",
        "- **Volume d'actions par catégorie :**",
        "    - Sélection des aires de diffusion x, y, z",
        "    - Simulations",
        "    - Configuration alertes pour x, y et z",
        "    - _Exportations/Téléchargements_ (ex. 5 rapports générés)",
        "",
        "### 4. Journal détaillé des événements (La reddition de compte technique)",
        "",
        (
            "C'est le cœur du rapport. Il se présente généralement sous forme "
            "d'un tableau chronologique détaillé. Pour chaque action, on doit "
            "retrouver :"
        ),
        "",
        (
            "- **Horodatage (Timestamp) :** Date et heure précises (idéalement "
            "en UTC ou avec le fuseau horaire spécifié)."
        ),
        (
            "- **Type d'événement :** Connexion, déconnexion, opération CRUD "
            "(Create, Read, Update, Delete)."
        ),
        (
            "- **Module ou Composant touché :** Quelle partie du logiciel a été "
            "utilisée (ex. _Paramètres du profil_)."
        ),
        (
            "- **Détails de l'action (Payload) :** Ce qui a changé concrètement "
            "(ex. « Valeur X modifiée de 10 à 15 »), ou toute donnée utile "
            "issue du journal (ex. adresse IP, user-agent) uniquement si elle "
            "apparaît dans l'entrée — sans phrase du type « IP non spécifiée »."
        ),
        (
            "- **Statut de l'opération :** Succès, Échec, ou Refusé (très "
            "important pour identifier les bugs ou les problèmes de droits)."
        ),
        "",
        (
            "#### C'est ici qu'on présentera l'ensemble des recommandations par "
            "territoire en se basant sur les indicateurs météo, sociaux, "
            "territoriaux."
        ),
        "",
        "### 5. Données utilisées par le modèle",
        "",
        (
            "Ensemble de données utilisé (Inondations pluviales → jeux de "
            "données perso). Sources des indicateurs techniques (sociaux, "
            "territoriaux). Canicules → quel modèle est utilisé, etc."
        ),
    ]
)
