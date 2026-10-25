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

/** Même règle que l'API : alerte ≤ seuil, à surveiller ≤ 1,5 × seuil. */
export function statutDe(stock, seuil) {
  if (stock <= seuil) return 'alerte';
  if (stock <= 1.5 * seuil) return 'a_surveiller';
  return 'en_forme';
}

/** Recherche sans casse ni accents (« ecrin » trouve « Écrin »). */
export const normaliser = (texte) => (texte ?? '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();

const comparateurNoms = new Intl.Collator('fr', { sensitivity: 'base' });
export const parNom = (a, b) => comparateurNoms.compare(a.nom, b.nom);

// ---------- Fenêtres construites en JS ----------

const ICONE_FERMER = () => {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '20');
  svg.setAttribute('height', '20');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '3');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('aria-hidden', 'true');
  const trait = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  trait.setAttribute('d', 'M6 6l12 12M18 6L6 18');
  svg.append(trait);
  return svg;
};

let compteurFenetres = 0;

/**
 * Ouvre une fenêtre modale à la charte. Renvoie { dialog, corps, pied, fermer }.
 * Le <dialog> est retiré du DOM à la fermeture ; `surFermeture` est alors appelé.
 */
export function ouvrirFenetre({ titre, rubrique, description, etroite = false, classeCarte = '', surFermeture }) {
  const idTitre = `fenetre-titre-${++compteurFenetres}`;
  const corps = h('div', { class: 'pile', style: { gap: '18px' } });
  const pied = h('div', { class: 'fenetre-pied' });
  const dialog = h('dialog', { class: `cadre-fenetre${etroite ? ' etroit' : ''}`, 'aria-labelledby': idTitre },
    h('section', { class: `fenetre ${classeCarte}` },
      h('div', { class: 'etoile', 'aria-hidden': 'true' }),
      h('div', { class: 'fenetre-tete' },
        h('div', { class: 'pile' },
          rubrique && h('span', { class: 'onglet-rubrique' }, rubrique),
          h('h1', { id: idTitre }, titre),
          description && h('p', {}, description)),
        h('button', { type: 'button', class: 'fermer', 'aria-label': 'Fermer', 'data-fermer': true }, ICONE_FERMER())),
      corps,
      pied));
  dialog.addEventListener('click', (e) => { if (e.target.closest('[data-fermer]')) dialog.close(); });
  dialog.addEventListener('close', () => { dialog.remove(); surFermeture?.(); });
  document.body.append(dialog);
  dialog.showModal();
  return { dialog, corps, pied, fermer: () => dialog.close() };
}

// ---------- Champs de formulaire ----------

/** Champ étiqueté ; `nom` sert à retrouver le champ quand l'API renvoie une erreur dessus. */
export function champ({ nom, libelle, obligatoire = false, controle, aide, classe = '' }) {
  const id = controle.id || `champ-${nom}-${++compteurFenetres}`;
  controle.id = id;
  controle.name ||= nom;
  const idErreur = `${id}-erreur`;
  return h('div', { class: `champ ${classe}`, 'data-champ': nom },
    h('label', { for: id }, libelle, obligatoire && h('span', { class: 'obligatoire' }, ' *')),
    controle,
    aide && h('p', { class: 'aide' }, aide),
    h('p', { class: 'erreur-champ', id: idErreur, hidden: true }));
}

/** Remplace `el` à sa place par `fabrique(el)` (qui peut contenir `el` lui-même). */
export function envelopper(el, fabrique) {
  const parent = el.parentNode;
  const suivant = el.nextSibling;
  const nouveau = fabrique(el);
  parent.insertBefore(nouveau, suivant);
  return nouveau;
}

/** Saisie avec son unité à droite (« 100 ml »). */
export const avecUnite = (controle, unite) => h('span', { class: 'avec-unite' }, controle, h('span', { class: 'unite' }, unite));

export function effacerErreurs(racine) {
  racine.querySelectorAll('[aria-invalid="true"]').forEach((el) => el.removeAttribute('aria-invalid'));
  racine.querySelectorAll('.erreur-champ').forEach((el) => { el.hidden = true; el.textContent = ''; });
}

/** Dès que Maud corrige un champ en erreur, son message disparaît. */
function effacerAuChangement(racine) {
  if (racine.dataset.effacementBranche) return;
  racine.dataset.effacementBranche = '1';
  const effacer = (evenement) => {
    const bloc = evenement.target.closest('[data-champ]');
    if (!bloc) return;
    bloc.querySelectorAll('[aria-invalid="true"]').forEach((el) => el.removeAttribute('aria-invalid'));
    bloc.querySelectorAll('.erreur-champ').forEach((el) => { el.hidden = true; });
  };
  racine.addEventListener('input', effacer);
  racine.addEventListener('change', effacer);
}

/** Place les erreurs de l'API sous les champs ; renvoie les messages qui n'ont pas trouvé de champ. */
export function afficherErreurs(racine, erreur) {
  effacerErreurs(racine);
  effacerAuChangement(racine);
  const restants = [];
  for (const [nom, message] of Object.entries(erreur.details ?? {})) {
    const bloc = racine.querySelector(`[data-champ="${CSS.escape(nom)}"]`);
    if (!bloc || typeof message !== 'string') { if (typeof message === 'string') restants.push(message); continue; }
    const controle = bloc.querySelector('input, select, textarea');
    const zone = bloc.querySelector('.erreur-champ');
    controle?.setAttribute('aria-invalid', 'true');
    controle?.setAttribute('aria-describedby', zone.id);
    zone.textContent = message;
    zone.hidden = false;
  }
  const premier = racine.querySelector('[aria-invalid="true"]');
  premier?.focus();
  return premier ? restants : [erreur.message, ...restants];
}

/** Lit un nombre saisi (« 12,5 » accepté) ; vide → null ; texte invalide renvoyé tel quel pour que l'API le signale. */
export function lireNombre(controle) {
  const brut = controle.value.trim().replace(',', '.');
  if (brut === '') return null;
  const nombre = Number(brut);
  return Number.isFinite(nombre) ? nombre : controle.value;
}

/** Saisie numérique qui accepte la virgule (type=number la refuse selon les navigateurs). */
export const saisieNombre = (attributs = {}) => h('input', { class: 'saisie', type: 'text', inputmode: 'decimal', autocomplete: 'off', ...attributs });
