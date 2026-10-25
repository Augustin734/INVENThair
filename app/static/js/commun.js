// Outils partagés par toutes les pages : appels API, création d'éléments, formats français, annonces.
// Le DOM est construit avec h() (jamais innerHTML) : un nom de produit ne peut pas injecter de HTML.

// ---------- API ----------

export class ErreurApi extends Error {
  constructor(statut, code, message, details = {}) {
    super(message);
    this.statut = statut;
    this.code = code;
    this.details = details;
  }
}

/** Appelle /api/v1 ; renvoie le JSON, null (204) ou la Response (fichier). Lève ErreurApi au format unique. */
export async function api(methode, chemin, corps) {
  const options = { method: methode, headers: { Accept: 'application/json' } };
  if (corps !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(corps);
  }
  let reponse;
  try {
    reponse = await fetch(`/api/v1${chemin}`, options);
  } catch {
    throw new ErreurApi(0, 'RESEAU', "INVENThair ne répond pas. Relance l'appli depuis le Bureau.");
  }
  if (reponse.status === 204) return null;
  if (!reponse.ok) {
    let erreur = {};
    try {
      erreur = (await reponse.json()).erreur ?? {};
    } catch {
      /* corps illisible : message générique */
    }
    throw new ErreurApi(reponse.status, erreur.code ?? 'ERREUR', erreur.message ?? 'Une erreur est survenue.', erreur.details ?? {});
  }
  const type = reponse.headers.get('content-type') ?? '';
  return type.includes('application/json') ? reponse.json() : reponse;
}

// ---------- DOM ----------

/** h('a', {class: 'btn', href: '/x', onclick: f}, 'texte', autreElement) */
export function h(tag, attributs = {}, ...enfants) {
  const el = document.createElement(tag);
  for (const [cle, valeur] of Object.entries(attributs ?? {})) {
    if (valeur === null || valeur === undefined || valeur === false) continue;
    if (cle.startsWith('on') && typeof valeur === 'function') el.addEventListener(cle.slice(2), valeur);
    else if (cle === 'class') el.className = valeur;
    else if (cle === 'style' && typeof valeur === 'object') Object.assign(el.style, valeur);
    else if (cle === 'dataset') Object.assign(el.dataset, valeur);
    else if (valeur === true) el.setAttribute(cle, '');
    else el.setAttribute(cle, String(valeur));
  }
  ajouter(el, enfants);
  return el;
}

function ajouter(parent, enfants) {
  for (const enfant of enfants.flat(Infinity)) {
    if (enfant === null || enfant === undefined || enfant === false) continue;
    parent.append(enfant instanceof Node ? enfant : document.createTextNode(String(enfant)));
  }
}

/** Remplace le contenu d'un élément. */
export function remplir(el, ...enfants) {
  el.replaceChildren();
  ajouter(el, enfants);
  return el;
}

export const $ = (selecteur, racine = document) => racine.querySelector(selecteur);

// ---------- Formats français ----------

const formatNombre = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 3 });
const UNITES = { piece: ['pièce', 'pièces'], flacon: ['flacon', 'flacons'], ml: ['ml', 'ml'], g: ['g', 'g'] };

export const nombreFr = (valeur) => formatNombre.format(valeur);
export const uniteFr = (unite, quantite = 1) => UNITES[unite][Math.abs(quantite) >= 2 ? 1 : 0];
export const quantiteFr = (quantite, unite) => `${nombreFr(quantite)} ${uniteFr(unite, quantite)}`;
/** « +100 ml », « −15 ml » (vrai signe moins). */
export const variationFr = (quantite, unite) => `${quantite > 0 ? '+' : quantite < 0 ? '−' : ''}${quantiteFr(Math.abs(quantite), unite)}`;

