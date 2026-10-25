# Charte INVENThair

Direction : magazine ado années 2000 (logo gonflé, pois, stickers étoile, rubriques « Au sommaire », blocs « Plutôt… : »). Référence visuelle : `maquettes/Charte.dc.html`.

## Couleurs (variables CSS à créer)

```css
:root {
  --prune: #430D2B;        /* logo (contour + ombre), cadres, ombres portées */
  --mauve: #79365C;        /* navigation, statut « À surveiller », texte secondaire */
  --pivoine: #B01050;      /* boutons d'action, statut « Alerte ! » */
  --soleil: #F6BE28;       /* fonds jaunes, stickers, « hair » du logo */
  --caramel: #C47914;      /* numéros façon quiz */
  --sapin: #2D5128;        /* statut « En forme », succès (texte) */
  --asperge: #8DA750;      /* champs de saisie, écarts positifs (texte foncé dessus) */
  --rose-vif: #F070A8;     /* bordures pointillées */
  --rose-pale: #FCD4E6;    /* pois, panneaux roses, lignes en alerte */
  --vieux-rose: #CCA7BC;   /* pointillés secondaires, bordures fines */
  --mindaro: #E4EB9C;      /* fond des messages de succès */
  --erreur: #960018;       /* texte d'erreur */
  --encre: #270317;        /* tout le texte */
  --fond: #FFF0F6;         /* fond de page (blanc pétale) */
  --blanc: #FFFFFF;
}
```

## Typo

- Titres, chiffres, logo : **Lilita One**. Logo = texte blanc, contour 3 px prune, ombre portée pleine 6 px prune.
- Texte : **Nunito** 700 à 900. Rubriques en capitales italiques pivoine.

## Composants

- Bouton principal : pilule pivoine, texte blanc 900, bordure 3 px encre, ombre portée pleine 4 px encre.
- Bouton secondaire : pilule soleil, texte encre, bordure 3 px encre.
- Bouton discret : pilule blanche, bordure 3 px mauve, texte mauve.
- Pastilles de statut : En forme (sapin), À surveiller (mauve), Alerte ! (pivoine), texte blanc.
- Cartes : fond blanc, bordure 3–4 px, rayon 22–28 px, ombre portée pleine (jamais floue).
- Fond de page : `--fond` avec pois `--rose-pale` (radial-gradient 16 px).
- Couleur des catégories : choisie par l'utilisatrice (RGBA). Texte de la pastille calculé : blanc ou encre selon la luminance (le plus contrasté).
