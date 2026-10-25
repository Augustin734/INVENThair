// Sélecteur de couleur façon Office (US16) : palette (10 couleurs du thème × 6 nuances,
// 10 standard, 8 récentes) ou couleur personnalisée (R, V, B, opacité, hexa).
import { couleurCss, h, texteSur } from './commun.js';

const CLE_RECENTES = 'inventhair.couleurs-recentes';

const THEME = [
  ['#FFFFFF', 'Blanc'], ['#F070A8', 'Rose vif'], ['#270317', 'Encre'], ['#430D2B', 'Prune'], ['#79365C', 'Mauve'],
  ['#B01050', 'Pivoine'], ['#C47914', 'Caramel'], ['#F6BE28', 'Soleil'], ['#2D5128', 'Vert sapin'], ['#8DA750', 'Asperge'],
];
const STANDARD = [
  ['#C00000', 'Rouge foncé'], ['#FF0000', 'Rouge'], ['#FFC000', 'Orange'], ['#FFFF00', 'Jaune'], ['#92D050', 'Vert clair'],
  ['#00B050', 'Vert'], ['#00B0F0', 'Bleu clair'], ['#0070C0', 'Bleu'], ['#002060', 'Bleu foncé'], ['#7030A0', 'Violet'],
];
const NUANCES = [
  [(c) => c, ''],
  [(c) => melanger(c, 0.8, 255), ', plus clair 80 %'],
  [(c) => melanger(c, 0.6, 255), ', plus clair 60 %'],
  [(c) => melanger(c, 0.4, 255), ', plus clair 40 %'],
  [(c) => melanger(c, 0.25, 0), ', plus foncé 25 %'],
  [(c) => melanger(c, 0.5, 0), ', plus foncé 50 %'],
];

const depuisHexa = (hexa) => ({ r: parseInt(hexa.slice(1, 3), 16), g: parseInt(hexa.slice(3, 5), 16), b: parseInt(hexa.slice(5, 7), 16), a: 1 });
const versHexa = (c) => `#${[c.r, c.g, c.b].map((v) => v.toString(16).padStart(2, '0')).join('').toUpperCase()}`;
const memeRvb = (a, b) => a.r === b.r && a.g === b.g && a.b === b.b;
function melanger(c, t, vers) {
  const m = (v) => Math.round(v + (vers - v) * t);
  return { r: m(c.r), g: m(c.g), b: m(c.b), a: 1 };
}

function lireRecentes() {
  try {
    const valeur = JSON.parse(localStorage.getItem(CLE_RECENTES) ?? '[]');
    return Array.isArray(valeur) ? valeur.slice(0, 8) : [];
  } catch {
    return [];
  }
}

function memoriserRecente(couleur) {
  const recentes = [couleur, ...lireRecentes().filter((c) => !(memeRvb(c, couleur) && c.a === couleur.a))].slice(0, 8);
  try {
    localStorage.setItem(CLE_RECENTES, JSON.stringify(recentes));
  } catch {
    /* stockage indisponible : les récentes ne sont simplement pas gardées */
  }
}

