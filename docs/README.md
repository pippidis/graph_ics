# graph_ics website

This directory contains the complete static website: the homepage, visual gallery, user guide, technical references, downloadable scenes and logo assets.

Open [index.html](index.html) locally or visit [graph-ics.pippidis.no](https://graph-ics.pippidis.no) after launch. GitHub Pages can serve this directory from `main` / `/docs`. Links are relative so the site also works offline and under a project URL.

To refresh the website from the repository root:

```console
python -m scripts.prepare_site
python -m scripts.check_site
```

Editable manual sources live in [scripts/site_content](../scripts/site_content/). Shared presentation and navigation are maintained in `src/gallery_page.py` and `src/site_structure.py`; edit those sources rather than generated HTML. See [supporting scripts](../scripts/README.md) for artwork regeneration and [release helper](../scripts/release.py) for hosting instructions.