const jourCourt = new Intl.DateTimeFormat('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
const jourMois = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' });
const jourLong = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

const enDate = (valeur) => (valeur instanceof Date ? valeur : new Date(valeur));
/** « ven. 23 oct. » */
export const dateCourte = (valeur) => jourCourt.format(enDate(valeur));
/** « 3 oct. » */
export const dateJourMois = (valeur) => jourMois.format(enDate(valeur));
/** « dimanche 25 octobre 2026 » */
export const dateLongue = (valeur = new Date()) => jourLong.format(enDate(valeur));
/** « 10 h 52 » */
export const heureFr = (valeur = new Date()) => {
  const d = enDate(valeur);
  return `${d.getHours()} h ${String(d.getMinutes()).padStart(2, '0')}`;
};

// ---------- Statuts, types, couleurs ----------

export const STATUTS = {
  alerte: { libelle: 'Alerte !', classe: 'p-alerte', couleurTexte: 'qte-moins' },
  a_surveiller: { libelle: 'À surveiller', classe: 'p-surveiller', couleurTexte: '' },
  en_forme: { libelle: 'En forme', classe: 'p-forme', couleurTexte: 'qte-plus' },
};

export const TYPES_MOUVEMENT = {
  entree: { libelle: 'Entrée', classe: 'p-entree' },
  sortie: { libelle: 'Sortie', classe: 'p-sortie' },
  ajustement: { libelle: 'Ajustement', classe: 'p-ajustement' },
};

export const pastilleStatut = (statut) => h('span', { class: `pastille ${STATUTS[statut].classe}` }, STATUTS[statut].libelle);

export const couleurCss = ({ r, g, b, a }) => `rgba(${r}, ${g}, ${b}, ${Math.round(a * 100) / 100})`;

/** Blanc ou encre, selon ce qui contraste le mieux avec la couleur posée sur fond blanc (charte). */
export function texteSur({ r, g, b, a }) {
  const lin = [r, g, b]
    .map((v) => (v * a + 255 * (1 - a)) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  const L = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
  return 1.05 / (L + 0.05) >= (L + 0.05) / 0.0555 ? '#FFFFFF' : '#270317';
}

export const pastilleCategorie = (categorie, suffixe = '') =>
  h('span', { class: 'pastille p-categorie', style: { background: couleurCss(categorie.couleur), color: texteSur(categorie.couleur) } }, categorie.nom + suffixe);

// ---------- Annonces ----------

/** Message temporaire en bas de l'écran ; « erreur » reste plus longtemps. */
export function annoncer(message, type = 'succes') {
  const zone = $('#annonces');
  const el = h('p', { class: `msg msg-${type}`, role: type === 'erreur' ? 'alert' : 'status' }, message);
  zone.append(el);
  setTimeout(() => el.remove(), type === 'erreur' ? 9000 : 5000);
}

/** Affiche une ErreurApi (ou toute erreur) de façon lisible. */
export function annoncerErreur(erreur) {
  annoncer(erreur instanceof ErreurApi ? erreur.message : 'Oups, une erreur inattendue.', 'erreur');
  if (!(erreur instanceof ErreurApi)) console.error(erreur);
}

// ---------- Fichiers ----------

/** Déclenche le téléchargement d'une Response (nom tiré de Content-Disposition). */
export async function telecharger(reponse, nomParDefaut) {
  const entete = reponse.headers.get('content-disposition') ?? '';
  const nom = /filename="([^"]+)"/.exec(entete)?.[1] ?? nomParDefaut;
  const url = URL.createObjectURL(await reponse.blob());
  const lien = h('a', { href: url, download: nom, hidden: true });
  document.body.append(lien);
  lien.click();
  lien.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------- Fenêtres (<dialog>) ----------

/** Les boutons [data-fermer] ferment leur <dialog>. Échap ferme nativement. */
export function brancherFenetres(racine = document) {
  racine.addEventListener('click', (evenement) => {
    const bouton = evenement.target.closest('[data-fermer]');
    if (bouton) bouton.closest('dialog')?.close();
  });
}

export const lienProduit = (id) => `/produits/${id}`;
