// Fenêtre « Réception / sortie » (US5, US6).
import {
  afficherErreurs, annoncer, annoncerErreur, api, champ, effacerErreurs, envelopper, ErreurApi, h, lireNombre, nombreFr,
  ouvrirFenetre, pastilleCategorie, pastilleStatut, quantiteFr, remplir, saisieNombre, statutDe, uniteFr, variationFr,
} from '../commun.js';

const MOTIFS = { entree: ['Réception commande', 'Cadeau fournisseur'], sortie: ['Utilisation', 'Perte', 'Casse'] };

/** `produitId` pré-sélectionne le produit (depuis la fiche). `surEnregistre(mouvement)` après succès. */
export async function ouvrirFenetreMouvement({ produitId = null, sens = 'entree', surEnregistre } = {}) {
  let produits;
  let categories;
  try {
    [produits, categories] = await Promise.all([api('GET', '/produits'), api('GET', '/categories')]);
  } catch (erreur) {
    annoncerErreur(erreur);
    return;
  }
  const categorieDe = new Map(categories.map((c) => [c.id, c]));

  // Libellés uniques pour la liste de suggestions (deux produits peuvent porter le même nom).
  const libelles = new Map();
  for (const p of produits) {
    let libelle = p.reference ? `${p.nom} (${p.reference})` : p.nom;
    if (libelles.has(libelle)) libelle = `${libelle} #${p.id}`;
    libelles.set(libelle, p);
  }
  const produitInitial = produits.find((p) => p.id === produitId) ?? null;
  const libelleDe = (p) => [...libelles].find(([, x]) => x === p)?.[0] ?? '';

  const fenetre = ouvrirFenetre({ titre: 'Réception / sortie', rubrique: 'Arrivage', description: 'Le stock est mis à jour dès que tu enregistres.', etroite: true });

  const saisieProduit = h('input', { class: 'saisie', type: 'search', list: 'mouvement-produits', autocomplete: 'off', value: produitInitial ? libelleDe(produitInitial) : '', placeholder: 'Tape le nom du produit…' });
  const suggestions = h('datalist', { id: 'mouvement-produits' }, [...libelles.keys()].map((l) => h('option', { value: l })));
  const carteProduit = h('div', { class: 'produit-choisi', hidden: true });

  const radio = (valeur, titre, detail) => h('label', { class: valeur },
    h('input', { type: 'radio', name: 'sens', value: valeur, checked: sens === valeur, onchange: maj }),
    h('span', { class: 'nom' }, titre), h('span', { class: 'detail' }, detail));
  const choixSens = h('div', { class: 'sens' }, radio('entree', 'Une entrée', 'Réception de commande, cadeau fournisseur…'), radio('sortie', 'Une sortie', 'Utilisation, perte, casse…'));

  const saisieQuantite = saisieNombre({ value: '' });
  const blocQuantite = champ({ nom: 'quantite', libelle: 'Quantité', controle: saisieQuantite });
  const uniteQuantite = h('span', { class: 'unite' });
  envelopper(saisieQuantite, (el) => h('span', { class: 'avec-unite' }, el, uniteQuantite));
  saisieQuantite.addEventListener('input', maj);

  const saisieMotif = h('input', { class: 'saisie', type: 'text', autocomplete: 'off' });
  const motifsRapides = h('div', { class: 'choix', role: 'group', 'aria-label': 'Motifs rapides' });
  saisieMotif.addEventListener('input', majMotifs);

  const apercu = h('div', { class: 'apercu', 'aria-live': 'polite' });
  const erreurGenerale = h('p', { class: 'msg msg-erreur', role: 'alert', hidden: true });

  const formulaire = h('form', { class: 'pile', style: { gap: '18px' }, novalidate: true, onsubmit: enregistrer },
    erreurGenerale,
    champ({ nom: 'produit_id', libelle: 'Produit', controle: saisieProduit }),
    suggestions,
    carteProduit,
    h('fieldset', { class: 'champ' }, h('legend', { class: 'etiquette' }, "C'est…"), choixSens),
    h('div', { class: 'ligne', style: { alignItems: 'flex-start', gap: '18px 24px' } },
      blocQuantite,
      h('div', { class: 'champ', style: { flex: '1 1 240px' }, 'data-champ': 'motif' },
        h('label', { for: 'mouvement-motif' }, 'Motif (facultatif)'),
        Object.assign(saisieMotif, { id: 'mouvement-motif', name: 'motif' }),
        motifsRapides,
        h('p', { class: 'erreur-champ', id: 'mouvement-motif-erreur', hidden: true }))),
    apercu);
  fenetre.corps.append(formulaire);
  const boutonValider = h('button', { type: 'button', class: 'btn btn-primaire', onclick: () => formulaire.requestSubmit() });
  remplir(fenetre.pied, h('button', { type: 'button', class: 'btn btn-discret', 'data-fermer': true }, 'Annuler'), boutonValider);
  saisieProduit.addEventListener('input', maj);

  const sensChoisi = () => choixSens.querySelector('input:checked').value;
  const produitChoisi = () => libelles.get(saisieProduit.value) ?? null;

  function majMotifs() {
    remplir(motifsRapides, MOTIFS[sensChoisi()].map((m) => {
      const actif = saisieMotif.value === m;
      return h('button', {
        type: 'button', class: `btn btn-discret btn-petit${actif ? ' actif' : ''}`, 'aria-pressed': String(actif),
        onclick: () => { saisieMotif.value = actif ? '' : m; majMotifs(); },
      }, m);
    }));
  }

  function maj() {
    const p = produitChoisi();
    const s = sensChoisi();
    boutonValider.textContent = s === 'entree' ? "Enregistrer l'entrée" : 'Enregistrer la sortie';
    majMotifs();
    carteProduit.hidden = !p;
    uniteQuantite.textContent = p ? uniteFr(p.unite, 2) : '';
    if (p) {
      const cat = categorieDe.get(p.categorie_id);
      remplir(carteProduit, cat && pastilleCategorie(cat), h('strong', {}, p.nom),
        h('span', { class: 'texte-doux' }, [p.reference && `Réf. ${p.reference}`, `en stock : ${quantiteFr(p.stock_actuel, p.unite)}`, `seuil ${quantiteFr(p.seuil_alerte, p.unite)}`].filter(Boolean).join(' · ')));
    }
    const quantite = lireNombre(saisieQuantite);
    if (!p || typeof quantite !== 'number' || quantite <= 0) {
      remplir(apercu, h('span', { class: 'rubrique', style: { color: 'var(--prune)' } }, 'Aperçu'),
        h('span', { class: 'texte-doux' }, p ? 'Indique une quantité.' : 'Choisis un produit.'));
      return;
    }
    const variation = s === 'entree' ? quantite : -quantite;
    const apres = Math.round((p.stock_actuel + variation) * 1000) / 1000;
    remplir(apercu,
      h('span', { class: 'rubrique', style: { color: 'var(--prune)' } }, 'Aperçu'),
      h('span', {}, h('span', { class: 'chiffre' }, nombreFr(p.stock_actuel)), ` ${uniteFr(p.unite, p.stock_actuel)} `, pastilleStatut(p.statut)),
      h('span', { 'aria-hidden': 'true', class: 'fleche' }, '→'), h('span', { class: 'sr' }, 'devient'),
      apres < 0
        ? h('span', { class: 'erreur-champ' }, `Impossible : il ne reste que ${quantiteFr(p.stock_actuel, p.unite)}.`)
        : h('span', {}, h('span', { class: 'chiffre' }, nombreFr(apres)), ` ${uniteFr(p.unite, apres)} `, pastilleStatut(statutDe(apres, p.seuil_alerte))));
  }

  async function enregistrer(evenement) {
    evenement.preventDefault();
    effacerErreurs(formulaire);
    erreurGenerale.hidden = true;
    const p = produitChoisi();
    if (!p) {
      afficherErreurs(formulaire, { details: { produit_id: saisieProduit.value ? 'Produit inconnu : choisis-le dans la liste.' : 'Choisis un produit.' } });
      return;
    }
    boutonValider.disabled = true;
    try {
      const m = await api('POST', '/mouvements', { produit_id: p.id, type: sensChoisi(), quantite: lireNombre(saisieQuantite), motif: saisieMotif.value });
      fenetre.fermer();
      annoncer(`C'est noté : ${variationFr(m.quantite, m.unite)} de ${m.produit_nom}. Stock : ${quantiteFr(p.stock_actuel + m.quantite, p.unite)}.`);
      surEnregistre?.(m);
    } catch (erreur) {
      if (!(erreur instanceof ErreurApi)) throw erreur;
      const restants = afficherErreurs(formulaire, erreur);
      erreurGenerale.textContent = restants.join(' ');
      erreurGenerale.hidden = restants.length === 0;
    } finally {
      boutonValider.disabled = false;
    }
  }

  maj();
  setTimeout(() => (produitInitial ? saisieQuantite : saisieProduit).focus());
}
