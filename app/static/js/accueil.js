// Accueil : alertes, sommaire, chiffres clés, derniers mouvements (US11, US7, US15).
import {
  $, api, annoncer, annoncerErreur, dateCourte, dateJourMois, dateLongue, h, lienProduit, quantiteFr, remplir, TYPES_MOUVEMENT, variationFr,
} from './commun.js';

const MAX_CARTES_ALERTE = 8;

function afficherAlertes(alertes) {
  const nb = alertes.length;
  $('#nb-alertes').textContent = nb;
  $('#nb-alertes-2').textContent = nb;
  $('#bloc-alertes').removeAttribute('aria-busy');

  if (nb === 0) {
    $('#sticker-alertes').classList.add('calme');
    remplir($('#libelle-alertes'), 'produit', h('br'), 'sous le seuil');
    $('#titre-alertes').textContent = 'Tout est en forme !';
    $('#texte-alertes').textContent = "Aucun produit sous son seuil. Ta liste d'achat peut attendre.";
    remplir($('#grille-alertes'));
    return;
  }
  remplir($('#libelle-alertes'), nb > 1 ? 'produits' : 'produit', h('br'), 'sous le seuil');
  const cartes = alertes.slice(0, MAX_CARTES_ALERTE).map((p) =>
    h('li', {},
      h('a', { class: 'carte-alerte', href: lienProduit(p.id) },
        h('span', {}, h('span', { class: 'nom' }, p.nom), h('br'), h('span', { class: 'seuil' }, `Seuil ${quantiteFr(p.seuil_alerte, p.unite)}`)),
        h('span', { class: 'pastille p-alerte' }, quantiteFr(p.stock_actuel, p.unite)))));
  if (nb > MAX_CARTES_ALERTE) {
    const reste = nb - MAX_CARTES_ALERTE;
    cartes.push(h('li', {}, h('a', { class: 'carte-alerte', href: '/produits?en_alerte=1' },
      h('span', { class: 'nom' }, `Et ${reste} autre${reste > 1 ? 's' : ''}…`), h('span', { 'aria-hidden': 'true' }, '→'))));
  }
  remplir($('#grille-alertes'), cartes);
}

function afficherChiffres(actifs, archives, inventaires) {
  $('#nb-actifs').textContent = actifs.length;
  $('#nb-archives').textContent = archives.length;
  const dernier = inventaires.find((i) => i.statut === 'valide');
  $('#dernier-inventaire').textContent = dernier ? dateJourMois(dernier.valide_le) : 'Jamais';

  const brouillon = inventaires.find((i) => i.statut === 'brouillon');
  $('#lien-inventaire').textContent = brouillon ? `Reprendre l'inventaire N°${brouillon.id}` : 'Lancer un inventaire';
}

function contexteMouvement(m) {
  const motif = m.inventaire_id ? `Inventaire N°${m.inventaire_id}` : m.motif;
  return [motif, dateCourte(m.cree_le)].filter(Boolean).join(' · ');
}

function afficherPotins(mouvements) {
  const liste = $('#potins');
  liste.removeAttribute('aria-busy');
  if (mouvements.length === 0) {
    remplir(liste, h('li', { class: 'vide' }, 'Rien à raconter pour le moment : ajoute un produit avec son stock de départ.'));
    return;
  }
  remplir(liste, mouvements.map((m) => {
    const type = TYPES_MOUVEMENT[m.type];
    const sens = m.quantite > 0 ? 'qte-plus' : m.quantite < 0 ? 'qte-moins' : '';
    return h('li', { class: 'potin' },
      h('span', { class: `pastille p-type ${type.classe}` }, type.libelle),
      h('a', { class: 'produit', href: lienProduit(m.produit_id) }, m.produit_nom),
      h('span', { class: `qte ${sens}` }, variationFr(m.quantite, m.unite)),
      h('span', { class: 'contexte' }, contexteMouvement(m)));
  }));
}

async function sauvegarder(evenement) {
  const bouton = evenement.currentTarget;
  bouton.disabled = true;
  try {
    const { fichier } = await api('POST', '/backup');
    annoncer(`Base sauvegardée : backups/${fichier}`);
  } catch (erreur) {
    annoncerErreur(erreur);
  } finally {
    bouton.disabled = false;
  }
}

async function demarrer() {
  $('#date-du-jour').textContent = dateLongue();
  $('#sauvegarder').addEventListener('click', sauvegarder);
  try {
    const [alertes, actifs, archives, inventaires, mouvements] = await Promise.all([
      api('GET', '/alertes'),
      api('GET', '/produits'),
      api('GET', '/produits?archive=true'),
      api('GET', '/inventaires'),
      api('GET', '/mouvements?limite=5'),
    ]);
    afficherAlertes(alertes);
    afficherChiffres(actifs, archives, inventaires);
    afficherPotins(mouvements);
  } catch (erreur) {
    annoncerErreur(erreur);
  }
}

demarrer();
