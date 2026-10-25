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
- Structure : `app/main.py`, `app/models.py`, `app/schemas.py`, `app/services/`, `app/routers/`, `app/static/`, `app/templates/`, `tests/`.
- Fin de session : `pytest` vert, `./start.sh` démarre, commit avec un message clair.

## Front et maquettes

- Les fichiers `docs/maquettes/*.dc.html` viennent d'un outil de maquettage : la balise `<x-dc>`, les `{{ variables }}`, `<sc-for>`, `<sc-if>` et la classe `Component extends DCLogic` sont propres à cet outil. Reprends la **structure, les textes, les couleurs, les tailles et les espacements**, mais réécris en HTML/CSS/JS vanilla branché sur l'API.
- Extraire les styles inline dans une feuille commune `app/static/style.css` avec des variables CSS (voir `docs/charte.md`). Les maquettes répètent les styles : factorise-les en classes (`.btn`, `.btn-primaire`, `.pastille`, `.carte`, etc.).
- Correspondance pages ↔ maquettes : Accueil = `Main.dc.html`, Produits = `Produits.dc.html`, fenêtre Mes catégories = `Categories.dc.html` (modale sur la page Produits), Inventaire = `Inventaire.dc.html`, Liste d'achat = `ListeAchat.dc.html`, charte = `Charte.dc.html`.
- Les données dans les maquettes (produits, quantités, « Grossiste A ») sont des exemples : tout vient de l'API.
- Polices Google Fonts : Lilita One (titres) et Nunito 500–900 (texte). Prévoir une police de repli locale, l'appli doit marcher hors ligne.
- Accessibilité : vrais `<button>`, `<label>` sur chaque champ, cibles ≥ 44 px, contraste texte ≥ 4,5:1.
