// Fiche produit (US7) : infos, stock, actions et historique des mouvements.
import {
  $, annoncerErreur, api, dateCourte, ErreurApi, h, nombreFr, pastilleCategorie, pastilleStatut, quantiteFr, remplir,
  TYPES_MOUVEMENT, uniteFr, variationFr,
} from './commun.js';
import { desarchiver, ouvrirFenetreArchiver } from './fenetres/archiver.js';
import { ouvrirFenetreMouvement } from './fenetres/mouvement.js';
import { ouvrirFenetreProduit } from './fenetres/produit.js';

const conteneur = $('#fiche');
const produitId = Number(conteneur.dataset.produitId);
const CLASSE_STICKER = { alerte: '', a_surveiller: 'surveiller', en_forme: 'forme' };

function prixFr(p) {
  if (p.prix_unitaire === null) return '—';
  const prix = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 3 }).format(p.prix_unitaire);
  return `${prix} / ${uniteFr(p.unite)}`;
}

function rendreFiche(p, categorie, fournisseur) {
  const actions = p.archive
    ? [h('button', { type: 'button', class: 'btn btn-primaire', onclick: () => desarchiver(p, charger) }, 'Désarchiver')]
    : [
      h('button', { type: 'button', class: 'btn btn-primaire', onclick: () => ouvrirFenetreMouvement({ produitId: p.id, surEnregistre: charger }) }, 'Réception / sortie'),
      h('button', { type: 'button', class: 'btn btn-secondaire', onclick: () => modifier(p) }, 'Modifier'),
      h('button', { type: 'button', class: 'btn btn-discret', onclick: () => ouvrirFenetreArchiver({ produit: p, surArchive: charger }) }, 'Archiver'),
    ];
  return h('section', { class: 'carte carte-ombre fiche', 'aria-labelledby': 'nom-produit' },
    h('div', { class: 'etoile', 'aria-hidden': 'true' }),
    h('div', { class: 'fiche-infos' },
      h('div', { class: 'ligne' },
        categorie && pastilleCategorie(categorie),
        p.archive ? h('span', { class: 'pastille p-annule' }, 'Archivé') : pastilleStatut(p.statut)),
      h('h1', { id: 'nom-produit' }, p.nom),
      p.archive && h('p', { class: 'msg msg-info' },
        `Archivé le ${dateCourte(p.archive_le)}`, p.archive_motif ? ` : « ${p.archive_motif} »` : '', '. Il ne compte plus dans les alertes, les inventaires ni la liste d\'achat.'),
      h('dl', { class: 'details' },
        [['Référence', p.reference ?? '—'], ['Fournisseur', fournisseur?.nom ?? '—'], ["Seuil d'alerte", quantiteFr(p.seuil_alerte, p.unite)],
          ['À racheter', quantiteFr(p.qte_reappro, p.unite)], ['Prix', prixFr(p)]]
          .map(([terme, valeur]) => h('div', {}, h('dt', {}, terme), h('dd', {}, valeur)))),
      h('div', { class: 'ligne', style: { marginTop: '6px' } }, actions)),
    h('div', { class: `burst sticker-stock ${p.archive ? 'surveiller' : CLASSE_STICKER[p.statut]}`, role: 'img', 'aria-label': `En stock : ${quantiteFr(p.stock_actuel, p.unite)}` },
      h('span', { style: { fontWeight: 900, fontSize: '14px', textTransform: 'uppercase', fontStyle: 'italic' } }, 'En stock'),
      h('span', { class: 'chiffre' }, nombreFr(p.stock_actuel)),
      h('span', { style: { fontWeight: 900, fontSize: '15px', textTransform: 'uppercase' } }, uniteFr(p.unite, p.stock_actuel))));
}

function rendreHistorique(p, mouvements) {
  // « Stock après » : on part du stock actuel et on remonte le temps.
  let stock = p.stock_actuel;
  const lignes = mouvements.map((m) => {
    const apres = stock;
    stock = Math.round((stock - m.quantite) * 1000) / 1000;
    const type = TYPES_MOUVEMENT[m.type];
    const sens = m.quantite > 0 ? 'qte-plus' : m.quantite < 0 ? 'qte-moins' : '';
    return h('li', {},
      h('span', { class: 'date' }, dateCourte(m.cree_le)),
      h('span', {}, h('span', { class: `pastille p-type ${type.classe}` }, type.libelle)),
      h('span', { class: 'motif' }, m.inventaire_id ? `Inventaire N°${m.inventaire_id}` : (m.motif ?? '—')),
      h('span', { class: `qte ${sens}` }, variationFr(m.quantite, m.unite)),
      h('span', { class: 'apres' }, quantiteFr(apres, p.unite)));
  });
  const nb = mouvements.length;
  return h('section', { class: 'carte', 'aria-labelledby': 'titre-histo' },
    h('div', { class: 'ligne', style: { justifyContent: 'space-between' } },
      h('h2', { id: 'titre-histo', class: 'titre-section' }, 'Son historique'),
      h('span', { class: 'texte-doux', style: { fontWeight: 800 } }, nb === 0 ? 'Aucun mouvement' : `${nb} mouvement${nb > 1 ? 's' : ''}, du plus récent au plus ancien`)),
    nb === 0
      ? h('p', { class: 'vide' }, "Pas encore de mouvement : enregistre une réception pour démarrer l'historique.")
      : h('ul', { class: 'historique' },
        h('li', { class: 'entete-liste', 'aria-hidden': 'true' },
          h('span', {}, 'Date'), h('span', {}, 'Type'), h('span', {}, 'Motif'), h('span', { style: { textAlign: 'right' } }, 'Quantité'), h('span', { style: { textAlign: 'right' } }, 'Stock après')),
        lignes));
}

function modifier(p) {
  ouvrirFenetreProduit({ produit: p, surEnregistre: charger, surMouvement: () => ouvrirFenetreMouvement({ produitId: p.id, surEnregistre: charger }) });
}

async function charger() {
  try {
    const [produit, mouvements, categories, fournisseurs] = await Promise.all([
      api('GET', `/produits/${produitId}`),
      api('GET', `/produits/${produitId}/mouvements`),
      api('GET', '/categories'),
      api('GET', '/fournisseurs'),
    ]);
    document.title = `${produit.nom} · INVENThair`;
    remplir(conteneur,
      rendreFiche(produit, categories.find((c) => c.id === produit.categorie_id), fournisseurs.find((f) => f.id === produit.fournisseur_id)),
      rendreHistorique(produit, mouvements));
  } catch (erreur) {
    if (erreur instanceof ErreurApi && erreur.statut === 404) {
      remplir(conteneur, h('section', { class: 'carte' },
        h('h1', { class: 'titre-section' }, 'Produit introuvable'),
        h('p', {}, "Ce produit n'existe pas ou plus. ", h('a', { href: '/produits' }, 'Revenir à la liste des produits'), '.')));
    } else {
      annoncerErreur(erreur);
    }
  } finally {
    conteneur.removeAttribute('aria-busy');
  }
}

charger();
