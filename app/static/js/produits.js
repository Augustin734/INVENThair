// Page Produits (US2, US3, US4) : liste filtrée, onglets Actifs / Archivés, fenêtres.
import {
  $, annoncerErreur, api, couleurCss, dateCourte, h, lienProduit, normaliser, pastilleCategorie, pastilleStatut, quantiteFr,
  remplir, STATUTS, texteSur,
} from './commun.js';
import { desarchiver, ouvrirFenetreArchiver } from './fenetres/archiver.js';
import { ouvrirCategories } from './fenetres/categories.js';
import { ouvrirFournisseurs } from './fenetres/fournisseurs.js';
import { ouvrirFenetreMouvement } from './fenetres/mouvement.js';
import { ouvrirFenetreProduit } from './fenetres/produit.js';

const parametres = new URLSearchParams(location.search);
const archives = parametres.get('onglet') === 'archives';
const etat = {
  actifs: [],
  archives: [],
  categories: [],
  fournisseurs: [],
  categorie: null,
  alerte: parametres.get('en_alerte') === '1',
  recherche: '',
};

const COLONNES_ACTIFS = ['Produit', 'Catégorie', 'Stock', 'Seuil', 'Fournisseur', 'Statut', 'Actions'];
const COLONNES_ARCHIVES = ['Produit', 'Catégorie', 'Stock restant', 'Archivé le', 'Pourquoi', 'Actions'];

async function charger() {
  try {
    [etat.actifs, etat.archives, etat.categories, etat.fournisseurs] = await Promise.all([
      api('GET', '/produits'),
      api('GET', '/produits?archive=true'),
      api('GET', '/categories'),
      api('GET', '/fournisseurs'),
    ]);
    if (etat.categorie !== null && !etat.categories.some((c) => c.id === etat.categorie)) etat.categorie = null;
    rendre();
  } catch (erreur) {
    annoncerErreur(erreur);
  }
}

function rendreEntete() {
  const nbAlertes = etat.actifs.filter((p) => p.en_alerte).length;
  $('#resume').textContent = `${etat.actifs.length} actif${etat.actifs.length > 1 ? 's' : ''} · ${nbAlertes} en alerte · ${etat.archives.length} archivé${etat.archives.length > 1 ? 's' : ''}`;
  $('#nb-actifs').textContent = etat.actifs.length;
  $('#nb-archives').textContent = etat.archives.length;
}

function rendreFiltres() {
  const filtreCategorie = (categorie) => {
    const actif = etat.categorie === (categorie?.id ?? null);
    const style = categorie ? { background: couleurCss(categorie.couleur), color: texteSur(categorie.couleur) } : undefined;
    return h('button', {
      type: 'button', class: `filtre${categorie ? '' : ' filtre-tout'}`, style, 'aria-pressed': String(actif),
      onclick: () => { etat.categorie = categorie?.id ?? null; rendre(); },
    }, h('span', { class: 'puce', 'aria-hidden': 'true' }), categorie ? categorie.nom : 'Tout');
  };
  remplir($('#filtres-categories'),
    filtreCategorie(null),
    etat.categories.map(filtreCategorie),
    !archives && h('button', {
      type: 'button', class: 'filtre filtre-alerte', 'aria-pressed': String(etat.alerte),
      onclick: () => { etat.alerte = !etat.alerte; rendre(); },
    }, 'En alerte seulement'),
    h('button', { type: 'button', class: 'btn btn-tirets-soleil', onclick: () => ouvrirCategories({ surChangement: charger }) }, 'Mes catégories'),
    h('button', { type: 'button', class: 'btn btn-tirets-soleil', onclick: () => ouvrirFournisseurs({ surChangement: charger }) }, 'Mes fournisseurs'));
}

function produitsAffiches() {
  const terme = normaliser(etat.recherche.trim());
  return (archives ? etat.archives : etat.actifs).filter((p) =>
    (etat.categorie === null || p.categorie_id === etat.categorie)
    && (!etat.alerte || archives || p.en_alerte)
    && (!terme || normaliser(`${p.nom} ${p.reference ?? ''}`).includes(terme)));
}

function celluleProduit(p) {
  return h('td', {}, h('a', { href: lienProduit(p.id) }, p.nom), h('span', { class: 'ref' }, p.reference ? `Réf. ${p.reference}` : 'Sans réf.'));
}

