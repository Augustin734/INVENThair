# INVENThair – Cadrage projet

Version du 25 octobre 2026. Source : doc « INVENThair – Cadrage projet ».

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

- **Back** : Python 3.11+, FastAPI, SQLModel (ou SQLAlchemy), SQLite (un fichier `inventhair.db`).
- **Front** : HTML + JS vanilla (ou HTMX) servi par FastAPI. Pas de framework JS, pas de build.
- **PDF** : WeasyPrint ou ReportLab. **Mail** : SMTP (`smtplib`), identifiants dans `.env`.
- **Lancement** : `./start.sh` → venv, migrations, serveur sur `http://localhost:8000`.
- **Tests** : pytest sur l'API.

### Contraintes

- Tourne hors ligne sur un PC Linux, une seule utilisatrice, pas d'authentification en V1 (écoute sur 127.0.0.1 uniquement).
- Interface en français, utilisable sans formation, lisible sur écran portable.
- Le stock n'est jamais modifié « à la main » : toute variation passe par un mouvement tracé.
- Sauvegarde : une commande copie le fichier `.db` dans `backups/` avec la date.
- L'API est le seul point d'accès aux données : le futur site de vente l'utilisera aussi.

## 2. Modèle de données

Six tables en V1 ; le stock d'un produit = somme de ses mouvements, mise en cache dans `produit.stock_actuel`.

| Table | Champs | Notes |
| --- | --- | --- |
| `categorie` | id, nom (unique), couleur_r, couleur_g, couleur_b (0–255), couleur_a (0,2–1), ordre (int), cree_le | Gérée par Maud dans l'appli (ajout, renommage, couleur, ordre, fusion). Relation 1-n : une catégorie a plusieurs produits, un produit a une seule catégorie (`produit.categorie_id`, obligatoire). Au démarrage : Gels, Vernis, Capsules, Consommables. |
| `fournisseur` | id, nom, email?, site_url?, notes? | Optionnel sur un produit |
| `produit` | id, nom, reference?, categorie_id, fournisseur_id?, unite (`piece`, `ml`, `g`, `flacon`), stock_actuel (décimal), seuil_alerte, qte_reappro, prix_unitaire?, archive (bool, défaut false), archive_motif?, cree_le, maj_le | `qte_reappro` = quantité proposée dans la liste d'achat |
| `mouvement` | id, produit_id, type (`entree`, `sortie`, `ajustement`), quantite (signée), motif?, inventaire_id?, cree_le | Jamais modifié ni supprimé |
| `inventaire` | id, statut (`brouillon`, `valide`, `annule`), commentaire?, cree_le, valide_le? | Un seul brouillon à la fois |
| `ligne_inventaire` | id, inventaire_id, produit_id, qte_theorique, qte_comptee?, ecart (calculé) | Une ligne par produit actif à l'ouverture |

**Règles métier**

- `stock_actuel` est recalculé à chaque mouvement, dans la même transaction.
- Une sortie qui rendrait le stock négatif est refusée (erreur 409).
- Valider un inventaire crée un mouvement `ajustement` par ligne dont l'écart ≠ 0, puis passe l'inventaire en `valide`. Un inventaire validé est en lecture seule.
- Un produit archivé n'apparaît plus dans les listes, alertes, inventaires ni la liste d'achat ; son historique reste.
- Alerte = produit non archivé avec `stock_actuel <= seuil_alerte`.

**Catégories** : le nom est unique (insensible à la casse). Une catégorie qui contient des produits ne peut pas être supprimée telle quelle : on choisit une catégorie de destination, les produits y sont déplacés, puis elle est supprimée (fusion). Les produits archivés comptent aussi.

