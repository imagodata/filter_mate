#!/usr/bin/env python3
"""Create the FilterMate forms on Tally, in English and French.

Forms (``--form``):
    usage     How FilterMate is used today, with a star rating and a review.
    review    A short review: star rating, comment, permission to quote.
    services  A request for training, a funded feature or a domain pack.
    feature   Suggest a feature without a GitHub account.
    testers   Volunteer to test the experimental features.
    waitlist  The FilterMate Cloud waitlist (already live: EN PR9gVb, FR EqlgyN).

Each form measures one criterion of the commercial strategy for the end of
January 2027 (150 sign-ups, 5 teams, one service contract). Every form has a
hidden ``ref`` field, filled from ``?ref=...`` on the link, to know which
channel brought the answer.

With a rating, 4 or 5 stars show a link to rate FilterMate on
plugins.qgis.org (its "popular" ranking depends on the rating) and 1 to 3
stars ask what to fix. If Tally refuses that conditional logic, the form is
sent again without it: both blocks are then always shown.

Usage:
    python3 scripts/tally_forms.py --dry-run               # write the bodies, send nothing
    TALLY_API_KEY=tly-... python3 scripts/tally_forms.py   # create usage, review, services,
                                                           # feature and testers
    TALLY_API_KEY=tly-... python3 scripts/tally_forms.py --form usage --lang fr

The key comes from https://tally.so/settings/api-keys. Only the standard
library is used.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API_URL = "https://api.tally.so/forms"
PLUGIN_PAGE = "https://plugins.qgis.org/plugins/filter_mate/"


def _id() -> str:
    return str(uuid.uuid4())


class Form:
    """Collects Tally API blocks in order."""

    def __init__(self, logic: bool) -> None:
        self.blocks: list[dict] = []
        self.logic = logic

    # -- low level -------------------------------------------------------
    def _single(self, block_type: str, payload: dict, group_type: str | None = None) -> dict:
        uid = _id()
        block = {
            "uuid": uid,
            "type": block_type,
            "groupUuid": uid,
            "groupType": group_type or block_type,
            "payload": payload,
        }
        self.blocks.append(block)
        return block

    def _options(self, block_type: str, group_type: str, labels: list[str],
                 required: bool, name: str, extra: dict | None = None) -> None:
        group = _id()
        last = len(labels) - 1
        for index, label in enumerate(labels):
            payload = {
                "index": index,  # 0-based per the API schema
                "isFirst": index == 0,
                "isLast": index == last,
                "text": label,
                "isRequired": required,
                "name": name,
            }
            payload.update(extra or {})
            self.blocks.append({
                "uuid": _id(),
                "type": block_type,
                "groupUuid": group,
                "groupType": group_type,
                "payload": payload,
            })

    # -- content ---------------------------------------------------------
    def title(self, text: str) -> None:
        self._single("FORM_TITLE", {"html": text, "title": text})

    def text(self, html: str, hidden: bool = False) -> dict:
        return self._single("TEXT", {"html": html, "isHidden": hidden})

    def hidden_ref(self) -> None:
        self._single("HIDDEN_FIELDS", {"hiddenFields": [{"uuid": _id(), "name": "ref"}]})

    def question(self, html: str, hidden: bool = False) -> dict:
        return self._single("TITLE", {"html": html, "isHidden": hidden}, "QUESTION")

    def email(self, label: str, name: str, required: bool, placeholder: str = "") -> None:
        self.question(label)
        self._single("INPUT_EMAIL", {
            "isRequired": required, "placeholder": placeholder, "name": name,
        })

    def short(self, label: str, name: str, required: bool = False,
              placeholder: str = "", hidden: bool = False) -> list[dict]:
        q = self.question(label, hidden)
        b = self._single("INPUT_TEXT", {
            "isRequired": required, "placeholder": placeholder, "name": name,
            "isHidden": hidden,
        })
        return [q, b]

    def long(self, label: str, name: str, required: bool = False,
             placeholder: str = "", hidden: bool = False) -> list[dict]:
        q = self.question(label, hidden)
        b = self._single("TEXTAREA", {
            "isRequired": required, "placeholder": placeholder, "name": name,
            "isHidden": hidden,
        })
        return [q, b]

    def choice(self, label: str, name: str, options: list[str], required: bool = False) -> None:
        self.question(label)
        self._options("MULTIPLE_CHOICE_OPTION", "MULTIPLE_CHOICE", options, required, name)

    def checkboxes(self, label: str, name: str, options: list[str],
                   required: bool = False) -> None:
        self.question(label)
        self._options("CHECKBOX", "CHECKBOXES", options, required, name)

    def rating(self, t: dict, required: bool) -> None:
        """Star rating; good marks lead to plugins.qgis.org, low marks ask what to fix."""
        self.question(t["rating"])
        star = self._single("RATING", {"isRequired": required, "stars": 5, "name": "rating"})
        hidden = self.logic
        good = self.text(t["rate_plugin"].format(url=PLUGIN_PAGE), hidden=hidden)
        fix = self.long(t["fix"], "fix", hidden=hidden)
        if not self.logic:
            return
        field = {
            "uuid": star["uuid"],
            "type": "INPUT_FIELD",
            "questionType": "RATING",
            "blockGroupUuid": star["groupUuid"],
            "title": t["rating"],
        }
        for comparison, value, shown in (
            ("GREATER_OR_EQUAL_THAN", 4, [good["uuid"]]),
            ("LESS_OR_EQUAL_THAN", 3, [b["uuid"] for b in fix]),
        ):
            self._single("CONDITIONAL_LOGIC", {
                "logicalOperator": "AND",
                "conditionals": [{
                    "uuid": _id(),
                    "type": "SINGLE",
                    "payload": {"field": field, "comparison": comparison, "value": value},
                }],
                "actions": [{
                    "uuid": _id(),
                    "type": "SHOW_BLOCKS",
                    "payload": {"showBlocks": shown},
                }],
            })

    def consent(self, label: str, text: str, name: str = "consent",
                required: bool = True) -> None:
        self.question(label)
        self._options("CHECKBOX", "CHECKBOXES", [text], required, name)

    def thanks(self, heading: str, text: str) -> None:
        self._single("PAGE_BREAK", {
            "index": 1, "isFirst": False, "isLast": True, "isThankYouPage": True,
        })
        self._single("HEADING_2", {"html": heading})
        self.text(text)


# ---------------------------------------------------------------------------
# Shared texts
# ---------------------------------------------------------------------------

COMMON = {
    "en": {
        "email": "Your e-mail",
        "email_opt": "Your e-mail (optional, if you want an answer)",
        "email_ph": "you@example.org",
        "consent": "Consent",
        "consent_txt": (
            "I agree to be contacted about this request. "
            "I can ask for my data to be deleted at any time."
        ),
        "rating": "How would you rate FilterMate?",
        "rate_plugin": (
            "Thank you! A rating on <a href=\"{url}\">plugins.qgis.org</a> helps "
            "other QGIS users find FilterMate (log in with your OSGeo account, "
            "then pick the stars at the top of the page)."
        ),
        "fix": "What should we fix first?",
        "review": "Your review (optional)",
        "review_ph": "What FilterMate changed in your work, or what is missing",
        "quote": "Quote",
        "quote_txt": (
            "You may quote my review on the FilterMate site, with my first name "
            "and organisation only."
        ),
        "thanks": "Thank you.",
    },
    "fr": {
        "email": "Votre e-mail",
        "email_opt": "Votre e-mail (facultatif, si vous voulez une réponse)",
        "email_ph": "vous@exemple.fr",
        "consent": "Consentement",
        "consent_txt": (
            "J’accepte d’être recontacté au sujet de cette demande. "
            "Je peux demander la suppression de mes données à tout moment."
        ),
        "rating": "Quelle note donneriez-vous à FilterMate ?",
        "rate_plugin": (
            "Merci ! Une note sur <a href=\"{url}\">plugins.qgis.org</a> aide "
            "d’autres utilisateurs de QGIS à trouver FilterMate (connectez-vous "
            "avec votre compte OSGeo, puis choisissez les étoiles en haut de la page)."
        ),
        "fix": "Que faudrait-il corriger en premier ?",
        "review": "Votre avis (facultatif)",
        "review_ph": "Ce que FilterMate a changé dans votre travail, ou ce qui manque",
        "quote": "Citation",
        "quote_txt": (
            "Vous pouvez citer mon avis sur le site de FilterMate, avec seulement "
            "mon prénom et ma structure."
        ),
        "thanks": "Merci.",
    },
}


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

def usage(f: Form, lang: str) -> None:
    c = COMMON[lang]
    t = {
        "en": dict(
            title="How do you use FilterMate?",
            intro="Two minutes to tell us who you are and how FilterMate fits your work. "
                  "Your answers decide what we build next. The e-mail is optional.",
            sector="Your sector",
            sectors=["Local authority", "Consultancy or engineering firm", "Private company",
                     "Research or education", "State agency or public body", "Freelance",
                     "Other"],
            role="Your role",
            roles=["GIS analyst or technician", "GIS manager", "Developer",
                   "Planner, architect or engineer", "Student", "Other"],
            team="Do you use FilterMate alone or in a team?",
            teams=["Alone", "Team of 2 to 5", "Team of 6 to 20", "More than 20"],
            data="Which data do you filter?",
            datas=["GeoPackage", "PostgreSQL / PostGIS", "Shapefile",
                   "WFS or other web services", "Rasters", "Point clouds (LiDAR)", "Other"],
            features="Which features do you use?",
            featuress=["Filters on several layers", "Spatial filters (buffer, intersects)",
                       "Favorites", "Filter history and undo", "Export",
                       "Project sharing in a GeoPackage", "AGENT (chat)", "SAM segmentation",
                       "Raster and point-cloud filters", "Processing algorithms or API"],
            often="How often?",
            oftens=["Every day", "Every week", "Every month", "Rarely"],
            block="What blocks you or slows you down?",
            pay="What would be worth paying for, if anything?",
            pay_ph="e.g. a shared library for the team, segmentation without a GPU…",
            thanks="Your answers help decide what comes next for FilterMate.",
        ),
        "fr": dict(
            title="Comment utilisez-vous FilterMate ?",
            intro="Deux minutes pour nous dire qui vous êtes et la place de FilterMate dans "
                  "votre travail. Vos réponses décident de la suite. L’e-mail est facultatif.",
            sector="Votre secteur",
            sectors=["Collectivité", "Bureau d’études", "Entreprise privée",
                     "Recherche ou enseignement", "Service de l’État ou établissement public",
                     "Indépendant", "Autre"],
            role="Votre rôle",
            roles=["Géomaticien ou technicien SIG", "Responsable SIG", "Développeur",
                   "Urbaniste, architecte ou ingénieur", "Étudiant", "Autre"],
            team="Utilisez-vous FilterMate seul ou en équipe ?",
            teams=["Seul", "Équipe de 2 à 5", "Équipe de 6 à 20", "Plus de 20"],
            data="Quelles données filtrez-vous ?",
            datas=["GeoPackage", "PostgreSQL / PostGIS", "Shapefile",
                   "WFS ou autres services web", "Rasters", "Nuages de points (LiDAR)",
                   "Autre"],
            features="Quelles fonctions utilisez-vous ?",
            featuress=["Filtres sur plusieurs couches", "Filtres spatiaux (tampon, intersection)",
                       "Favoris", "Historique et annulation", "Export",
                       "Partage de projet dans un GeoPackage", "AGENT (tchat)",
                       "Segmentation SAM", "Filtres raster et nuages de points",
                       "Algorithmes Processing ou API"],
            often="À quelle fréquence ?",
            oftens=["Tous les jours", "Toutes les semaines", "Tous les mois", "Rarement"],
            block="Qu’est-ce qui vous bloque ou vous ralentit ?",
            pay="Qu’est-ce qui vaudrait d’être payé, s’il y a quelque chose ?",
            pay_ph="ex. une bibliothèque partagée pour l’équipe, la segmentation sans GPU…",
            thanks="Vos réponses aident à décider de la suite de FilterMate.",
        ),
    }[lang]
    f.title(t["title"])
    f.text(t["intro"])
    f.hidden_ref()
    f.choice(t["sector"], "sector", t["sectors"])
    f.choice(t["role"], "role", t["roles"])
    f.choice(t["team"], "team", t["teams"])
    f.checkboxes(t["data"], "data", t["datas"])
    f.checkboxes(t["features"], "features", t["featuress"])
    f.choice(t["often"], "often", t["oftens"])
    f.long(t["block"], "block")
    f.long(t["pay"], "pay", placeholder=t["pay_ph"])
    f.rating(c, required=False)
    f.long(c["review"], "review", placeholder=c["review_ph"])
    f.consent(c["quote"], c["quote_txt"], "quote", required=False)
    f.email(c["email_opt"], "email", False, c["email_ph"])
    f.thanks(c["thanks"], t["thanks"])


def review(f: Form, lang: str) -> None:
    c = COMMON[lang]
    t = {
        "en": dict(title="Your review of FilterMate",
                   intro="Thirty seconds: a rating and, if you like, a few words.",
                   thanks="Your review helps us and other QGIS users."),
        "fr": dict(title="Votre avis sur FilterMate",
                   intro="Trente secondes : une note et, si vous voulez, quelques mots.",
                   thanks="Votre avis nous aide, ainsi que d’autres utilisateurs de QGIS."),
    }[lang]
    f.title(t["title"])
    f.text(t["intro"])
    f.hidden_ref()
    f.rating(c, required=True)
    f.long(c["review"], "review", placeholder=c["review_ph"])
    f.consent(c["quote"], c["quote_txt"], "quote", required=False)
    f.email(c["email_opt"], "email", False, c["email_ph"])
    f.thanks(c["thanks"], t["thanks"])


def services(f: Form, lang: str) -> None:
    c = COMMON[lang]
    t = {
        "en": dict(
            title="Training and services around FilterMate",
            intro="imagodata trains teams on QGIS and FilterMate, builds funded features "
                  "that are published as open source, and prepares domain packs. "
                  "Tell us what you need; we answer within a week.",
            who="Your name and organisation",
            need="What do you need?",
            needs=["Training (QGIS and FilterMate)",
                   "A funded feature, published as open source",
                   "A domain pack (setup, recipes and styles for your field)",
                   "Support or an audit of your setup", "Other"],
            people="How many people are concerned?",
            people_ph="e.g. 8 GIS technicians",
            when="By when?",
            whens=["Within a month", "Within 3 months", "Within 6 months", "No deadline"],
            budget="Indicative budget (excl. VAT)",
            budgets=["Under 1,000 €", "1,000 to 5,000 €", "5,000 to 15,000 €",
                     "Over 15,000 €", "Not known yet"],
            detail="Describe your need",
            detail_ph="Your data, your tools, what you want to achieve",
            thanks="We will answer within a week.",
        ),
        "fr": dict(
            title="Formation et services autour de FilterMate",
            intro="imagodata forme les équipes à QGIS et FilterMate, développe des fonctions "
                  "financées publiées en open source et prépare des packs métier. "
                  "Dites-nous votre besoin ; nous répondons sous une semaine.",
            who="Votre nom et votre structure",
            need="De quoi avez-vous besoin ?",
            needs=["Une formation (QGIS et FilterMate)",
                   "Une fonction financée, publiée en open source",
                   "Un pack métier (réglages, recettes et styles pour votre domaine)",
                   "Un accompagnement ou un audit de votre installation", "Autre"],
            people="Combien de personnes sont concernées ?",
            people_ph="ex. 8 techniciens SIG",
            when="Pour quand ?",
            whens=["D’ici un mois", "D’ici 3 mois", "D’ici 6 mois", "Pas d’échéance"],
            budget="Budget indicatif (HT)",
            budgets=["Moins de 1 000 €", "1 000 à 5 000 €", "5 000 à 15 000 €",
                     "Plus de 15 000 €", "Pas encore connu"],
            detail="Décrivez votre besoin",
            detail_ph="Vos données, vos outils, ce que vous voulez obtenir",
            thanks="Nous vous répondons sous une semaine.",
        ),
    }[lang]
    f.title(t["title"])
    f.text(t["intro"])
    f.hidden_ref()
    f.email(c["email"], "email", True, c["email_ph"])
    f.short(t["who"], "organisation", required=True)
    f.checkboxes(t["need"], "need", t["needs"], required=True)
    f.short(t["people"], "people", placeholder=t["people_ph"])
    f.choice(t["when"], "when", t["whens"])
    f.choice(t["budget"], "budget", t["budgets"])
    f.long(t["detail"], "detail", required=True, placeholder=t["detail_ph"])
    f.consent(c["consent"], c["consent_txt"])
    f.thanks(c["thanks"], t["thanks"])


def feature(f: Form, lang: str) -> None:
    c = COMMON[lang]
    t = {
        "en": dict(
            title="Suggest a feature for FilterMate",
            intro="No GitHub account needed. One idea per answer; we read every one.",
            need="Your need in one sentence",
            need_ph="e.g. filter a layer by the values of a field in another layer",
            context="The context: what are you trying to do, with which data?",
            weight="How important is it for you?",
            weights=["Nice to have", "Important", "Blocking"],
            fund="Would your organisation fund it, published as open source?",
            funds=["Yes", "Maybe", "No"],
            notify="Follow-up",
            notify_txt="Write to me when it ships, or if you have a question.",
            thanks="Every suggestion is read and sorted with the others.",
        ),
        "fr": dict(
            title="Proposer une fonction pour FilterMate",
            intro="Pas besoin de compte GitHub. Une idée par réponse ; nous les lisons toutes.",
            need="Votre besoin en une phrase",
            need_ph="ex. filtrer une couche selon les valeurs d’un champ d’une autre couche",
            context="Le contexte : que cherchez-vous à faire, avec quelles données ?",
            weight="Quelle importance pour vous ?",
            weights=["Ce serait bien", "Important", "Bloquant"],
            fund="Votre structure la financerait-elle, publiée en open source ?",
            funds=["Oui", "Peut-être", "Non"],
            notify="Suivi",
            notify_txt="Écrivez-moi quand elle sort, ou si vous avez une question.",
            thanks="Chaque proposition est lue et classée avec les autres.",
        ),
    }[lang]
    f.title(t["title"])
    f.text(t["intro"])
    f.hidden_ref()
    f.short(t["need"], "need", required=True, placeholder=t["need_ph"])
    f.long(t["context"], "context")
    f.choice(t["weight"], "weight", t["weights"])
    f.choice(t["fund"], "fund", t["funds"])
    f.email(c["email_opt"], "email", False, c["email_ph"])
    f.consent(t["notify"], t["notify_txt"], "notify", required=False)
    f.thanks(c["thanks"], t["thanks"])


def testers(f: Form, lang: str) -> None:
    c = COMMON[lang]
    t = {
        "en": dict(
            title="Test FilterMate's experimental features",
            intro="AGENT, SAM segmentation and point clouds are experimental. "
                  "Testers get them first and shape how they work.",
            what="What would you test?",
            whats=["AGENT (a chat that drives QGIS)", "SAM segmentation",
                   "Point-cloud filters and objects", "New versions before release"],
            setup="Your setup",
            setups=["NVIDIA GPU", "Ollama installed",
                    "Own API key (Anthropic, OpenAI, Mistral…)", "None of these"],
            qgis="QGIS version",
            qgiss=["QGIS 3 (LTR or latest)", "QGIS 4", "Not sure"],
            os="Operating system",
            oss=["Windows", "macOS", "Linux"],
            time="How much time could you give?",
            times=["One test and some feedback", "A test per release", "Regular calls"],
            consent_txt="I agree to be contacted about testing FilterMate. "
                        "I can ask for my data to be deleted at any time.",
            thanks="We will write to you with the next version to test.",
        ),
        "fr": dict(
            title="Tester les fonctions expérimentales de FilterMate",
            intro="AGENT, la segmentation SAM et les nuages de points sont expérimentaux. "
                  "Les testeurs les reçoivent en premier et décident de leur forme.",
            what="Que testeriez-vous ?",
            whats=["AGENT (un tchat qui pilote QGIS)", "Segmentation SAM",
                   "Filtres et objets des nuages de points",
                   "Les nouvelles versions avant leur sortie"],
            setup="Votre matériel",
            setups=["Carte graphique NVIDIA", "Ollama installé",
                    "Clé API personnelle (Anthropic, OpenAI, Mistral…)", "Aucun de ceux-là"],
            qgis="Version de QGIS",
            qgiss=["QGIS 3 (LTR ou dernière)", "QGIS 4", "Je ne sais pas"],
            os="Système d’exploitation",
            oss=["Windows", "macOS", "Linux"],
            time="Combien de temps pourriez-vous y consacrer ?",
            times=["Un test et un retour", "Un test par version", "Des échanges réguliers"],
            consent_txt="J’accepte d’être recontacté pour tester FilterMate. "
                        "Je peux demander la suppression de mes données à tout moment.",
            thanks="Nous vous écrirons avec la prochaine version à tester.",
        ),
    }[lang]
    f.title(t["title"])
    f.text(t["intro"])
    f.hidden_ref()
    f.email(c["email"], "email", True, c["email_ph"])
    f.checkboxes(t["what"], "what", t["whats"], required=True)
    f.checkboxes(t["setup"], "setup", t["setups"])
    f.choice(t["qgis"], "qgis", t["qgiss"])
    f.choice(t["os"], "os", t["oss"])
    f.choice(t["time"], "time", t["times"])
    f.consent(c["consent"], t["consent_txt"])
    f.thanks(c["thanks"], t["thanks"])


def waitlist(f: Form, lang: str) -> None:
    c = COMMON[lang]
    t = {
        "en": dict(
            title="FilterMate Cloud waitlist",
            intro="Tell us which tier you would use and what you expect from it. "
                  "No payment, no commitment; you will only be written to about "
                  "FilterMate Cloud.",
            tier="Which tier would you use?",
            tiers=["Free account", "Pro", "Team", "Organisation",
                   "Services only (training, funded features)"],
            team="Team or Organisation: how many people, and which organisation?",
            team_ph="e.g. 6 GIS analysts, Example County Council",
            service="Do you need training or a funded feature?",
            service_opts=["Yes", "Not now"],
            service_detail="If yes, what would it be?",
            service_detail_ph="e.g. a one-day QGIS + FilterMate training for 8 people",
            expect="What do you expect from FilterMate Cloud?",
            expect_ph="The feature that would make you use it",
            source="How did you hear about FilterMate?",
            sources=["LinkedIn", "Reddit", "Mastodon", "QGIS-fr or GeoRezo",
                     "plugins.qgis.org", "A colleague", "Other"],
            consent_txt="I agree to be contacted about FilterMate Cloud. "
                        "I can ask for my data to be deleted at any time.",
            letter="FilterMate letter",
            letter_txt="Also send me the FilterMate letter (one a month at most).",
            thanks_title="Thank you, you are on the list.",
            thanks="We will write to you when FilterMate Cloud opens a tier you "
                   "chose, and only about that.",
        ),
        "fr": dict(
            title="Liste d’attente FilterMate Cloud",
            intro="Dites-nous quelle formule vous utiliseriez et ce que vous en "
                  "attendez. Aucun paiement, aucun engagement ; nous ne vous "
                  "écrirons qu’au sujet de FilterMate Cloud.",
            tier="Quelle formule utiliseriez-vous ?",
            tiers=["Compte gratuit", "Pro", "Équipe", "Organisation",
                   "Services seulement (formation, fonctions financées)"],
            team="Équipe ou Organisation : combien de personnes, et quelle structure ?",
            team_ph="ex. 6 géomaticiens, communauté d’agglomération de …",
            service="Avez-vous besoin d’une formation ou d’une fonction financée ?",
            service_opts=["Oui", "Pas pour l’instant"],
            service_detail="Si oui, laquelle ?",
            service_detail_ph="ex. une journée de formation QGIS + FilterMate pour 8 personnes",
            expect="Qu’attendez-vous de FilterMate Cloud ?",
            expect_ph="La fonction qui vous le ferait utiliser",
            source="Comment avez-vous connu FilterMate ?",
            sources=["LinkedIn", "Reddit", "Mastodon", "QGIS-fr ou GeoRezo",
                     "plugins.qgis.org", "Un collègue", "Autre"],
            consent_txt="J’accepte d’être recontacté au sujet de FilterMate Cloud. "
                        "Je peux demander la suppression de mes données à tout moment.",
            letter="Lettre FilterMate",
            letter_txt="M’envoyer aussi la lettre FilterMate (une par mois au plus).",
            thanks_title="Merci, vous êtes sur la liste.",
            thanks="Nous vous écrirons quand FilterMate Cloud ouvrira une formule "
                   "que vous avez choisie, et seulement pour cela.",
        ),
    }[lang]
    f.title(t["title"])
    f.text(t["intro"])
    f.hidden_ref()
    f.email(c["email"], "email", True, c["email_ph"])
    f.choice(t["tier"], "tier", t["tiers"], required=True)
    f.short(t["team"], "team", placeholder=t["team_ph"])
    f.choice(t["service"], "service", t["service_opts"])
    f.short(t["service_detail"], "service_detail", placeholder=t["service_detail_ph"])
    f.long(t["expect"], "expect", placeholder=t["expect_ph"])
    f.choice(t["source"], "source", t["sources"])
    f.consent(c["consent"], t["consent_txt"])
    f.consent(t["letter"], t["letter_txt"], "letter", required=False)
    f.thanks(t["thanks_title"], t["thanks"])


FORMS = {
    "usage": usage,
    "review": review,
    "services": services,
    "feature": feature,
    "testers": testers,
    "waitlist": waitlist,
}
DEFAULT_FORMS = ["usage", "review", "services", "feature", "testers"]


def build_body(form: str, lang: str, status: str, logic: bool = True) -> dict:
    """The request body of POST /forms for one form in one language."""
    f = Form(logic)
    FORMS[form](f, lang)
    return {"status": status, "blocks": f.blocks, "settings": {"language": lang}}


def _post(body: dict, key: str) -> dict:
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "filtermate-forms-setup",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def create(form: str, lang: str, status: str, key: str) -> tuple[dict, bool]:
    """Create one form; retry without conditional logic if Tally refuses it."""
    body = build_body(form, lang, status, logic=True)
    has_logic = any(b["type"] == "CONDITIONAL_LOGIC" for b in body["blocks"])
    try:
        return _post(body, key), has_logic
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        if error.code != 400 or not has_logic:
            raise SystemExit(f"{form}/{lang}: Tally refused the form ({error.code}): {detail}")
        print(f"{form}/{lang}: logic refused ({detail[:300]}); sending without it",
              file=sys.stderr)
    try:
        return _post(build_body(form, lang, status, logic=False), key), False
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise SystemExit(f"{form}/{lang}: Tally refused the form ({error.code}): {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--form", choices=[*FORMS, "all"], action="append",
                        help="form to create (repeatable; default: all but waitlist)")
    parser.add_argument("--lang", choices=["en", "fr", "both"], default="both")
    parser.add_argument("--status", choices=["PUBLISHED", "DRAFT"], default="PUBLISHED")
    parser.add_argument("--dry-run", action="store_true",
                        help="write the request bodies to --out and send nothing")
    parser.add_argument("--no-logic", action="store_true",
                        help="dry run only: write the bodies without conditional logic")
    parser.add_argument("--out", type=Path, default=Path("tally_forms"))
    args = parser.parse_args()

    forms = args.form or DEFAULT_FORMS
    if "all" in forms:
        forms = list(FORMS)
    langs = ["en", "fr"] if args.lang == "both" else [args.lang]

    if args.dry_run:
        args.out.mkdir(parents=True, exist_ok=True)
        for form in forms:
            for lang in langs:
                body = build_body(form, lang, args.status, logic=not args.no_logic)
                path = args.out / f"{form}_{lang}.json"
                path.write_text(json.dumps(body, ensure_ascii=False, indent=2),
                                encoding="utf-8")
                print(f"{form}/{lang}: {len(body['blocks'])} blocks -> {path}")
        return 0

    key = os.environ.get("TALLY_API_KEY", "").strip()
    if not key:
        print("Set TALLY_API_KEY (https://tally.so/settings/api-keys).", file=sys.stderr)
        return 2

    for form in forms:
        for lang in langs:
            result, logic = create(form, lang, args.status, key)
            form_id = result.get("id")
            note = " (with rating logic)" if logic else ""
            print(f"{form}/{lang}: {form_id} https://tally.so/r/{form_id}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