function ligneActif(p, categories, fournisseurs) {
  const categorie = categories.get(p.categorie_id);
  return h('tr', { class: p.en_alerte ? 'ligne-alerte' : '' },
    celluleProduit(p),
    h('td', {}, categorie && pastilleCategorie(categorie)),
    h('td', { class: `nombre ${STATUTS[p.statut].couleurTexte || 'qte-surveiller'}`, style: { fontWeight: 900 } }, quantiteFr(p.stock_actuel, p.unite)),
    h('td', { class: 'nombre' }, quantiteFr(p.seuil_alerte, p.unite)),
    h('td', {}, fournisseurs.get(p.fournisseur_id)?.nom ?? '—'),
    h('td', {}, pastilleStatut(p.statut)),
    h('td', { class: 'actions-ligne' },
      h('button', { type: 'button', class: 'btn btn-discret btn-petit', 'aria-label': `Modifier ${p.nom}`, onclick: () => modifier(p) }, 'Modifier'),
      ' ',
      h('button', { type: 'button', class: 'btn-lien', 'aria-label': `Archiver ${p.nom}`, onclick: () => ouvrirFenetreArchiver({ produit: p, surArchive: charger }) }, 'Archiver')));
}

function ligneArchive(p, categories) {
  const categorie = categories.get(p.categorie_id);
  return h('tr', {},
    celluleProduit(p),
    h('td', {}, categorie && pastilleCategorie(categorie)),
    h('td', { class: 'nombre', style: { fontWeight: 900 } }, quantiteFr(p.stock_actuel, p.unite)),
    h('td', {}, p.archive_le ? dateCourte(p.archive_le) : '—'),
    h('td', { class: p.archive_motif ? 'motif-archive' : 'texte-doux' }, p.archive_motif ?? '—'),
    h('td', { class: 'actions-ligne' },
      h('button', { type: 'button', class: 'btn btn-discret btn-petit', 'aria-label': `Désarchiver ${p.nom}`, onclick: () => desarchiver(p, charger) }, 'Désarchiver')));
}

function rendreTableau() {
  const colonnes = archives ? COLONNES_ARCHIVES : COLONNES_ACTIFS;
  remplir($('#tableau-tete'), h('tr', {}, colonnes.map((c) => h('th', { scope: 'col', class: ['Stock', 'Seuil', 'Stock restant'].includes(c) ? 'nombre' : c === 'Actions' ? 'actions-ligne' : '' }, c))));
  const categories = new Map(etat.categories.map((c) => [c.id, c]));
  const fournisseurs = new Map(etat.fournisseurs.map((f) => [f.id, f]));
  const liste = produitsAffiches();
  const total = (archives ? etat.archives : etat.actifs).length;
  const corps = $('#tableau-corps');
  corps.removeAttribute('aria-busy');

  if (liste.length === 0) {
    const message = total === 0
      ? (archives ? 'Aucun produit archivé.' : "Aucun produit pour l'instant : ajoute le premier avec « + Nouveau produit ».")
      : 'Aucun produit ne correspond à ces filtres.';
    remplir(corps, h('tr', { class: 'vide-ligne' }, h('td', { colspan: colonnes.length }, message)));
  } else {
    remplir(corps, liste.map((p) => (archives ? ligneArchive(p, categories) : ligneActif(p, categories, fournisseurs))));
  }
  $('#compte').textContent = `${liste.length} sur ${total} produit${total > 1 ? 's' : ''} ${archives ? 'archivé' : 'affiché'}${total > 1 ? 's' : ''}`;
}

function rendre() {
  rendreEntete();
  rendreFiltres();
  rendreTableau();
}

function modifier(produit) {
  ouvrirFenetreProduit({
    produit,
    surEnregistre: charger,
    surMouvement: (p) => ouvrirFenetreMouvement({ produitId: p.id, surEnregistre: charger }),
  });
}

function nouveau() {
  ouvrirFenetreProduit({ surEnregistre: charger });
}

function demarrer() {
  $(archives ? '#onglet-archives' : '#onglet-actifs').setAttribute('aria-current', 'page');
  const lien = $('#lien-autre-onglet');
  lien.href = archives ? '/produits' : '/produits?onglet=archives';
  lien.textContent = archives ? 'Revenir aux produits actifs' : 'Voir les archivés';
  if (archives) $('#libelle-recherche').textContent = 'Je cherche dans les archives…';

  $('#recherche').addEventListener('input', (e) => { etat.recherche = e.target.value; rendreTableau(); });
  $('#bouton-nouveau').addEventListener('click', nouveau);
  $('#bouton-mouvement').addEventListener('click', () => ouvrirFenetreMouvement({ surEnregistre: charger }));

  // Raccourcis depuis l'accueil : /produits#nouveau, /produits#mouvement.
  const raccourci = location.hash.slice(1);
  if (raccourci) history.replaceState(null, '', location.pathname + location.search);
  if (raccourci === 'nouveau') nouveau();
  if (raccourci === 'mouvement') ouvrirFenetreMouvement({ surEnregistre: charger });
  charger();
}

demarrer();
