// Page Inventaire (US8–US10) : lancer, compter au fil de l'eau, récap et validation, anciens numéros.
import {
  $, annoncer, annoncerErreur, api, dateCourte, ErreurApi, h, heureFr, lireNombre,
  nombreFr, ouvrirFenetre, quantiteFr, remplir, saisieNombre, uniteFr,
} from './commun.js';

const conteneur = $('#inventaire');
const numeroConsulte = Number(new URLSearchParams(location.search).get('numero')) || null;
const STATUTS_INVENTAIRE = { brouillon: ['Brouillon', 'p-brouillon'], valide: ['Validé', 'p-valide'], annule: ['Annulé', 'p-annule'] };

const libelleEcart = (ecart) => {
  if (ecart === null) return h('span', { class: 'pastille p-acompter' }, 'À compter');
  if (ecart === 0) return h('span', { class: 'pastille p-ok' }, 'Pile poil !');
  return h('span', { class: `pastille ${ecart < 0 ? 'p-moins' : 'p-plus'}` }, `Écart ${ecart > 0 ? '+' : '−'}${nombreFr(Math.abs(ecart))}`);
};
const compter = (lignes) => ({
  moins: lignes.filter((l) => l.ecart !== null && l.ecart < 0).length,
  plus: lignes.filter((l) => l.ecart !== null && l.ecart > 0).length,
  pile: lignes.filter((l) => l.ecart === 0).length,
  restantes: lignes.filter((l) => l.ecart === null).length,
});
const pluriel = (n, mot) => `${n} ${mot}${n > 1 ? 's' : ''}`;

// ---------- Aucun inventaire en cours ----------

function rendreAccueil(inventaires, nbProduits) {
  const dernier = inventaires.find((i) => i.statut === 'valide');
  const prochain = Math.max(0, ...inventaires.map((i) => i.id)) + 1;
  const bouton = h('button', { type: 'button', class: 'btn btn-primaire', onclick: lancer }, `Lancer l'inventaire N°${prochain}`);

  async function lancer() {
    bouton.disabled = true;
    try {
      await api('POST', '/inventaires');
      annoncer(`Inventaire N°${prochain} lancé : à toi de compter !`);
      await charger();
    } catch (erreur) {
      annoncerErreur(erreur);
      bouton.disabled = false;
    }
  }

  return [
    h('section', { class: 'carte carte-soleil carte-ombre lancer', 'aria-labelledby': 'titre-lancer' },
      h('div', { class: 'lancer-texte' },
        h('span', { class: 'rubrique-italique' }, 'Enquête'),
        h('h1', { id: 'titre-lancer' }, 'Prête pour le grand comptage ?'),
        h('p', {}, `On note le stock théorique de tes ${pluriel(nbProduits, 'produit')} actif${nbProduits > 1 ? 's' : ''}. Tu comptes à ton rythme : chaque ligne est sauvegardée dès que tu la remplis, tu peux t'arrêter et reprendre plus tard.`),
        h('div', { class: 'ligne' }, bouton,
          h('span', { style: { fontWeight: 800, color: 'var(--prune)' } }, dernier ? `Dernier inventaire : ${dateCourte(dernier.valide_le)}` : 'Ce sera ton premier inventaire.'))),
      h('div', { class: 'burst sticker-lancer', role: 'img', 'aria-label': `${pluriel(nbProduits, 'produit')} à compter` },
        h('span', { class: 'chiffre' }, nbProduits),
        h('span', {}, nbProduits > 1 ? 'produits' : 'produit', h('br'), 'à compter'))),
    h('section', { class: 'carte', 'aria-labelledby': 'titre-numeros' },
      h('h2', { id: 'titre-numeros', class: 'titre-section' }, 'Les anciens numéros'),
      inventaires.length === 0
        ? h('p', { class: 'vide' }, 'Aucun inventaire pour le moment.')
        : h('ul', { class: 'numeros' }, inventaires.map((i) => {
          const [libelle, classe] = STATUTS_INVENTAIRE[i.statut];
          const quand = i.statut === 'valide'
            ? `Validé le ${dateCourte(i.valide_le)} à ${heureFr(i.valide_le)}`
            : `Ouvert le ${dateCourte(i.cree_le)}${i.statut === 'annule' ? ', puis annulé' : ''}`;
          const ajustements = i.statut === 'valide' ? pluriel(i.nb_ecarts, 'ajustement') : 'aucun ajustement';
          return h('li', {},
            h('span', { class: 'num' }, `N°${i.id}`),
            h('span', { class: 'quand' }, quand),
            h('span', { class: `pastille ${classe}` }, libelle),
            h('span', { class: 'chiffres' }, `${pluriel(i.nb_lignes, 'produit')} · ${ajustements}`),
            h('a', { class: 'btn btn-discret btn-petit', href: `/inventaire?numero=${i.id}`, 'aria-label': `Voir le détail de l'inventaire N°${i.id}` }, 'Voir le détail'));
        }))),
  ];
}

