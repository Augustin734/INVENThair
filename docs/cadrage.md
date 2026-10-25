# INVENThair – Cadrage projet

Version du 25 octobre 2026, révision 2 (arbitrages après relecture des maquettes, voir § 6). Source : doc « INVENThair – Cadrage projet ».

## 1. Cahier des charges

INVENThair est une appli web locale qui suit le stock de matière première de l'onglerie de Maud, gère les inventaires et produit une liste d'achat. À terme, elle alimentera un site de vente d'ongles pour couper automatiquement les produits en rupture.

### Objectifs V1

1. Savoir à tout moment ce qu'il reste en stock, produit par produit.
2. Faire un inventaire (comptage réel) et l'enregistrer en base en une fois.
3. Archiver un produit qu'on n'utilise plus sans perdre son historique.
4. Être alertée quand un produit passe sous son seuil.
5. Générer une liste d'achat téléchargeable (CSV/PDF) ou envoyée par mail.

### Périmètre

| Dans la V1 | Hors V1 (plus tard) |
| --- | --- |
| CRUD produits, catégories, fournisseurs | Site de vente d'ongles |
| Mouvements de stock (entrée, sortie, ajustement) | Table « recettes » (ongle = liste de matières) |
| Inventaires avec validation | Rupture auto côté boutique |
| Archivage / désarchivage produit | Multi-utilisateurs, rôles |
| Alertes de seuil dans l'UI | Appli mobile, hébergement en ligne |
| Liste d'achat CSV / PDF / mail | Scan code-barres, commande fournisseur auto |

### Stack imposée

