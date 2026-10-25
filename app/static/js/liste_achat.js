// Liste d'achat (US12–US14) : quantités modifiables, lignes retirées ou ajoutées, export et envoi.
import {
  $, afficherErreurs, annoncer, annoncerErreur, api, dateLongue, effacerErreurs, ErreurApi, h, heureFr, lireNombre, normaliser,
  ouvrirFenetre, parNom, quantiteFr, remplir, saisieNombre, telecharger, uniteFr,
} from './commun.js';

const ICONE_RETIRER = () => {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [k, v] of Object.entries({ width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 3, 'stroke-linecap': 'round', 'aria-hidden': 'true' })) svg.setAttribute(k, v);
  const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  p.setAttribute('d', 'M6 6l12 12M18 6L6 18');
  svg.append(p);
  return svg;
};

let liste = { genere_le: null, fournisseurs: [] };
let fournisseurs = [];

const lignesACommander = () => liste.fournisseurs.flatMap((g) => g.lignes).filter((l) => typeof l.quantite === 'number' && l.quantite > 0);

function majCompteur() {
  const nb = lignesACommander().length;
  $('#nb-a-racheter').textContent = nb;
  $('#libelle-a-racheter').textContent = nb > 1 ? 'produits' : 'produit';
  $('#sticker-achat').setAttribute('aria-label', `À racheter : ${nb} produit${nb > 1 ? 's' : ''}`);
}

function rendre() {
  const zone = $('#groupes');
  zone.removeAttribute('aria-busy');
  const groupes = liste.fournisseurs.filter((g) => g.lignes.length > 0);
  const ajout = h('button', { type: 'button', class: 'btn btn-tirets', onclick: ajouterHorsAlerte }, '+ Ajouter un produit hors alerte');
  if (groupes.length === 0) {
    remplir(zone, h('section', { class: 'carte' },
      h('h2', { class: 'titre-section' }, 'Rien à racheter !'),
      h('p', {}, "Aucun produit n'est sous son seuil. Tu peux quand même préparer une commande en ajoutant des produits.")), ajout);
    majCompteur();
    return;
  }
  remplir(zone, liste.fournisseurs.map((groupe, gi) => groupe.lignes.length > 0 && h('section', { class: `groupe-achat${gi % 2 ? ' groupe-prune' : ''}`, 'aria-labelledby': `groupe-${gi}` },
    h('h2', { id: `groupe-${gi}`, class: 'onglet-groupe' }, groupe.fournisseur_id === null ? groupe.nom : `Chez ${groupe.nom}`),
    groupe.lignes.map((l, li) => {
      const saisie = saisieNombre({ value: l.quantite, id: `quantite-${gi}-${li}`, name: `fournisseurs.${gi}.lignes.${li}.quantite` });
      saisie.addEventListener('input', () => { l.quantite = lireNombre(saisie); majCompteur(); });
      return h('div', { class: 'ligne-achat', 'data-champ': `fournisseurs.${gi}.lignes.${li}.quantite` },
        h('span', { class: 'produit-achat' }, l.nom,
          h('span', { class: 'texte-doux' }, `Reste ${quantiteFr(l.stock_actuel, l.unite)} · seuil ${quantiteFr(l.seuil_alerte, l.unite)}`)),
        h('label', { class: 'avec-unite', for: saisie.id }, 'Quantité', saisie, h('span', {}, uniteFr(l.unite, 2))),
        h('button', {
          type: 'button', class: 'btn-rond', 'aria-label': `Retirer ${l.nom} de la liste`,
          onclick: () => { groupe.lignes.splice(li, 1); rendre(); $('#groupes button, #groupes input')?.focus(); },
        }, ICONE_RETIRER()),
        h('p', { class: 'erreur-champ', id: `quantite-${gi}-${li}-erreur`, hidden: true }));
    }))), ajout);
  majCompteur();
}

async function ajouterHorsAlerte() {
  let produits;
  try {
    produits = await api('GET', '/produits');
  } catch (erreur) {
    annoncerErreur(erreur);
    return;
  }
  const dejaLa = new Set(liste.fournisseurs.flatMap((g) => g.lignes.map((l) => l.produit_id)));
  const disponibles = produits.filter((p) => !dejaLa.has(p.id));
  const fenetre = ouvrirFenetre({ titre: 'Ajouter un produit', rubrique: 'Shopping', description: 'Choisis un produit à ajouter à ta commande.', etroite: true });
  const recherche = h('input', { class: 'saisie', type: 'search', id: 'recherche-ajout', autocomplete: 'off', placeholder: 'gel, capsules, lime…' });
  const resultats = h('ul', { class: 'liste-choix' });
  const afficher = () => {
    const terme = normaliser(recherche.value.trim());
    const choix = disponibles.filter((p) => !terme || normaliser(`${p.nom} ${p.reference ?? ''}`).includes(terme)).slice(0, 12);
    remplir(resultats, choix.length === 0
      ? h('li', { class: 'vide' }, disponibles.length ? 'Aucun produit ne correspond.' : 'Tous tes produits sont déjà dans la liste.')
      : choix.map((p) => h('li', {}, h('button', { type: 'button', class: 'choix-produit', onclick: () => { ajouter(p); fenetre.fermer(); } },
        h('strong', {}, p.nom), h('span', { class: 'texte-doux' }, `Reste ${quantiteFr(p.stock_actuel, p.unite)} · à racheter ${quantiteFr(p.qte_reappro, p.unite)}`)))));
  };
  recherche.addEventListener('input', afficher);
  fenetre.corps.append(h('div', { class: 'champ' }, h('label', { for: 'recherche-ajout' }, 'Je cherche…'), recherche), resultats);
  remplir(fenetre.pied, h('button', { type: 'button', class: 'btn btn-discret', 'data-fermer': true }, 'Fermer'));
  afficher();
  setTimeout(() => recherche.focus());
}