// ---------- Lignes (brouillon ou lecture seule) ----------

function rendreInventaire(inventaire) {
  const lectureSeule = inventaire.statut !== 'brouillon';
  const lignes = inventaire.lignes.map((l) => ({ ...l }));
  const progression = h('div', { class: 'progression' });
  const resultats = h('section', { class: 'resultats', 'aria-label': 'Résultats' });
  const zonePied = h('div');

  function majSynthese() {
    const n = compter(lignes);
    const comptees = lignes.length - n.restantes;
    const pourcentage = lignes.length ? Math.round((comptees / lignes.length) * 100) : 100;
    remplir(progression,
      h('div', { class: 'ligne', style: { justifyContent: 'space-between', fontWeight: 900 } },
        h('span', {}, 'Progression'), h('span', { style: { color: 'var(--pivoine)' } }, `${comptees} / ${lignes.length} comptés`)),
      h('div', { class: 'barre', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': lignes.length, 'aria-valuenow': comptees, 'aria-label': 'Produits comptés' },
        h('div', { style: { width: `${pourcentage}%` } })),
      h('span', { class: 'texte-doux' }, lectureSeule && inventaire.valide_le
        ? `Validé le ${dateCourte(inventaire.valide_le)} à ${heureFr(inventaire.valide_le)}`
        : `Ouvert le ${dateCourte(inventaire.cree_le)} à ${heureFr(inventaire.cree_le)}`));
    remplir(resultats,
      h('div', { class: 'blob', style: { background: 'var(--mauve)' } },
        h('span', { class: 'titre' }, 'Plutôt moins :'), h('span', { class: 'chiffres' }, `${n.moins} ${n.moins > 1 ? 'écarts négatifs' : 'écart négatif'}`),
        h('span', {}, 'Des produits ont filé en douce. Ajustement à la baisse.')),
      h('div', { class: 'blob', style: { background: 'var(--asperge)', color: 'var(--encre)' } },
        h('span', { class: 'titre' }, 'Plutôt plus :'), h('span', { class: 'chiffres', style: { color: 'var(--encre)' } }, `${n.plus} ${n.plus > 1 ? 'écarts positifs' : 'écart positif'}`),
        h('span', {}, 'Tu en avais plus que prévu. Ajustement à la hausse.')),
      h('div', { class: 'blob', style: { background: 'var(--pivoine)' } },
        h('span', { class: 'titre' }, 'Pile poil :'), h('span', { class: 'chiffres' }, `${n.pile} sans écart`),
        h('span', {}, 'Rien à corriger, bravo la gestion !')));
    if (!lectureSeule) rendrePied(n.restantes);
  }

  function ligneInventaire(l, index) {
    const ecart = h('span', { class: 'ecart' }, libelleEcart(l.ecart));
    const theorique = h('span', {}, `Théorique : ${nombreFr(l.qte_theorique)}`);
    let compte;
    if (lectureSeule) {
      compte = h('span', { class: 'etiquette-c' }, h('span', { class: 'rond rond-c', 'aria-hidden': 'true' }, 'C'), `Compté : ${l.qte_comptee === null ? '—' : nombreFr(l.qte_comptee)}`);
    } else {
      const saisie = saisieNombre({ value: l.qte_comptee ?? '', placeholder: '?', class: `saisie saisie-compte${l.qte_comptee === null ? ' a-compter' : ''}`, 'data-index': index });
      const erreur = h('p', { class: 'erreur-champ', hidden: true });
      saisie.addEventListener('change', () => enregistrer(l, saisie, ecart, theorique, erreur));
      saisie.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        saisie.dispatchEvent(new Event('change'));
        conteneur.querySelector(`[data-index="${index + 1}"]`)?.focus();
      });
      compte = h('div', { class: 'pile', style: { gap: '4px' } },
        h('label', { class: 'etiquette-c' }, h('span', { class: 'rond rond-c', 'aria-hidden': 'true' }, 'C'), 'Compté', h('span', { class: 'sr' }, ` (${l.produit_nom}, en ${uniteFr(l.unite, 2)})`), saisie),
        erreur);
    }
    return h('li', { class: 'ligne-inventaire' },
      h('div', { class: 'titre-ligne' },
        h('span', { class: 'num' }, `${index + 1}.`),
        h('span', { class: 'nom' }, l.produit_nom),
        h('span', { class: 'texte-doux' }, `en ${uniteFr(l.unite, 2)}`)),
      h('div', { class: 'ligne' },
        h('span', { class: 'etiquette-c' }, h('span', { class: 'rond rond-t', 'aria-hidden': 'true' }, 'T'), theorique),
        compte,
        ecart));
  }

  async function enregistrer(l, saisie, ecart, theorique, erreur) {
    const valeur = lireNombre(saisie);
    if (valeur === l.qte_comptee) return;
    erreur.hidden = true;
    saisie.removeAttribute('aria-invalid');
    try {
      const maj = await api('PATCH', `/inventaires/${inventaire.id}/lignes/${l.id}`, { qte_comptee: valeur });
      Object.assign(l, maj);
      saisie.classList.toggle('a-compter', maj.qte_comptee === null);
      remplir(ecart, libelleEcart(maj.ecart));
      theorique.textContent = `Théorique : ${nombreFr(maj.qte_theorique)}`;
      majSynthese();
    } catch (e) {
      if (!(e instanceof ErreurApi)) throw e;
      erreur.textContent = e.details.qte_comptee ?? e.message;
      erreur.hidden = false;
      saisie.setAttribute('aria-invalid', 'true');
    }
  }

  function rendrePied(restantes) {
    const garder = h('input', { type: 'checkbox', id: 'garder-theorique' });
    remplir(zonePied, h('section', { class: 'pied-inventaire' },
      restantes > 0
        ? h('label', { class: 'case' }, garder, `Garder la quantité théorique pour ${restantes > 1 ? `les ${restantes} produits pas encore comptés` : 'le produit pas encore compté'}`)
        : h('span', { class: 'case' }, 'Tout est compté, bravo !'),
      h('div', { class: 'ligne' },
        h('button', { type: 'button', class: 'btn btn-discret', onclick: confirmerAnnulation }, "Annuler l'inventaire"),
        h('button', { type: 'button', class: 'btn btn-primaire', onclick: () => ouvrirRecap(garder.checked) }, 'Voir le récap et valider'))));
  }

  function confirmerAnnulation() {
    const nb = lignes.length - compter(lignes).restantes;
    const fenetre = ouvrirFenetre({
      titre: `On oublie l'inventaire N°${inventaire.id} ?`,
      description: `${nb === 0 ? 'Aucun comptage' : nb > 1 ? `Tes ${nb} comptages seront perdus` : 'Ton comptage sera perdu'}. Le stock ne bouge pas.`,
      etroite: true,
    });
    fenetre.dialog.setAttribute('role', 'alertdialog');
    remplir(fenetre.pied,
      h('button', { type: 'button', class: 'btn btn-discret', 'data-fermer': true }, 'Non, je continue'),
      h('button', {
        type: 'button', class: 'btn btn-primaire',
        onclick: async () => {
          try {
            await api('POST', `/inventaires/${inventaire.id}/annuler`);
            fenetre.fermer();
            annoncer(`Inventaire N°${inventaire.id} annulé. Le stock n'a pas bougé.`);
            await charger();
          } catch (erreur) {
            annoncerErreur(erreur);
          }
        },
      }, "Oui, annuler l'inventaire"));
  }

  function ouvrirRecap(garderInitial) {
    const n = compter(lignes);
    const fenetre = ouvrirFenetre({
      titre: `On valide l'inventaire N°${inventaire.id} ?`,
      rubrique: 'Le récap',
      description: "Vérifie les écarts : une fois validé, l'inventaire est verrouillé.",
    });
    const garder = h('input', { type: 'checkbox', checked: garderInitial });
    const avecEcart = lignes.filter((l) => l.ecart !== null && l.ecart !== 0);
    const erreur = h('div', { class: 'msg msg-erreur', role: 'alert', hidden: true });
    const bloquage = h('p', { class: 'msg msg-erreur', role: 'alert' }, `Il reste ${pluriel(n.restantes, 'produit')} à compter. Compte-les ou coche « Garder la quantité théorique ».`);
    const valider = h('button', { type: 'button', class: 'btn btn-primaire' }, 'Valider et ajuster le stock');
    const majBloquage = () => {
      bloquage.hidden = n.restantes === 0 || garder.checked;
      valider.disabled = !bloquage.hidden;
    };
    garder.addEventListener('change', majBloquage);

    fenetre.corps.append(
      h('div', { class: 'compteurs' },
        h('div', { class: 'compteur', style: { background: 'var(--pivoine)', color: 'var(--blanc)' } }, h('span', { class: 'chiffre' }, n.moins), h('span', {}, 'en moins')),
        h('div', { class: 'compteur', style: { background: 'var(--asperge)', color: 'var(--encre)' } }, h('span', { class: 'chiffre' }, n.plus), h('span', {}, 'en plus')),
        h('div', { class: 'compteur', style: { background: 'var(--sapin)', color: 'var(--blanc)' } }, h('span', { class: 'chiffre' }, n.pile), h('span', {}, 'pile poil')),
        h('div', { class: 'compteur compteur-vide' }, h('span', { class: 'chiffre' }, n.restantes), h('span', {}, 'pas comptés'))),
      avecEcart.length === 0
        ? h('p', { class: 'vide' }, 'Aucun écart : le stock ne bougera pas.')
        : h('div', { class: 'tableau-defile cadre-ecarts' },
          h('table', { class: 'tableau ecarts' },
            h('caption', { class: 'sr' }, `Les ${avecEcart.length} ajustements qui seront créés`),
            h('thead', {}, h('tr', {}, ['Produit', 'Théorique', 'Compté', 'Écart'].map((t, i) => h('th', { scope: 'col', class: i ? 'nombre' : '' }, t)))),
            h('tbody', {}, avecEcart.map((l) => h('tr', {},
              h('td', { style: { fontWeight: 900 } }, l.produit_nom),
              h('td', { class: 'nombre' }, quantiteFr(l.qte_theorique, l.unite)),
              h('td', { class: 'nombre' }, quantiteFr(l.qte_comptee, l.unite)),
              h('td', { class: 'nombre' }, libelleEcart(l.ecart))))))),
      n.restantes > 0 && h('label', { class: 'case' }, garder, `Garder la quantité théorique pour ${pluriel(n.restantes, 'produit')} pas encore compté${n.restantes > 1 ? 's' : ''} (aucun ajustement pour eux)`),
      avecEcart.length > 0 && h('p', { class: 'msg msg-info' }, `${pluriel(avecEcart.length, 'ajustement')} ${avecEcart.length > 1 ? 'vont être ajoutés' : 'va être ajouté'} à l'historique des produits, avec le motif « Inventaire N°${inventaire.id} ».`),
      n.restantes > 0 && bloquage,
      erreur);
    majBloquage();

    valider.addEventListener('click', async () => {
      valider.disabled = true;
      erreur.hidden = true;
      try {
        await api('POST', `/inventaires/${inventaire.id}/valider`, { garder_theorique_si_vide: garder.checked });
        fenetre.fermer();
        annoncer(`Inventaire N°${inventaire.id} validé : ${pluriel(avecEcart.length, 'produit')} ajusté${avecEcart.length > 1 ? 's' : ''}. Ton stock est à jour !`);
        await charger();
      } catch (e) {
        if (!(e instanceof ErreurApi)) throw e;
        const fautives = e.details.lignes?.map((x) => x.produit_nom) ?? e.details.produits ?? [];
        remplir(erreur, h('p', { style: { margin: 0 } }, e.message), fautives.length > 0 && h('ul', {}, fautives.map((nom) => h('li', {}, nom))));
        erreur.hidden = false;
        valider.disabled = false;
      }
    });
    remplir(fenetre.pied, h('button', { type: 'button', class: 'btn btn-discret gauche', 'data-fermer': true }, 'Je reprends le comptage'), valider);
  }

  const [libelleStatut] = STATUTS_INVENTAIRE[inventaire.statut];
  const elements = [
    lectureSeule && h('a', { class: 'retour', href: '/inventaire' }, '← Tous les inventaires'),
    h('section', { class: 'carte entete-inventaire' },
      h('div', { class: 'pile', style: { flex: '1 1 480px', gap: '8px' } },
        h('span', { class: 'pastille p-brouillon etiquette-numero' }, `Inventaire N°${inventaire.id} · ${libelleStatut.toLowerCase()}`),
        h('h1', {}, lectureSeule ? `Inventaire N°${inventaire.id}` : "Combien il t'en reste ?"),
        h('p', {}, lectureSeule
          ? (inventaire.statut === 'valide' ? 'Consultation seule : les ajustements ont été appliqués au stock.' : 'Inventaire annulé : il n\'a rien changé au stock.')
          : "Compte chaque produit et note la quantité. L'écart se calcule tout seul et tout est sauvegardé au fil de l'eau.")),
      progression),
    lignes.length === 0
      ? h('p', { class: 'vide' }, 'Aucun produit dans cet inventaire.')
      : h('ol', { class: 'lignes-inventaire', 'aria-label': "Lignes d'inventaire" }, lignes.map(ligneInventaire)),
    resultats,
    zonePied,
  ];
  majSynthese();
  return elements;
}

// ---------- Chargement ----------

async function charger() {
  conteneur.setAttribute('aria-busy', 'true');
  try {
    if (numeroConsulte) {
      const inventaire = await api('GET', `/inventaires/${numeroConsulte}`);
      document.title = `Inventaire N°${inventaire.id} · INVENThair`;
      remplir(conteneur, rendreInventaire(inventaire));
      return;
    }
    const inventaires = await api('GET', '/inventaires');
    const brouillon = inventaires.find((i) => i.statut === 'brouillon');
    if (brouillon) {
      remplir(conteneur, rendreInventaire(await api('GET', `/inventaires/${brouillon.id}`)));
    } else {
      const produits = await api('GET', '/produits');
      remplir(conteneur, rendreAccueil(inventaires, produits.length));
    }
  } catch (erreur) {
    if (erreur instanceof ErreurApi && erreur.statut === 404) {
      remplir(conteneur, h('section', { class: 'carte' }, h('h1', { class: 'titre-section' }, 'Inventaire introuvable'),
        h('p', {}, h('a', { href: '/inventaire' }, 'Revenir aux inventaires'), '.')));
    } else {
      annoncerErreur(erreur);
    }
  } finally {
    conteneur.removeAttribute('aria-busy');
  }
}

charger();
