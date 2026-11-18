#!/usr/bin/env python3
"""Create the FilterMate Cloud waitlist forms on Tally (English and French).

Each question measures one of the criteria the commercial strategy sets for the
end of January 2027: 150 sign-ups, 5 teams asking for the private library, one
service contract. The forms are built as Tally API blocks and sent to
``POST https://api.tally.so/forms``.

Usage:
    # Write the two request bodies to disk, send nothing.
    python3 scripts/tally_waitlist_form.py --dry-run

    # Create both forms (key from https://tally.so/settings/api-keys).
    TALLY_API_KEY=tly-... python3 scripts/tally_waitlist_form.py

The form ids printed at the end replace ``__TALLY_FORM_ID__`` in
``website/cloud.html`` (English form) and ``website/cloud.fr.html`` (French
form). Only the standard library is used.
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

TEXTS = {
    "en": {
        "title": "FilterMate Cloud waitlist",
        "intro": (
            "Tell us which tier you would use and what you expect from it. "
            "No payment, no commitment; you will only be written to about "
            "FilterMate Cloud."
        ),
        "email": "Your e-mail",
        "email_ph": "you@example.org",
        "tier": "Which tier would you use?",
        "tiers": [
            "Free account",
            "Pro",
            "Team",
            "Organisation",
            "Services only (training, funded features)",
        ],
        "team": "Team or Organisation: how many people, and which organisation?",
        "team_ph": "e.g. 6 GIS analysts, Example County Council",
        "service": "Do you need training or a funded feature?",
        "service_opts": ["Yes", "Not now"],
        "service_detail": "If yes, what would it be?",
        "service_detail_ph": "e.g. a one-day QGIS + FilterMate training for 8 people",
        "expect": "What do you expect from FilterMate Cloud?",
        "expect_ph": "The feature that would make you use it",
        "source": "How did you hear about FilterMate?",
        "sources": [
            "LinkedIn",
            "Reddit",
            "Mastodon",
            "QGIS-fr or GeoRezo",
            "plugins.qgis.org",
            "A colleague",
            "Other",
        ],
        "consent": "Consent",
        "consent_opt": (
            "I agree to be contacted about FilterMate Cloud. "
            "I can ask for my data to be deleted at any time."
        ),
        "letter": "FilterMate letter",
        "letter_opt": "Also send me the FilterMate letter (one a month at most).",
        "thanks_title": "Thank you, you are on the list.",
        "thanks": (
            "We will write to you when FilterMate Cloud opens a tier you "
            "chose, and only about that."
        ),
    },
    "fr": {
        "title": "Liste d’attente FilterMate Cloud",
        "intro": (
            "Dites-nous quelle formule vous utiliseriez et ce que vous en "
            "attendez. Aucun paiement, aucun engagement ; nous ne vous "
            "écrirons qu’au sujet de FilterMate Cloud."
        ),
        "email": "Votre e-mail",
        "email_ph": "vous@exemple.fr",
        "tier": "Quelle formule utiliseriez-vous ?",
        "tiers": [
            "Compte gratuit",
            "Pro",
            "Équipe",
            "Organisation",
            "Services seulement (formation, fonctions financées)",
        ],
        "team": "Équipe ou Organisation : combien de personnes, et quelle structure ?",
        "team_ph": "ex. 6 géomaticiens, communauté d’agglomération de …",
        "service": "Avez-vous besoin d’une formation ou d’une fonction financée ?",
        "service_opts": ["Oui", "Pas pour l’instant"],
        "service_detail": "Si oui, laquelle ?",
        "service_detail_ph": "ex. une journée de formation QGIS + FilterMate pour 8 personnes",
        "expect": "Qu’attendez-vous de FilterMate Cloud ?",
        "expect_ph": "La fonction qui vous le ferait utiliser",
        "source": "Comment avez-vous connu FilterMate ?",
        "sources": [
            "LinkedIn",
            "Reddit",
            "Mastodon",
            "QGIS-fr ou GeoRezo",
            "plugins.qgis.org",
            "Un collègue",
            "Autre",
        ],
        "consent": "Consentement",
        "consent_opt": (
            "J’accepte d’être recontacté au sujet de FilterMate Cloud. "
            "Je peux demander la suppression de mes données à tout moment."
        ),
        "letter": "Lettre FilterMate",
        "letter_opt": "M’envoyer aussi la lettre FilterMate (une par mois au plus).",
        "thanks_title": "Merci, vous êtes sur la liste.",
        "thanks": (
            "Nous vous écrirons quand FilterMate Cloud ouvrira une formule "
            "que vous avez choisie, et seulement pour cela."
        ),
    },
}


def _id() -> str:
    return str(uuid.uuid4())


def _single(block_type: str, payload: dict, group_type: str | None = None) -> dict:
    """A standalone block: its group is itself."""
    uid = _id()
    return {
        "uuid": uid,
        "type": block_type,
        "groupUuid": uid,
        "groupType": group_type or block_type,
        "payload": payload,
    }


def _question(html: str) -> dict:
    return _single("TITLE", {"html": html}, "QUESTION")


def _options(block_type: str, group_type: str, labels: list[str],
             required: bool, name: str) -> list[dict]:
    """A group of option blocks sharing one groupUuid (index is 0-based)."""
    group = _id()
    last = len(labels) - 1
    blocks = []
    for index, label in enumerate(labels):
        blocks.append({
            "uuid": _id(),
            "type": block_type,
            "groupUuid": group,
            "groupType": group_type,
            "payload": {
                "index": index,
                "isFirst": index == 0,
                "isLast": index == last,
                "text": label,
                "isRequired": required,
                "name": name,
            },
        })
    return blocks


def _choice(labels: list[str], required: bool, name: str) -> list[dict]:
    return _options("MULTIPLE_CHOICE_OPTION", "MULTIPLE_CHOICE", labels, required, name)


def _checkbox(label: str, required: bool, name: str) -> list[dict]:
    return _options("CHECKBOX", "CHECKBOXES", [label], required, name)


def build_body(lang: str, status: str) -> dict:
    """The request body of POST /forms for one language."""
    t = TEXTS[lang]
    blocks: list[dict] = [
        _single("FORM_TITLE", {"html": t["title"], "title": t["title"]}),
        _single("TEXT", {"html": t["intro"]}),
        # Filled from ?ref=... on the page URL: which channel brought the visitor.
        _single("HIDDEN_FIELDS", {"hiddenFields": [{"uuid": _id(), "name": "ref"}]}),
        # 1. E-mail: the 150 sign-ups.
        _question(t["email"]),
        _single("INPUT_EMAIL", {
            "isRequired": True, "placeholder": t["email_ph"], "name": "email",
        }),
        # 2. Tier: Team + Organisation count toward the 5 teams.
        _question(t["tier"]),
        *_choice(t["tiers"], True, "tier"),
        # 3. Qualifies those teams (optional, no branching needed).
        _question(t["team"]),
        _single("INPUT_TEXT", {
            "isRequired": False, "placeholder": t["team_ph"], "name": "team",
        }),
        # 4. Service leads: the one contract.
        _question(t["service"]),
        *_choice(t["service_opts"], False, "service"),
        _question(t["service_detail"]),
        _single("INPUT_TEXT", {
            "isRequired": False, "placeholder": t["service_detail_ph"],
            "name": "service_detail",
        }),
        # 5. Expected features.
        _question(t["expect"]),
        _single("TEXTAREA", {
            "isRequired": False, "placeholder": t["expect_ph"], "name": "expect",
        }),
        # 6. Channels of the communication strategy.
        _question(t["source"]),
        *_choice(t["sources"], False, "source"),
        # 7. GDPR consent, required.
        _question(t["consent"]),
        *_checkbox(t["consent_opt"], True, "consent"),
        # 8. The letter, optional.
        _question(t["letter"]),
        *_checkbox(t["letter_opt"], False, "letter"),
        # Thank-you page.
        _single("PAGE_BREAK", {
            "index": 1, "isFirst": False, "isLast": True, "isThankYouPage": True,
        }),
        _single("HEADING_2", {"html": t["thanks_title"]}),
        _single("TEXT", {"html": t["thanks"]}),
    ]
    return {
        "status": status,
        "blocks": blocks,
        "settings": {"language": lang},
    }


def create(body: dict, key: str) -> dict:
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "filtermate-waitlist-setup",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise SystemExit(f"Tally refused the form ({error.code}): {detail}") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="write the request bodies to --out and send nothing")
    parser.add_argument("--out", type=Path, default=Path("tally_forms"),
                        help="folder for the dry-run bodies (default: ./tally_forms)")
    parser.add_argument("--status", choices=["PUBLISHED", "DRAFT"], default="PUBLISHED",
                        help="PUBLISHED is needed for the embed on the site")
    parser.add_argument("--lang", choices=["en", "fr", "both"], default="both")
    args = parser.parse_args()

    langs = ["en", "fr"] if args.lang == "both" else [args.lang]
    bodies = {lang: build_body(lang, args.status) for lang in langs}

    if args.dry_run:
        args.out.mkdir(parents=True, exist_ok=True)
        for lang, body in bodies.items():
            path = args.out / f"waitlist_{lang}.json"
            path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{lang}: {len(body['blocks'])} blocks -> {path}")
        return 0

    key = os.environ.get("TALLY_API_KEY", "").strip()
    if not key:
        print("Set TALLY_API_KEY (https://tally.so/settings/api-keys).", file=sys.stderr)
        return 2

    pages = {"en": "website/cloud.html", "fr": "website/cloud.fr.html"}
    for lang, body in bodies.items():
        form = create(body, key)
        form_id = form.get("id")
        print(f"{lang}: form {form_id} ({form.get('status')}) "
              f"https://tally.so/r/{form_id} -> {pages[lang]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