function ajouter(p) {
  const nomFournisseur = fournisseurs.find((f) => f.id === p.fournisseur_id)?.nom ?? 'Sans fournisseur';
  let groupe = liste.fournisseurs.find((g) => g.fournisseur_id === (p.fournisseur_id ?? null));
  if (!groupe) {
    groupe = { fournisseur_id: p.fournisseur_id ?? null, nom: nomFournisseur, lignes: [] };
    liste.fournisseurs.push(groupe);
    liste.fournisseurs.sort((a, b) => (a.fournisseur_id === null) - (b.fournisseur_id === null) || parNom(a, b));
  }
  groupe.lignes.push({ produit_id: p.id, nom: p.nom, unite: p.unite, stock_actuel: p.stock_actuel, seuil_alerte: p.seuil_alerte, quantite: p.qte_reappro });
  rendre();
  annoncer(`« ${p.nom} » ajouté à la liste.`);
}

/** Corps envoyé à l'API : la liste telle que Maud l'a retouchée. */
const corpsListe = () => ({ genere_le: liste.genere_le, fournisseurs: liste.fournisseurs });

function verifierAvantEnvoi() {
  effacerErreurs($('#groupes'));
  if (lignesACommander().length === 0) {
    annoncer('La liste est vide : ajoute un produit ou une quantité.', 'erreur');
    return false;
  }
  return true;
}

async function exporter(evenement) {
  const bouton = evenement.currentTarget;
  if (!verifierAvantEnvoi()) return;
  bouton.disabled = true;
  try {
    const reponse = await api('POST', `/liste-achat/export?format=${bouton.dataset.format}`, corpsListe());
    await telecharger(reponse, `liste-achat.${bouton.dataset.format}`);
  } catch (erreur) {
    if (erreur instanceof ErreurApi && erreur.code === 'VALIDATION') afficherErreurs($('#groupes'), erreur);
    else annoncerErreur(erreur);
  } finally {
    bouton.disabled = false;
  }
}

async function envoyer(evenement) {
  evenement.preventDefault();
  const formulaire = evenement.currentTarget;
  const resultat = $('#resultat-envoi');
  remplir(resultat);
  effacerErreurs(formulaire);
  if (!verifierAvantEnvoi()) return;
  const bouton = $('#bouton-envoyer');
  bouton.disabled = true;
  bouton.textContent = 'Envoi en cours…';
  try {
    const envoi = await api('POST', '/liste-achat/envoyer', { destinataire: $('#destinataire').value, liste: corpsListe() });
    remplir(resultat, h('p', { class: 'msg msg-succes', role: 'status' }, `Liste envoyée à ${envoi.destinataire} à ${heureFr(envoi.envoye_le)} !`));
  } catch (erreur) {
    if (!(erreur instanceof ErreurApi)) throw erreur;
    if (erreur.code === 'VALIDATION' && erreur.details.destinataire) afficherErreurs(formulaire, erreur);
    else if (erreur.code === 'VALIDATION') afficherErreurs($('#groupes'), erreur);
    else remplir(resultat, h('p', { class: 'msg msg-erreur', role: 'alert' }, erreur.message));
  } finally {
    bouton.disabled = false;
    bouton.textContent = 'Envoyer la liste';
  }
}

async function demarrer() {
  document.querySelectorAll('.bouton-export').forEach((b) => b.addEventListener('click', exporter));
  $('#formulaire-envoi').addEventListener('submit', envoyer);
  try {
    const [liste_, fournisseurs_, parametres] = await Promise.all([api('GET', '/liste-achat'), api('GET', '/fournisseurs'), api('GET', '/parametres')]);
    liste = liste_;
    fournisseurs = fournisseurs_;
    $('#genere-le').textContent = `Générée le ${dateLongue(liste.genere_le)} · ajuste les quantités avant d'envoyer`;
    $('#destinataire').value = parametres.mail_destinataire_defaut ?? '';
    if (!parametres.envoi_mail_configure) {
      $('#mail-non-configure').hidden = false;
      $('#bouton-envoyer').disabled = true;
    }
    rendre();
    if (location.hash === '#envoyer') $('#destinataire').focus();
  } catch (erreur) {
    annoncerErreur(erreur);
  }
}

demarrer();
