# INVENThair

Appli web locale de gestion de stock pour une onglerie (une utilisatrice : Maud). Interface et code métier en français.

## Sources de vérité (à lire avant de coder)

- `docs/cadrage.md` : cahier des charges, modèle de données, user stories (US1–US16), contrat d'API, étapes. **Il fait foi.**
- `docs/maquettes/*.html` : maquettes validées par la DA. Ce sont des références visuelles, pas du code à copier tel quel (voir plus bas).
- `docs/charte.md` : couleurs, typo, composants.

## Règles

- Ne pas ajouter de table, de route, de champ ou de dépendance absents de `docs/cadrage.md` sans le signaler et demander d'abord.
- Une session = une étape de la section « Étapes » du cadrage. Annonce l'étape en cours, ne touche pas aux étapes déjà validées sans raison.
- Ne pas coder la V2 (recettes, vente, `/disponibilites`, `/ventes`), seulement ne pas la bloquer.
- Stack : Python 3.11+, FastAPI, SQLModel, SQLite, pytest. Front en HTML + JS vanilla (ou HTMX) servi par FastAPI depuis `app/static/` et `app/templates/`. Pas de framework JS, pas de build, pas de Docker, pas d'auth.
- Toute variation de stock passe par une seule fonction `appliquer_mouvement()` dans `app/services/`.
- Format d'erreur unique : `{"erreur": {"code", "message", "details"}}` avec les codes listés dans le cadrage.
- Chaque endpoint a au moins un test pytest (cas nominal + un cas d'erreur).
- Structure : `app/main.py`, `app/config.py`, `app/database.py`, `app/erreurs.py`, `app/models.py`, `app/schemas.py`, `app/services/`, `app/routers/`, `app/static/`, `app/templates/`, `tests/`, `scripts/` (fonctions shell communes, modèle du raccourci `.desktop`). Les scripts de lancement sont à la racine.
- Lever les erreurs métier avec `ErreurMetier(statut, code, message, details)` (`app/erreurs.py`) ; ne jamais construire la réponse d'erreur à la main.
- Fin de session : `pytest` vert, `./start.sh` démarre, commit avec un message clair.

## Front et maquettes

- Les fichiers `docs/maquettes/*.dc.html` viennent d'un outil de maquettage : la balise `<x-dc>`, les `{{ variables }}`, `<sc-for>`, `<sc-if>` et la classe `Component extends DCLogic` sont propres à cet outil. Reprends la **structure, les textes, les couleurs, les tailles et les espacements**, mais réécris en HTML/CSS/JS vanilla branché sur l'API.
- Extraire les styles inline dans une feuille commune `app/static/style.css` avec des variables CSS (voir `docs/charte.md`). Les maquettes répètent les styles : factorise-les en classes (`.btn`, `.btn-primaire`, `.pastille`, `.carte`, etc.).
- Correspondance pages ↔ maquettes : Accueil = `Main.dc.html`, Produits = `Produits.dc.html` (onglet Archivés = `ProduitsArchives.html`), fenêtre Mes catégories = `Categories.dc.html` (modale sur la page Produits), fenêtre Mes fournisseurs = `Fournisseurs.html`, fenêtre Nouveau / Modifier produit = `ProduitFenetre.html`, fenêtre Réception / sortie = `Mouvement.html`, Fiche produit = `FicheProduit.html`, Inventaire = `Inventaire.dc.html` (sans brouillon = `InventaireAccueil.html`, récap de validation = `InventaireRecap.html`), Liste d'achat = `ListeAchat.dc.html`, charte = `Charte.dc.html`.
- Les maquettes `*.html` (sans `.dc`) sont du HTML statique ordinaire qui s'appuie sur `docs/maquettes/maquettes.css` : c'est un bon point de départ pour `app/static/style.css`.
- En cas d'écart entre une maquette et le cadrage, le cadrage gagne (voir son § 6, « Journal des arbitrages »).
- Les données dans les maquettes (produits, quantités, « Grossiste A ») sont des exemples : tout vient de l'API.
- Polices : Lilita One (titres) et Nunito 500–900 (texte), servies en local depuis `app/static/fonts/` (woff2, licence OFL) : l'appli doit marcher hors ligne. Garder une pile de repli système derrière.
- Accessibilité : vrais `<button>`, `<label>` sur chaque champ, cibles ≥ 44 px, contraste texte ≥ 4,5:1.

## Git

- `main` = version installée chez Maud, ne reçoit que des merges depuis `dev`, avec l'accord explicite d'Augustin, puis un tag `vX.Y.Z`.
- `dev` = branche d'intégration. Tout part de `dev` et y revient.
- Une branche par sujet, créée depuis `dev` à jour : `feat/<sujet>` (ex. `feat/etape-2-categories`), `fix/<sujet>`, `docs/<sujet>`, `chore/<sujet>`, `test/<sujet>`.
- Commits petits et cohérents, format Conventional Commits en français : `feat(produits): archivage avec motif`, `fix(inventaire): …`, `docs: …`, `test: …`, `chore: …`. Corps du message pour le « pourquoi » si utile.
- Push régulier de la branche. À la fin du sujet : `pytest` vert, puis PR vers `dev` avec `gh pr create` (résumé, US couvertes, comment tester), merge (sans squash) et suppression de la branche.
- Jamais de force-push sur `main` ni `dev`. Ne jamais committer `.env`, `inventhair.db`, `backups/`, `logs/`, `.venv/`.

