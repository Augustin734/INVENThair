// Fenêtre « Nouveau produit » (US1) et « Modifier » (US3).
import {
  afficherErreurs, annoncer, annoncerErreur, api, avecUnite, champ, couleurCss, effacerErreurs, envelopper, ErreurApi, h, lireNombre,
  ouvrirFenetre, parNom, pastilleStatut, quantiteFr, remplir, saisieNombre, uniteFr,
} from '../commun.js';
import { selecteurCouleur } from '../selecteur_couleur.js';

const NOUVELLE = '__nouvelle';
const NOUVEAU = '__nouveau';
const UNITES = [['piece', 'pièce'], ['ml', 'ml'], ['g', 'g'], ['flacon', 'flacon']];
const PIVOINE = { r: 176, g: 16, b: 80, a: 1 };

/**
 * `produit` absent : création. `surEnregistre(produit)` après succès.
 * `surMouvement(produit)` : lien « Réception / sortie » du mode modification.
 */
export async function ouvrirFenetreProduit({ produit = null, surEnregistre, surMouvement } = {}) {
  let categories;
  let fournisseurs;
  try {
    [categories, fournisseurs] = await Promise.all([api('GET', '/categories'), api('GET', '/fournisseurs')]);
  } catch (erreur) {
    annoncerErreur(erreur);
    return;
  }
  const creation = produit === null;
  const fenetre = ouvrirFenetre({
    titre: creation ? 'Nouveau produit' : `Modifier « ${produit.nom} »`,
    rubrique: creation ? 'Exclu' : 'Retouche',
    description: 'Les champs marqués * sont obligatoires.',
  });

  const c = {
    nom: h('input', { class: 'saisie', type: 'text', value: produit?.nom ?? '', autocomplete: 'off' }),
    reference: h('input', { class: 'saisie', type: 'text', value: produit?.reference ?? '', autocomplete: 'off' }),
    prix_unitaire: saisieNombre({ value: produit?.prix_unitaire ?? '' }),
    categorie_id: h('select', { class: 'saisie' }),
    fournisseur_id: h('select', { class: 'saisie' }),
    stock_initial: saisieNombre({ value: '' }),
    qte_reappro: saisieNombre({ value: produit?.qte_reappro ?? '' }),
    seuil_alerte: saisieNombre({ value: produit?.seuil_alerte ?? '' }),
  };
  const unitesAffichees = [];
  const avecU = (controle) => {
    const el = avecUnite(controle, '');
    unitesAffichees.push(el.querySelector('.unite'));
    return el;
  };

  // --- Unité ---
  const radiosUnite = UNITES.map(([valeur, libelle]) =>
    h('label', {}, h('input', { type: 'radio', name: 'unite', value: valeur, checked: (produit?.unite ?? 'piece') === valeur, onchange: majUnites }), libelle));
  const uniteChoisie = () => radiosUnite.map((l) => l.querySelector('input')).find((i) => i.checked)?.value;
  function majUnites() {
    const unite = uniteChoisie();
    for (const el of unitesAffichees) el.textContent = uniteFr(unite, 2);
    aidePrix.textContent = `${unite === 'piece' ? "Prix d'une pièce" : unite === 'flacon' ? "Prix d'un flacon" : `Prix pour 1 ${unite}`}, facultatif.`;
  }
  const aidePrix = h('p', { class: 'aide' });

  // --- Catégorie, avec création sur place ---
  const saisieNouvelleCat = h('input', { class: 'saisie', type: 'text', autocomplete: 'off', 'aria-label': 'Nom de la nouvelle catégorie' });
  let couleurNouvelleCat = { ...PIVOINE };
  const pastilleCouleur = h('span', { class: 'damier rond-couleur', 'aria-hidden': 'true' }, h('span'));
  const zoneSelecteur = h('div');
  const erreurNouvelleCat = h('p', { class: 'erreur-champ', role: 'alert', hidden: true });
  const blocNouvelleCat = h('div', { class: 'encadre large', role: 'group', 'aria-label': 'Nouvelle catégorie', hidden: true },
    h('span', { class: 'rubrique', style: { color: 'var(--prune)' } }, 'Nouvelle catégorie'),
    h('div', { class: 'ligne' },
      saisieNouvelleCat,
      h('button', { type: 'button', class: 'btn btn-discret btn-encre', onclick: basculerSelecteur }, pastilleCouleur, 'Couleur…'),
      h('button', { type: 'button', class: 'btn btn-primaire', onclick: creerCategorie }, 'Créer')),
    erreurNouvelleCat,
    zoneSelecteur,
    h('p', { class: 'aide', style: { color: 'var(--prune)' } }, 'Elle sera sélectionnée tout de suite. Tu pourras la ranger plus tard dans « Mes catégories ».'));

  function majPastilleCouleur() { pastilleCouleur.firstChild.style.background = couleurCss(couleurNouvelleCat); }
  majPastilleCouleur();
  function basculerSelecteur() {
    if (zoneSelecteur.childElementCount) return remplir(zoneSelecteur);
    remplir(zoneSelecteur, selecteurCouleur({
      nom: saisieNouvelleCat.value.trim() || 'Nouvelle catégorie',
      couleur: couleurNouvelleCat,
      surAnnuler: () => remplir(zoneSelecteur),
      surAppliquer: (couleur) => { couleurNouvelleCat = couleur; majPastilleCouleur(); remplir(zoneSelecteur); },
    }));
  }
  function remplirCategories(idChoisi) {
    remplir(c.categorie_id,
      h('option', { value: '' }, '— Choisis —'),
      [...categories].sort((a, b) => a.ordre - b.ordre).map((cat) => h('option', { value: cat.id, selected: cat.id === idChoisi }, cat.nom)),
      h('option', { value: NOUVELLE }, '+ Nouvelle catégorie…'));
  }
  async function creerCategorie() {
    erreurNouvelleCat.hidden = true;
    try {
      const cat = await api('POST', '/categories', { nom: saisieNouvelleCat.value, couleur: couleurNouvelleCat });
      categories.push(cat);
      remplirCategories(cat.id);
      blocNouvelleCat.hidden = true;
      saisieNouvelleCat.value = '';
      annoncer(`Catégorie « ${cat.nom} » créée.`);
      c.categorie_id.focus();
    } catch (erreur) {
      if (!(erreur instanceof ErreurApi)) throw erreur;
      erreurNouvelleCat.textContent = erreur.details.nom ?? erreur.message;
      erreurNouvelleCat.hidden = false;
    }
  }

  // --- Fournisseur, avec création sur place ---
  const saisieNouveauFour = h('input', { class: 'saisie', type: 'text', autocomplete: 'off', 'aria-label': 'Nom du nouveau fournisseur' });
  const saisieMailFour = h('input', { class: 'saisie', type: 'email', autocomplete: 'off', placeholder: 'mail (facultatif)', 'aria-label': 'Mail du nouveau fournisseur' });
  const erreurNouveauFour = h('p', { class: 'erreur-champ', role: 'alert', hidden: true });
  const blocNouveauFour = h('div', { class: 'encadre large', role: 'group', 'aria-label': 'Nouveau fournisseur', hidden: true },
    h('span', { class: 'rubrique', style: { color: 'var(--prune)' } }, 'Nouveau fournisseur'),
    h('div', { class: 'ligne' }, saisieNouveauFour, saisieMailFour, h('button', { type: 'button', class: 'btn btn-primaire', onclick: creerFournisseur }, 'Créer')),
    erreurNouveauFour);
  function remplirFournisseurs(idChoisi) {
    remplir(c.fournisseur_id,
      h('option', { value: '' }, 'Aucun'),
      [...fournisseurs].sort(parNom).map((f) => h('option', { value: f.id, selected: f.id === idChoisi }, f.nom)),
      h('option', { value: NOUVEAU }, '+ Nouveau fournisseur…'));
  }
  async function creerFournisseur() {
    erreurNouveauFour.hidden = true;
    try {
      const f = await api('POST', '/fournisseurs', { nom: saisieNouveauFour.value, email: saisieMailFour.value });
      fournisseurs.push(f);
      remplirFournisseurs(f.id);
      blocNouveauFour.hidden = true;
      saisieNouveauFour.value = '';
      saisieMailFour.value = '';
      annoncer(`Fournisseur « ${f.nom} » ajouté.`);
      c.fournisseur_id.focus();
    } catch (erreur) {
      if (!(erreur instanceof ErreurApi)) throw erreur;
      erreurNouveauFour.textContent = Object.values(erreur.details)[0] ?? erreur.message;
      erreurNouveauFour.hidden = false;
    }
  }

  c.categorie_id.addEventListener('change', () => {
    blocNouvelleCat.hidden = c.categorie_id.value !== NOUVELLE;
    if (!blocNouvelleCat.hidden) saisieNouvelleCat.focus();
  });
  c.fournisseur_id.addEventListener('change', () => {
    blocNouveauFour.hidden = c.fournisseur_id.value !== NOUVEAU;
    if (!blocNouveauFour.hidden) saisieNouveauFour.focus();
  });
  remplirCategories(produit?.categorie_id);
  remplirFournisseurs(produit?.fournisseur_id);

  // --- Stock : saisi à la création, en lecture seule ensuite ---
  const blocStock = creation
    ? champ({ nom: 'stock_initial', libelle: 'Stock de départ', controle: c.stock_initial, aide: 'Crée une entrée « Stock initial » dans l\'historique.', classe: '' })
    : h('div', { class: 'champ' },
      h('span', { class: 'etiquette' }, 'Stock actuel'),
      h('span', { class: 'avec-unite' }, h('strong', { class: 'stock-lecture' }, quantiteFr(produit.stock_actuel, produit.unite)), pastilleStatut(produit.statut)),
      h('p', { class: 'aide' }, 'Le stock bouge seulement par une réception, une sortie ou un inventaire. ',
        surMouvement && h('button', { type: 'button', class: 'btn-lien', onclick: () => { fenetre.fermer(); surMouvement(produit); } }, 'Enregistrer une réception / sortie')));
  if (creation) {
    envelopper(blocStock.querySelector('input'), avecU);
  }

  const erreurGenerale = h('p', { class: 'msg msg-erreur large', role: 'alert', hidden: true });
  const formulaire = h('form', { class: 'grille-form', novalidate: true, onsubmit: enregistrer },
    erreurGenerale,
    champ({ nom: 'nom', libelle: 'Nom', obligatoire: true, controle: c.nom, classe: 'large' }),
    champ({ nom: 'reference', libelle: 'Référence', controle: c.reference }),
    h('div', { class: 'champ', 'data-champ': 'prix_unitaire' },
      h('label', { for: 'prix-unitaire' }, 'Prix unitaire (€)'), Object.assign(c.prix_unitaire, { id: 'prix-unitaire', name: 'prix_unitaire' }), aidePrix,
      h('p', { class: 'erreur-champ', id: 'prix-unitaire-erreur', hidden: true })),
    champ({ nom: 'categorie_id', libelle: 'Catégorie', obligatoire: true, controle: c.categorie_id }),
    champ({ nom: 'fournisseur_id', libelle: 'Fournisseur', controle: c.fournisseur_id }),
    blocNouvelleCat,
    blocNouveauFour,
    h('fieldset', { class: 'champ large', 'data-champ': 'unite' },
      h('legend', { class: 'etiquette' }, 'Unité', h('span', { class: 'obligatoire' }, ' *')),
      h('div', { class: 'choix' }, radiosUnite),
      h('p', { class: 'erreur-champ', id: 'unite-erreur', hidden: true })),
    blocStock,
    champ({ nom: 'qte_reappro', libelle: 'Quantité à racheter', obligatoire: true, controle: c.qte_reappro, aide: "Proposée dans la liste d'achat." }),
    champ({ nom: 'seuil_alerte', libelle: "Seuil d'alerte", obligatoire: true, controle: c.seuil_alerte, aide: '0 si tu ne veux jamais d\'alerte.' }));
  for (const nom of ['qte_reappro', 'seuil_alerte']) {
    envelopper(formulaire.querySelector(`[data-champ="${nom}"] input`), avecU);
  }
  majUnites();
  fenetre.corps.append(formulaire);

  const boutonValider = h('button', { type: 'button', class: 'btn btn-primaire' }, creation ? 'Ajouter le produit' : 'Enregistrer');
  boutonValider.addEventListener('click', () => formulaire.requestSubmit());
  remplir(fenetre.pied, h('button', { type: 'button', class: 'btn btn-discret', 'data-fermer': true }, 'Annuler'), boutonValider);
  setTimeout(() => c.nom.focus());

  async function enregistrer(evenement) {
    evenement.preventDefault();
    effacerErreurs(formulaire);
    erreurGenerale.hidden = true;
    const categorie = c.categorie_id.value;
    const fournisseur = c.fournisseur_id.value;
    if (categorie === NOUVELLE || fournisseur === NOUVEAU) {
      erreurGenerale.textContent = `Termine d'abord la création ${categorie === NOUVELLE ? 'de la catégorie' : 'du fournisseur'} (bouton « Créer »).`;
      erreurGenerale.hidden = false;
      return;
    }
    const vide = creation ? undefined : null; // création : champ omis → « Champ obligatoire »
    const corps = {
      nom: c.nom.value,
      reference: c.reference.value,
      categorie_id: categorie === '' ? vide : Number(categorie),
      fournisseur_id: fournisseur === '' ? null : Number(fournisseur),
      unite: uniteChoisie(),
      seuil_alerte: lireNombre(c.seuil_alerte) ?? vide,
      qte_reappro: lireNombre(c.qte_reappro) ?? vide,
      prix_unitaire: lireNombre(c.prix_unitaire),
    };
    if (creation) corps.stock_initial = lireNombre(c.stock_initial);
    boutonValider.disabled = true;
    try {
      const resultat = creation ? await api('POST', '/produits', corps) : await api('PATCH', `/produits/${produit.id}`, corps);
      fenetre.fermer();
      annoncer(creation ? `« ${resultat.nom} » est ajouté à tes produits.` : `« ${resultat.nom} » est à jour.`);
      surEnregistre?.(resultat);
    } catch (erreur) {
      if (!(erreur instanceof ErreurApi)) throw erreur;
      const restants = afficherErreurs(formulaire, erreur);
      erreurGenerale.textContent = restants.join(' ');
      erreurGenerale.hidden = restants.length === 0;
      if (!erreurGenerale.hidden) erreurGenerale.scrollIntoView({ block: 'nearest' });
    } finally {
      boutonValider.disabled = false;
    }
  }
}