**Prévu pour la V2 (ne pas coder maintenant)** : `article_vente` (un modèle d'ongles vendu) et `recette_ligne` (article_vente_id, produit_id, quantite_par_unite). Disponibilité d'un article = min(stock_actuel / quantite_par_unite) sur ses lignes.

## 3. User stories

Une seule persona : Maud, gérante de l'onglerie. Chaque story est « finie » quand ses critères passent en test.

| ID | En tant que Maud, je veux… | Critères d'acceptation |
| --- | --- | --- |
| US1 | ajouter un produit (nom, catégorie, unité, seuil, qté de réappro) | Champs obligatoires vérifiés ; catégorie choisie dans une liste déroulante (avec « + nouvelle catégorie ») ; stock initial saisi = mouvement `entree` ; apparaît dans la liste |
| US2 | voir la liste de mes produits avec leur stock | Tri par nom, filtre par catégorie (pastilles aux couleurs des catégories) et recherche texte ; produits en alerte surlignés |
| US3 | modifier un produit | Le stock n'est pas modifiable ici (seulement via mouvement ou inventaire) ; la catégorie peut changer |
| US4 | archiver un produit que je n'aime pas, avec un motif | Disparaît des listes, alertes, inventaires ; visible dans l'onglet « Archivés » ; désarchivable |
| US5 | enregistrer une réception de commande | Mouvement `entree`, stock à jour immédiatement |
| US6 | enregistrer une sortie ou une perte | Mouvement `sortie` ; refus si stock insuffisant |
| US7 | voir l'historique d'un produit | Liste des mouvements, du plus récent au plus ancien |
| US8 | lancer un inventaire | Crée un brouillon avec tous les produits actifs et leur qté théorique ; refus si un brouillon existe déjà |
| US9 | saisir mes comptages au fil de l'eau | Sauvegarde ligne par ligne ; je peux quitter et reprendre ; écart affiché en direct |
| US10 | valider l'inventaire | Récap des écarts avant confirmation ; ajustements créés ; inventaire verrouillé. Lignes non comptées = refus, sauf si je coche « garder la qté théorique » |
| US11 | voir les produits en alerte dès l'accueil | Bandeau avec le nombre et la liste, lien vers la liste d'achat |
| US12 | générer la liste d'achat | Produits en alerte, groupés par fournisseur, qté = `qte_reappro` modifiable avant export |
| US13 | télécharger la liste en CSV ou PDF | Fichier nommé `liste-achat-AAAA-MM-JJ` |
| US14 | envoyer la liste par mail | Adresse destinataire saisie (pré-remplie depuis `.env`) ; PDF en pièce jointe ; message de succès ou d'erreur clair |
| US15 | sauvegarder ma base | Bouton ou `./backup.sh` → copie datée dans `backups/` |
| US16 | gérer mes catégories depuis une fenêtre « Mes catégories » (bouton sur la page Produits) | Ajouter, renommer, changer l'ordre ; couleur via un sélecteur façon Office (onglet Palette : 10 couleurs du thème × 5 nuances, 10 couleurs standard, 8 couleurs récentes ; onglet Personnalisée : curseurs R, V, B, opacité A de 20 à 100 %, saisie hexa, code rgba affiché) ; texte des pastilles en blanc ou encre selon la luminosité de la couleur ; nombre de produits affiché par catégorie ; nom en double refusé ; supprimer une catégorie vide directement, une catégorie non vide seulement en choisissant où déplacer ses produits ; les filtres et listes déroulantes se mettent à jour sans recharger |

**V2 (pour mémoire)** : US17 définir la recette d'un modèle d'ongles ; US18 le site de vente lit la disponibilité et masque l'article en rupture ; US19 une vente déclenche les sorties de stock correspondantes.

## 4. Contrat d'interface (API REST)

Base `http://localhost:8000/api/v1`, JSON en UTF-8, dates ISO 8601, champs en snake_case. FastAPI génère la doc sur `/docs` : elle doit toujours correspondre à ce tableau.

### Endpoints

| Méthode | Route | Rôle | Réponse |
| --- | --- | --- | --- |
| GET | `/categories` | Lister (avec `nb_produits`) | 200 `[Categorie]` |
| POST | `/categories` | Créer | 201 `Categorie` |
| PATCH / DELETE | `/categories/{id}` | Modifier (nom, couleur, ordre) / supprimer. Non vide : 409 `RESSOURCE_UTILISEE`, sauf avec `?fusionner_vers={id}` qui déplace les produits puis supprime | 200 / 204, 409 |
| GET | `/fournisseurs` | Lister | 200 `[Fournisseur]` |
| POST | `/fournisseurs` | Créer | 201 |
| PATCH / DELETE | `/fournisseurs/{id}` | Modifier / supprimer (refus si utilisé) | 200 / 204, 409 |
| GET | `/produits?categorie_id=&q=&archive=false&en_alerte=` | Lister avec filtres | 200 `[Produit]` |
| POST | `/produits` | Créer (+ `stock_initial` optionnel) | 201 `Produit` |
| GET | `/produits/{id}` | Détail | 200, 404 |
| PATCH | `/produits/{id}` | Modifier (sans `stock_actuel`) | 200, 422 |
| POST | `/produits/{id}/archiver` | Archiver, body `{motif?}` | 200 |
| POST | `/produits/{id}/desarchiver` | Désarchiver | 200 |
| GET | `/produits/{id}/mouvements` | Historique | 200 `[Mouvement]` |
| POST | `/mouvements` | Entrée / sortie, body `{produit_id, type, quantite, motif?}` | 201, 409 si stock < 0 |
| GET | `/inventaires` | Lister | 200 `[Inventaire]` |
| POST | `/inventaires` | Ouvrir un brouillon | 201 `InventaireDetail`, 409 si brouillon existant |
| GET | `/inventaires/{id}` | Détail avec lignes | 200 `InventaireDetail` |
| PATCH | `/inventaires/{id}/lignes/{ligne_id}` | Saisir `{qte_comptee}` | 200 `LigneInventaire` |
| POST | `/inventaires/{id}/valider` | Body `{garder_theorique_si_vide: bool}` | 200, 409 si déjà validé ou lignes vides |
| POST | `/inventaires/{id}/annuler` | Annuler un brouillon | 200 |
| GET | `/alertes` | Produits sous seuil | 200 `[Produit]` |
| GET | `/liste-achat` | Liste groupée par fournisseur | 200 `ListeAchat` |
| POST | `/liste-achat/export?format=csv\|pdf` | Body `ListeAchat` éventuellement retouchée | 200 fichier |
| POST | `/liste-achat/envoyer` | Body `{destinataire, lignes}` | 202, 502 si SMTP KO |
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
  "Produit": {
    "id": 12, "nom": "Gel builder clair", "reference": "GB-50",
    "categorie_id": 2, "fournisseur_id": 1, "unite": "ml",
    "stock_actuel": 35.0, "seuil_alerte": 50.0, "qte_reappro": 100.0,
    "prix_unitaire": 0.24, "archive": false, "archive_motif": null,
    "en_alerte": true, "cree_le": "2026-10-24T10:00:00", "maj_le": "2026-10-24T10:00:00"
  },
  "Mouvement": { "id": 88, "produit_id": 12, "type": "sortie", "quantite": -15.0, "motif": "perte", "inventaire_id": null, "cree_le": "…" },
  "InventaireDetail": {
    "id": 3, "statut": "brouillon", "cree_le": "…", "valide_le": null,
    "lignes": [{ "id": 40, "produit_id": 12, "produit_nom": "Gel builder clair", "qte_theorique": 35.0, "qte_comptee": 30.0, "ecart": -5.0 }]
  },
  "ListeAchat": {
    "genere_le": "…",
    "fournisseurs": [{ "fournisseur_id": 1, "nom": "Grossiste A", "lignes": [{ "produit_id": 12, "nom": "Gel builder clair", "unite": "ml", "stock_actuel": 35.0, "quantite": 100.0 }] }]
  }
}
```

`quantite` dans `POST /mouvements` est toujours positive : le serveur applique le signe selon `type`.

### Erreurs

Toujours le même format : `{"erreur": {"code": "STOCK_INSUFFISANT", "message": "Texte lisible en français", "details": {}}}`.

| HTTP | Codes |
| --- | --- |
| 404 | `INTROUVABLE` |
| 409 | `STOCK_INSUFFISANT`, `INVENTAIRE_EN_COURS`, `INVENTAIRE_VERROUILLE`, `LIGNES_NON_COMPTEES`, `RESSOURCE_UTILISEE` |
| 422 | `VALIDATION` (détails par champ) |
| 502 | `ENVOI_MAIL_ECHOUE` |

## 5. Étapes

1. Squelette : FastAPI, SQLite, modèles, `start.sh`, `/health`.
2. CRUD catégories (avec fusion), fournisseurs, produits + archivage (US1–US4, US16).
3. Mouvements et historique (US5–US7).
4. Inventaires (US8–US10).
5. Alertes et liste d'achat, exports CSV/PDF (US11–US13).
6. Envoi mail et sauvegarde (US14–US15).
7. Front : pages Accueil, Produits (+ fenêtre Mes catégories), Inventaire, Liste d'achat, Archivés — d'après `docs/maquettes/`.
8. (V2) Recettes et liaison avec le site de vente.
