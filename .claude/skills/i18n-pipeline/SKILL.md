---
name: i18n-pipeline
description: Add or change translated strings of FilterMate in its 34 catalogs (i18n/FilterMate_*.ts and .qm) - add messages, compile with lrelease in Docker, resolve .qm conflicts after a merge, keep the terms consistent. Use whenever a change adds or changes a user-facing string, or a merge conflicts in i18n/.
---

# Translations of FilterMate

34 catalogs: `i18n/FilterMate_<lang>.ts` (sources and translations) and `.qm` (compiled). The test
`tests/unit/test_i18n_runtime_contexts.py::test_real_catalogs_translate_every_helper_string` fails when a string of
a `_tr` helper has no translation: run it after any change of a user-facing string.

## Contexts

Each module translates in its own context through a helper: `_tr` of `ui/controllers/agent_chat_controller.py` is
`AgentChat`, of `ui/widgets/agent_panel.py` is `AgentPanel`. A string already translated in another context can be
reused with `QCoreApplication.translate("AgentPanel", "Tools")` written inline: inline calls are not extracted by
`scripts/i18n_runtime_contexts.py`, so they must already exist in that context.

## Adding a few messages

1. Write `messages.json`: `[{"context", "after", "source", "file", "line", "translations": {"en", "fr", ...}}]`,
   `after` the source of an existing message of the same context, `file` relative to `i18n/`
   (`../ui/controllers/agent_chat_controller.py`), every one of the 34 languages present.
2. `python3 scripts/i18n_add_message.py messages.json` (a message already there is left alone; to change a
   translation, edit the `<translation>` of that `<source>`).
3. Compile: `docker run --rm -v "$PWD:/src" -w /src -e OWNER="$(id -u):$(id -g)" qgis/qgis:ltr bash
   scripts/i18n_release.sh` (Windows QGIS has no lrelease; "dropping duplicate messages" warnings are old).
4. Run the i18n test.

French is written by hand; other languages may be drafted by a sub-agent, then the uncertain ones read again
(Amharic, Uzbek, Tagalog, Thai and Hindi needed it). Keep `{}` and `\n` exactly as in the source.

## Terms already chosen

- Portuguese is European (`definições`, `guardar`), as the existing `FilterMate_pt.ts`.
- Chinese: the agent is `智能体` (not `代理`, which also reads as a proxy); Spanish settings are `ajustes`; Turkish agent
  `Aracı`; Uzbek in Latin script with an ASCII apostrophe.
- Before translating a word, look at how the catalog of that language already says it.

## After a merge

The `.ts` merge as text; the `.qm` conflict as binaries. Take one side and compile again from the merged `.ts`:

```bash
git checkout --theirs -- i18n/
docker run --rm -v "$PWD:/src" -w /src -e OWNER="$(id -u):$(id -g)" qgis/qgis:ltr bash scripts/i18n_release.sh
git add i18n/
```

Check that the merged `.ts` still hold the new strings (grep one of them) before committing.

## Full passes

A full extraction uses pylupdate5 on Windows, then `scripts/i18n_runtime_contexts.py`; it adds shifted locations
and may fill gaps of other branches: keep only the new messages in a focused change.