/** Renvoie l'élément du sélecteur. `surAppliquer(couleur)` reçoit {r, g, b, a}. */
export function selecteurCouleur({ nom, couleur, surAppliquer, surAnnuler }) {
  let brouillon = { ...couleur };
  let onglet = 'palette';
  const cases = [];

  const caseCouleur = (c, libelle, damier = false) => {
    const bouton = h('button', {
      type: 'button',
      class: `case-couleur${damier ? ' damier' : ''}`,
      title: `${libelle} (${versHexa(c)})`,
      'aria-label': `${libelle} (${versHexa(c)})`,
      onclick: () => { brouillon = damier ? { ...c } : { ...brouillon, r: c.r, g: c.g, b: c.b }; maj(); },
    }, h('span', { style: { background: couleurCss(c) } }));
    cases.push({ bouton, c, exacte: damier });
    return bouton;
  };

  const grilleTheme = h('div', { class: 'grille-couleurs', role: 'group', 'aria-label': 'Couleurs du thème et nuances' },
    NUANCES.flatMap(([varier, suffixe]) => THEME.map(([hexa, libelle]) => caseCouleur(varier(depuisHexa(hexa)), libelle + suffixe))));
  const grilleStandard = h('div', { class: 'grille-couleurs', role: 'group', 'aria-label': 'Couleurs standard' },
    STANDARD.map(([hexa, libelle]) => caseCouleur(depuisHexa(hexa), libelle)));
  const recentes = lireRecentes();
  const blocRecentes = recentes.length > 0 && [
    h('span', { class: 'rubrique' }, 'Couleurs récentes'),
    h('div', { class: 'ligne', style: { gap: '4px' } }, recentes.map((c) => caseCouleur(c, `Récente ${couleurCss(c)}`, true))),
  ];
  const panneauPalette = h('div', { class: 'pile', style: { gap: '10px' } },
    h('span', { class: 'rubrique' }, 'Couleurs du thème'), grilleTheme,
    h('span', { class: 'rubrique' }, 'Couleurs standard'), grilleStandard,
    blocRecentes);

  const curseur = (cle, libelle, min, max, accent) => {
    const valeur = h('span');
    const controle = h('input', {
      type: 'range', min, max, style: { accentColor: accent },
      oninput: () => {
        brouillon = { ...brouillon, [cle]: cle === 'a' ? Number(controle.value) / 100 : Number(controle.value) };
        maj();
      },
    });
    return { valeur, controle, bloc: h('label', { class: 'curseur' }, h('span', {}, `${libelle} : `, valeur, cle === 'a' ? ' %' : ''), controle) };
  };
  const curseurs = {
    r: curseur('r', 'Rouge (R)', 0, 255, '#B01050'),
    g: curseur('g', 'Vert (V)', 0, 255, '#2D5128'),
    b: curseur('b', 'Bleu (B)', 0, 255, '#430D2B'),
    a: curseur('a', 'Opacité (A)', 20, 100, '#79365C'),
  };
  const saisieHexa = h('input', {
    class: 'saisie saisie-code', type: 'text', maxlength: 7, spellcheck: 'false',
    onchange: () => {
      const m = /^#?([0-9a-f]{6})$/i.exec(saisieHexa.value.trim());
      if (m) { brouillon = { ...brouillon, ...depuisHexa(`#${m[1]}`), a: brouillon.a }; }
      maj();
    },
  });
  const codeRgba = h('code', { class: 'code-rgba' });
  const panneauPerso = h('div', { class: 'curseurs' },
    Object.values(curseurs).map((c) => c.bloc),
    h('label', { class: 'curseur' }, 'Hexadécimal', saisieHexa),
    h('div', { class: 'curseur' }, 'Code RGBA', codeRgba));

  const ongletPalette = h('button', { type: 'button', role: 'tab', onclick: () => { onglet = 'palette'; maj(); } }, 'Palette');
  const ongletPerso = h('button', { type: 'button', role: 'tab', onclick: () => { onglet = 'perso'; maj(); } }, 'Personnalisée');

  const pastilleApercu = h('span');
  const codeApercu = h('code', { class: 'texte-doux' });
  const avertissement = h('span', { class: 'erreur-champ', hidden: true }, 'Peu opaque : la pastille sera pâle sur fond blanc.');

  function maj() {
    const estPalette = onglet === 'palette';
    ongletPalette.setAttribute('aria-selected', String(estPalette));
    ongletPerso.setAttribute('aria-selected', String(!estPalette));
    panneauPalette.hidden = !estPalette;
    panneauPerso.hidden = estPalette;
    for (const { bouton, c, exacte } of cases) {
      const choisie = memeRvb(c, brouillon) && (!exacte || c.a === brouillon.a);
      bouton.setAttribute('aria-pressed', String(choisie));
    }
    for (const [cle, { valeur, controle }] of Object.entries(curseurs)) {
      const v = cle === 'a' ? Math.round(brouillon.a * 100) : brouillon[cle];
      valeur.textContent = v;
      if (document.activeElement !== controle) controle.value = v;
    }
    if (document.activeElement !== saisieHexa) saisieHexa.value = versHexa(brouillon);
    const css = couleurCss(brouillon);
    codeRgba.textContent = css;
    codeApercu.textContent = css;
    Object.assign(pastilleApercu.style, { background: css, color: texteSur(brouillon) });
    pastilleApercu.textContent = nom || 'Nouvelle catégorie';
    avertissement.hidden = brouillon.a >= 0.6;
  }

  const element = h('section', { class: 'selecteur-couleur', 'aria-label': `Couleur de « ${nom} »` },
    h('div', { class: 'ligne', style: { justifyContent: 'space-between' } },
      h('h2', {}, `Couleur de « ${nom || 'Nouvelle catégorie'} »`),
      h('div', { class: 'onglets-mini', role: 'tablist', 'aria-label': 'Mode de choix' }, ongletPalette, ongletPerso)),
    panneauPalette,
    panneauPerso,
    h('div', { class: 'apercu-couleur' },
      h('span', { class: 'rubrique' }, 'Aperçu'),
      h('span', { class: 'damier pastille-damier' }, pastilleApercu),
      codeApercu,
      avertissement,
      h('div', { class: 'ligne', style: { marginLeft: 'auto' } },
        h('button', { type: 'button', class: 'btn btn-discret btn-petit', onclick: () => surAnnuler?.() }, 'Annuler'),
        h('button', { type: 'button', class: 'btn btn-primaire btn-petit', onclick: () => { memoriserRecente(brouillon); surAppliquer({ ...brouillon }); } }, 'Appliquer'))));
  maj();
  return element;
}