- **Back** : Python 3.11+, FastAPI, SQLModel, SQLite (un fichier `inventhair.db`).
- **Front** : HTML + JS vanilla servi par FastAPI (`app/templates/` via Jinja2, `app/static/`). Pas de framework JS, pas de build.
- **PDF** : ReportLab (pur Python, s'installe hors ligne sans bibliothèque système). **Mail** : SMTP (`smtplib`), identifiants dans `.env` lu avec `python-dotenv`.
- **Lancement développeur** : `./start.sh` → venv, initialisation de la base, serveur au premier plan sur `http://localhost:8000` (avec rechargement auto).
- **Lancement Maud (appli de bureau)** : voir « Installation sur le PC de Maud » plus bas. Pas de Docker (pas utile pour une appli locale à une seule utilisatrice).
- **Base** : pas d'outil de migration en V1. Au démarrage, `SQLModel.metadata.create_all()` crée les tables manquantes, puis les catégories de départ sont insérées si la table est vide (idempotent).
- **Tests** : pytest + `httpx` (TestClient FastAPI) sur l'API.

**Dépendances autorisées** : `fastapi`, `uvicorn`, `sqlmodel`, `jinja2`, `reportlab`, `python-dotenv`, `pytest`, `httpx`. Toute autre dépendance se demande d'abord.

### Contraintes

- Tourne hors ligne sur un PC Linux, une seule utilisatrice, pas d'authentification en V1 (écoute sur 127.0.0.1 uniquement).
- Interface en français, utilisable sans formation, lisible sur écran portable.
- Le stock n'est jamais modifié « à la main » : toute variation passe par un mouvement tracé.
- Sauvegarde : une commande copie le fichier `.db` dans `backups/` avec la date.
- L'API est le seul point d'accès aux données : le futur site de vente l'utilisera aussi.
- Appli lançable d'un double-clic depuis le Bureau et le menu des applications, sans terminal.
- Hors ligne : les polices (Lilita One, Nunito, licence OFL) sont servies depuis `app/static/fonts/`, pas depuis Google Fonts.

### Installation sur le PC de Maud

- `./install.sh` (une seule fois, ou après une mise à jour) : crée le venv, installe les dépendances, initialise la base, puis installe le raccourci `inventhair.desktop` (icône `app/static/icone.png`) dans `~/.local/share/applications/` et sur le Bureau (`xdg-user-dir DESKTOP`, marqué comme fiable avec `gio set … metadata::trusted true`).
- Le raccourci lance `./lancer.sh` : si `GET /health` ne répond pas, il démarre le serveur en arrière-plan (journaux dans `logs/inventhair.log`, fichier PID dans `logs/`), attend que `/health` réponde (10 s maximum, sinon message d'erreur via `notify-send`), puis ouvre l'appli dans une fenêtre dédiée (`chromium --app=…` ou `google-chrome --app=…` s'ils existent, sinon le navigateur par défaut via `xdg-open`). Un second double-clic rouvre simplement la fenêtre.
- Le serveur tourne jusqu'à la fermeture de session ; `./stop.sh` l'arrête. Il écoute uniquement sur 127.0.0.1.
- `./desinstaller.sh` retire les raccourcis (la base et les sauvegardes restent).

## 2. Modèle de données

Six tables en V1 ; le stock d'un produit = somme de ses mouvements, mise en cache dans `produit.stock_actuel`.

| Table | Champs | Notes |
| --- | --- | --- |
| `categorie` | id, nom (unique), couleur_r, couleur_g, couleur_b (0–255), couleur_a (0,2–1), ordre (int), cree_le | Gérée par Maud dans l'appli (ajout, renommage, couleur, ordre, fusion). Relation 1-n : une catégorie a plusieurs produits, un produit a une seule catégorie (`produit.categorie_id`, obligatoire). Au démarrage : Gels `#B01050`, Vernis `#2D5128`, Capsules `#79365C`, Consommables `#430D2B` (opacité 1, ordre 1 à 4). |
| `fournisseur` | id, nom (unique), email?, site_url?, notes?, cree_le | Optionnel sur un produit |
| `produit` | id, nom, reference?, categorie_id, fournisseur_id?, unite (`piece`, `ml`, `g`, `flacon`), stock_actuel (décimal), seuil_alerte, qte_reappro, prix_unitaire?, archive (bool, défaut false), archive_motif?, archive_le?, cree_le, maj_le | `qte_reappro` = quantité proposée dans la liste d'achat |
| `mouvement` | id, produit_id, type (`entree`, `sortie`, `ajustement`), quantite (signée), motif?, inventaire_id?, cree_le | Jamais modifié ni supprimé |
| `inventaire` | id, statut (`brouillon`, `valide`, `annule`), commentaire?, cree_le, valide_le? | Un seul brouillon à la fois |
| `ligne_inventaire` | id, inventaire_id, produit_id, qte_theorique, qte_comptee?, compte_le?, ecart (calculé) | Une ligne par produit actif à l'ouverture |

**Règles métier**

- `stock_actuel` est recalculé à chaque mouvement, dans la même transaction.
- Une sortie qui rendrait le stock négatif est refusée (erreur 409 `STOCK_INSUFFISANT`).
- Un produit archivé ne reçoit plus de mouvement (409 `PRODUIT_ARCHIVE`) : il faut le désarchiver d'abord.
- Un produit archivé n'apparaît plus dans les listes, alertes, inventaires ni la liste d'achat ; son historique reste.
- Les listes de produits sont triées par nom (insensible à la casse et aux accents).
- Alerte = produit non archivé avec `stock_actuel <= seuil_alerte`.
- **Statut** (calculé, renvoyé par l'API, jamais stocké) : `alerte` si `stock_actuel <= seuil_alerte` ; `a_surveiller` si `stock_actuel <= 1,5 × seuil_alerte` ; `en_forme` sinon. Affichage : « Alerte ! », « À surveiller », « En forme ».

**Inventaires**

- À l'ouverture, une ligne est créée par produit actif avec `qte_theorique = stock_actuel`.
- Quand Maud saisit `qte_comptee`, `qte_theorique` est remis au `stock_actuel` du moment et `compte_le` est renseigné. Le théorique correspond ainsi au stock au moment du comptage, même si des mouvements ont eu lieu depuis l'ouverture. `ecart = qte_comptee − qte_theorique`.
- Valider crée un mouvement `ajustement` de valeur `ecart` par ligne dont l'écart ≠ 0, puis passe l'inventaire en `valide`. Les mouvements faits après le comptage d'une ligne sont donc conservés. Si un ajustement rendait un stock négatif, la validation est refusée (409 `STOCK_INSUFFISANT`, lignes concernées dans `details`) et rien n'est écrit.
- Lignes non comptées : refus (409 `LIGNES_NON_COMPTEES`), sauf avec `garder_theorique_si_vide`, auquel cas elles ne créent aucun mouvement.
- Un inventaire validé ou annulé est en lecture seule (409 `INVENTAIRE_VERROUILLE`).
- Archiver un produit pendant un brouillon supprime sa ligne du brouillon. Un produit créé ou désarchivé pendant un brouillon n'y est pas ajouté.

**Catégories** : le nom est unique (insensible à la casse), doublon refusé en 409 `NOM_DEJA_UTILISE`. Une catégorie qui contient des produits ne peut pas être supprimée telle quelle : on choisit une catégorie de destination, les produits y sont déplacés, puis elle est supprimée (fusion). Les produits archivés comptent aussi. Une nouvelle catégorie prend l'ordre maximal + 1.

**Fournisseurs** : nom unique (insensible à la casse, 409 `NOM_DEJA_UTILISE`). Suppression refusée (409 `RESSOURCE_UTILISEE`) si un produit, même archivé, y est rattaché.

**Prévu pour la V2 (ne pas coder maintenant)** : `article_vente` (un modèle d'ongles vendu) et `recette_ligne` (article_vente_id, produit_id, quantite_par_unite). Disponibilité d'un article = min(stock_actuel / quantite_par_unite) sur ses lignes.

## 3. User stories

Une seule persona : Maud, gérante de l'onglerie. Chaque story est « finie » quand ses critères passent en test.

| ID | En tant que Maud, je veux… | Critères d'acceptation |
| --- | --- | --- |
| US1 | ajouter un produit (nom, catégorie, unité, seuil, qté de réappro) | Fenêtre « Nouveau produit » ; champs obligatoires vérifiés ; catégorie choisie dans une liste déroulante (avec « + nouvelle catégorie » qui crée la catégorie sans quitter la fenêtre) ; fournisseur facultatif (avec « + nouveau fournisseur ») ; stock initial saisi = mouvement `entree` ; apparaît dans la liste |
| US2 | voir la liste de mes produits avec leur stock | Tri par nom, filtre par catégorie (pastilles aux couleurs des catégories) et recherche texte ; filtre « En alerte seulement » ; pastille de statut ; produits en alerte surlignés |
| US3 | modifier un produit | Même fenêtre que US1 ; le stock est affiché mais pas modifiable (lien vers Réception / sortie) ; la catégorie peut changer |
| US4 | archiver un produit que je n'aime pas, avec un motif | Disparaît des listes, alertes, inventaires ; visible dans l'onglet « Archivés » de la page Produits avec motif et date ; désarchivable |
| US5 | enregistrer une réception de commande | Fenêtre « Réception / sortie » ; mouvement `entree`, stock à jour immédiatement ; aperçu « avant → après » |
| US6 | enregistrer une sortie ou une perte | Même fenêtre ; mouvement `sortie` avec motif (raccourcis : Utilisation, Perte, Casse) ; refus si stock insuffisant, message clair |
| US7 | voir l'historique d'un produit | Fiche produit : infos, stock, statut, mouvements du plus récent au plus ancien ; les 5 derniers mouvements tous produits confondus sur l'accueil (« Les derniers potins du stock ») |
| US8 | lancer un inventaire | Crée un brouillon avec tous les produits actifs et leur qté théorique ; refus si un brouillon existe déjà ; sans brouillon, la page Inventaire montre le bouton « Lancer » et l'historique des inventaires |
| US9 | saisir mes comptages au fil de l'eau | Sauvegarde ligne par ligne ; je peux quitter et reprendre ; écart affiché en direct ; progression « x / n comptés » |
| US10 | valider l'inventaire | Récap des écarts avant confirmation ; ajustements créés ; inventaire verrouillé. Lignes non comptées = refus, sauf si je coche « garder la qté théorique » |
| US11 | voir les produits en alerte dès l'accueil | Bandeau avec le nombre et la liste (chaque produit mène à sa fiche), lien vers la liste d'achat |
| US12 | générer la liste d'achat | Produits en alerte, groupés par fournisseur (« Sans fournisseur » en dernier), qté = `qte_reappro` modifiable avant export ; je peux retirer une ligne ou ajouter un produit hors alerte (côté écran, la liste retouchée est envoyée à l'export) |
| US13 | télécharger la liste en CSV ou PDF | Fichier nommé `liste-achat-AAAA-MM-JJ` |
| US14 | envoyer la liste par mail | Adresse destinataire saisie (pré-remplie depuis `.env` via `GET /parametres`) ; PDF en pièce jointe ; message de succès ou d'erreur clair |
| US15 | sauvegarder ma base | Bouton ou `./backup.sh` → copie datée dans `backups/` ; message avec le nom du fichier |
| US16 | gérer mes catégories depuis une fenêtre « Mes catégories » (bouton sur la page Produits) | Ajouter, renommer, changer l'ordre (enregistré en une fois via `POST /categories/reordonner`) ; couleur via un sélecteur façon Office (onglet Palette : 10 couleurs du thème, chacune avec 5 nuances en plus de la couleur de base, soit 60 cases ; 10 couleurs standard ; 8 couleurs récentes gardées dans le navigateur (`localStorage`) ; onglet Personnalisée : curseurs R, V, B, opacité A de 20 à 100 %, saisie hexa, code rgba affiché) ; texte des pastilles en blanc ou encre selon la luminosité de la couleur ; nombre de produits affiché par catégorie ; nom en double refusé ; supprimer une catégorie vide directement, une catégorie non vide seulement en choisissant où déplacer ses produits ; les filtres et listes déroulantes se mettent à jour sans recharger |
| US16b | gérer mes fournisseurs depuis une fenêtre « Mes fournisseurs » (bouton sur la page Produits) | Ajouter, modifier (nom, mail, site, notes), supprimer ; nombre de produits par fournisseur ; suppression refusée avec message si des produits y sont rattachés ; nom en double refusé |

**V2 (pour mémoire)** : US17 définir la recette d'un modèle d'ongles ; US18 le site de vente lit la disponibilité et masque l'article en rupture ; US19 une vente déclenche les sorties de stock correspondantes.

## 4. Contrat d'interface (API REST)

Base `http://localhost:8000/api/v1`, JSON en UTF-8, dates ISO 8601, champs en snake_case. FastAPI génère la doc sur `/docs` : elle doit toujours correspondre à ce tableau.

### Endpoints

| Méthode | Route | Rôle | Réponse |
| --- | --- | --- | --- |
| GET | `/categories` | Lister par `ordre` (avec `nb_produits`) | 200 `[Categorie]` |
| POST | `/categories` | Créer | 201 `Categorie`, 409 `NOM_DEJA_UTILISE` |
| POST | `/categories/reordonner` | Body `{ids: [3, 1, 2, 4]}` : réécrit `ordre` de toutes les catégories en une transaction (la liste doit contenir toutes les catégories) | 200 `[Categorie]`, 422 |
| PATCH / DELETE | `/categories/{id}` | Modifier (nom, couleur, ordre) / supprimer. Non vide : 409 `RESSOURCE_UTILISEE`, sauf avec `?fusionner_vers={id}` qui déplace les produits puis supprime | 200 / 204, 409 |
| GET | `/fournisseurs` | Lister par nom (avec `nb_produits`) | 200 `[Fournisseur]` |
| POST | `/fournisseurs` | Créer | 201, 409 `NOM_DEJA_UTILISE` |
| PATCH / DELETE | `/fournisseurs/{id}` | Modifier / supprimer (refus si utilisé) | 200 / 204, 409 |
| GET | `/produits?categorie_id=&q=&archive=false&en_alerte=` | Lister avec filtres, tri par nom | 200 `[Produit]` |
| POST | `/produits` | Créer (+ `stock_initial` optionnel) | 201 `Produit` |
| GET | `/produits/{id}` | Détail | 200, 404 |
| PATCH | `/produits/{id}` | Modifier (sans `stock_actuel`) | 200, 422 |
| POST | `/produits/{id}/archiver` | Archiver, body `{motif?}` | 200 |
| POST | `/produits/{id}/desarchiver` | Désarchiver | 200 |
| GET | `/produits/{id}/mouvements` | Historique, du plus récent au plus ancien | 200 `[Mouvement]` |
| GET | `/mouvements?limite=5` | Derniers mouvements tous produits (`limite` 1–100, défaut 5) | 200 `[Mouvement]` |
| POST | `/mouvements` | Entrée / sortie, body `{produit_id, type, quantite, motif?}` (`type` ∈ `entree`, `sortie`) | 201, 409 `STOCK_INSUFFISANT` ou `PRODUIT_ARCHIVE` |
| GET | `/inventaires` | Lister, du plus récent au plus ancien | 200 `[Inventaire]` |
| POST | `/inventaires` | Ouvrir un brouillon | 201 `InventaireDetail`, 409 si brouillon existant |
| GET | `/inventaires/{id}` | Détail avec lignes | 200 `InventaireDetail` |
| PATCH | `/inventaires/{id}/lignes/{ligne_id}` | Saisir `{qte_comptee}` (`null` efface le comptage) | 200 `LigneInventaire`, 409 si verrouillé |
| POST | `/inventaires/{id}/valider` | Body `{garder_theorique_si_vide: bool}` | 200, 409 si déjà validé, lignes vides ou stock négatif |
| POST | `/inventaires/{id}/annuler` | Annuler un brouillon | 200 |
| GET | `/alertes` | Produits sous seuil | 200 `[Produit]` |
| GET | `/liste-achat` | Liste groupée par fournisseur | 200 `ListeAchat` |
| POST | `/liste-achat/export?format=csv\|pdf` | Body `ListeAchat` éventuellement retouchée | 200 fichier |
| POST | `/liste-achat/envoyer` | Body `{destinataire, liste: ListeAchat}` | 202, 502 si SMTP KO |
| GET | `/parametres` | Réglages utiles au front : `{mail_destinataire_defaut}` (lu dans `.env`, jamais les identifiants SMTP) | 200 |
| POST | `/backup` | Copie datée de la base | 201 `{fichier}` |
| GET | `/health` | Ping | 200 `{status: "ok"}` |

**Réservé V2** : `GET /disponibilites` (articles de vente et quantité fabricable) et `POST /ventes` (décrémente les matières). Ne pas implémenter, mais ne pas réutiliser ces routes.

### Objets principaux

```json
{
  "Categorie": {
    "id": 2, "nom": "Gels", "couleur": { "r": 176, "g": 16, "b": 80, "a": 1.0 },
    "ordre": 1, "nb_produits": 9, "cree_le": "2026-10-24T10:00:00"
  },
  "Fournisseur": {
    "id": 1, "nom": "Grossiste A", "email": "commandes@grossiste-a.fr", "site_url": null,
    "notes": "Livraison en 48 h", "nb_produits": 17, "cree_le": "…"
  },
  "Produit": {
    "id": 12, "nom": "Gel builder clair", "reference": "GB-50",
    "categorie_id": 2, "fournisseur_id": 1, "unite": "ml",
    "stock_actuel": 35.0, "seuil_alerte": 50.0, "qte_reappro": 100.0,
    "prix_unitaire": 0.24, "archive": false, "archive_motif": null, "archive_le": null,
    "en_alerte": true, "statut": "alerte", "cree_le": "2026-10-24T10:00:00", "maj_le": "2026-10-24T10:00:00"
  },
  "Mouvement": {
    "id": 88, "produit_id": 12, "produit_nom": "Gel builder clair", "unite": "ml",
    "type": "sortie", "quantite": -15.0, "motif": "perte", "inventaire_id": null, "cree_le": "…"
  },
  "Inventaire": {
    "id": 6, "statut": "valide", "commentaire": null, "cree_le": "…", "valide_le": "…",
    "nb_lignes": 38, "nb_comptees": 38, "nb_ecarts": 7
  },
  "InventaireDetail": {
    "id": 3, "statut": "brouillon", "commentaire": null, "cree_le": "…", "valide_le": null,
    "nb_lignes": 38, "nb_comptees": 12, "nb_ecarts": 3,
    "lignes": [{ "id": 40, "produit_id": 12, "produit_nom": "Gel builder clair", "unite": "ml", "qte_theorique": 35.0, "qte_comptee": 30.0, "ecart": -5.0, "compte_le": "…" }]
  },
  "ListeAchat": {
    "genere_le": "…",
    "fournisseurs": [{ "fournisseur_id": 1, "nom": "Grossiste A", "lignes": [{ "produit_id": 12, "nom": "Gel builder clair", "unite": "ml", "stock_actuel": 35.0, "seuil_alerte": 50.0, "quantite": 100.0 }] }]
  }
}
```

- `quantite` dans `POST /mouvements` est toujours positive : le serveur applique le signe selon `type`.
- `Produit` ne contient ni le nom de la catégorie ni celui du fournisseur : le front les joint depuis `/categories` et `/fournisseurs`, déjà chargés pour les filtres.
- Dans `ListeAchat`, les produits sans fournisseur forment un groupe `{"fournisseur_id": null, "nom": "Sans fournisseur"}`, placé en dernier.

### Erreurs

Toujours le même format : `{"erreur": {"code": "STOCK_INSUFFISANT", "message": "Texte lisible en français", "details": {}}}`.

| HTTP | Codes |
| --- | --- |
| 404 | `INTROUVABLE` |
| 409 | `STOCK_INSUFFISANT`, `INVENTAIRE_EN_COURS`, `INVENTAIRE_VERROUILLE`, `LIGNES_NON_COMPTEES`, `RESSOURCE_UTILISEE`, `NOM_DEJA_UTILISE`, `PRODUIT_ARCHIVE` |
| 422 | `VALIDATION` (détails par champ) |
| 502 | `ENVOI_MAIL_ECHOUE` |

## 5. Étapes

1. Squelette : FastAPI, SQLite, modèles, initialisation de la base + catégories de départ, `start.sh`, `/health`, lancement de bureau (`install.sh`, `lancer.sh`, `stop.sh`, `desinstaller.sh`, `inventhair.desktop`).
2. CRUD catégories (avec fusion et réordonnancement), fournisseurs, produits + archivage (US1–US4, US16, US16b, côté API).
3. Mouvements et historique, dont `GET /mouvements` (US5–US7).
4. Inventaires (US8–US10).
5. Alertes et liste d'achat, exports CSV/PDF (US11–US13).
6. Envoi mail, `/parametres` et sauvegarde (US14–US15).
7. Front d'après `docs/maquettes/` : Accueil ; Produits (onglets Actifs / Archivés, fenêtres Nouveau / Modifier produit, Réception / sortie, Archiver, Mes catégories, Mes fournisseurs) ; Fiche produit ; Inventaire (sans brouillon, brouillon, récap) ; Liste d'achat.
8. (V2) Recettes et liaison avec le site de vente.

## 6. Journal des arbitrages (révision 2, 25 octobre 2026)

Écarts relevés entre la révision 1 et les maquettes, et décision retenue.

| # | Sujet | Décision |
| --- | --- | --- |
| 1 | Pas d'écran fournisseurs | Fenêtre « Mes fournisseurs » sur la page Produits (US16b), sur le modèle de « Mes catégories » ; création rapide aussi depuis la fenêtre produit. |
| 2 | Derniers mouvements sur l'accueil | Nouvelle route `GET /mouvements?limite=` ; `Mouvement` porte `produit_nom` et `unite`. |
| 3 | Statut « À surveiller » | Champ calculé `statut` côté API (seuil × 1,5), pour que le futur site de vente ait la même règle. |
| 4 | Unité dans l'inventaire | `unite` ajouté à `LigneInventaire`. |
| 5 | Seuil dans la liste d'achat | `seuil_alerte` ajouté aux lignes de `ListeAchat`. |
| 6 | Adresse mail par défaut | `GET /parametres` renvoie `mail_destinataire_defaut`, jamais les identifiants SMTP. |
| 7 | Archivés : page ou onglet | Onglet « Archivés » de la page Produits (`/produits?onglet=archives`), avec motif, date (`archive_le`) et bouton Désarchiver. Le lien « Archivés » de la nav de l'accueil y mène. |
| 8–9 | Écrans manquants | Maquettes ajoutées : fenêtre produit, Réception / sortie, fiche produit, onglet Archivés, Mes fournisseurs, inventaire sans brouillon, récap de validation. |
| 10 | Tri des produits | Tri par nom, comme le dit US2. Les lignes en alerte restent surlignées et le filtre « En alerte seulement » les isole. |
| 11 | Produit hors alerte dans la liste d'achat | Gardé, côté écran uniquement : la liste retouchée est envoyée à l'export et à l'envoi. Pas de nouvelle route. |
| 12 | « Ajoute-les direct à ta liste d'achat » | Texte remplacé par « Clique sur un produit pour voir sa fiche, ou file direct à ta liste d'achat. » |
| 13 | Nuances de la palette | 10 couleurs × (base + 5 nuances) = 60 cases, comme la maquette. |
| 14 | Couleurs récentes | Gardées dans `localStorage`, pas de table. |
| 15 | Couleurs des pastilles | Toujours issues de l'API, texte blanc ou encre calculé partout (filtres, tableau, fenêtres). Les couleurs de la maquette deviennent celles des catégories de départ. |
| 16 | Changement d'ordre | `POST /categories/reordonner`, atomique. |
| 17 | Cibles < 44 px dans les maquettes | La règle des 44 px l'emporte sur les maquettes (filtres, boutons du tableau, onglets, cases de palette, lien de sauvegarde). |
| 18 | Fonds de page | Pois rose pâle 16 px sur toutes les pages. |
| 19 | Navigation | 4 liens sur toutes les pages (Accueil, Produits, Inventaire, Liste d'achat) ; le logo mène à l'accueil. « N°43 » supprimé, la date du jour reste. |
| — | Doublon de nom | Nouveau code 409 `NOM_DEJA_UTILISE` (catégories et fournisseurs). |
| — | Corps de `/liste-achat/envoyer` | `{destinataire, liste: ListeAchat}`, même forme que l'export. |
| — | Mouvement pendant un brouillon | `qte_theorique` remis au stock du moment à chaque saisie ; ajustement = écart ; refus si stock négatif. |
| — | Produit archivé | Plus de mouvement possible ; sa ligne est retirée d'un brouillon en cours. |
| — | Suppression d'un fournisseur | Refusée si un produit, même archivé, y est rattaché. |
| — | Migrations | Pas d'Alembic en V1 : `create_all` + données de départ idempotentes. |
| — | PDF, `.env`, tests | ReportLab, `python-dotenv`, `httpx`. Liste fermée des dépendances au § 1. |
| — | Appli de bureau | Raccourci `.desktop` + `lancer.sh` (serveur en arrière-plan, fenêtre navigateur dédiée). Pas de Docker, pas de PyInstaller en V1. |
| — | Polices hors ligne | Fichiers woff2 servis depuis `app/static/fonts/`. |
