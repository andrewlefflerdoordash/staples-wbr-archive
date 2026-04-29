# Staples WBR Archive

Internal static site that hosts the weekly Staples WBR pre-read decks.

- **Site contents**: `index.html` (auto-generated) + `decks/*.pdf`
- **Hosting**: GitHub Pages from a private repo in the `doordash` org, with
  org SSO required for access.

## Layout

```
wbr_site/
├── decks/                     # one PDF per week, named staples_wbr_week_YYYY-MM-DD.pdf
├── index.html                 # auto-generated landing page
├── publish.py                 # one-command publish script
└── README.md                  # this file
```

## Publishing a new week

```bash
cd ~/Documents/wbr_site
python3 publish.py
```

By default this picks up the newest `staples_wbr_week_*.pdf` from
`~/Documents/wbr_generator/`, copies it into `decks/`, regenerates
`index.html`, then commits and pushes to `origin`.

Other modes:

| Command | What it does |
| --- | --- |
| `python3 publish.py path/to/deck.pdf` | Publish a specific deck |
| `python3 publish.py --no-push` | Commit locally only; don't push |
| `python3 publish.py --rebuild` | Rebuild `index.html` from the decks already in `decks/` (no copy) |

## First-time setup (one-time)

The repo isn't on GitHub yet. To wire it up:

1. **Authorize SSO for your gh token** (so the CLI can see DoorDash's org):
   ```bash
   gh auth refresh -s admin:org,repo
   ```
   When the browser opens, click **Authorize** for the `doordash` SAML SSO.

2. **Create the private repo in the doordash org** (recommended name:
   `staples-wbr-archive`):
   ```bash
   cd ~/Documents/wbr_site
   gh repo create doordash/staples-wbr-archive \
     --private \
     --source=. \
     --push \
     --description "Internal archive of Staples WBR decks"
   ```
   This initializes the local repo, sets up `origin`, and pushes the seed commit.

3. **Enable GitHub Pages** with SSO restriction:
   - Go to <https://github.com/doordash/staples-wbr-archive/settings/pages>
   - **Source**: Deploy from a branch
   - **Branch**: `main` / `(root)`
   - Save
   - Then under **Settings → Pages**, set **Visibility** to **Private**
     (only org members with SSO can view). This requires GitHub Enterprise
     Cloud, which DoorDash has.

4. **Share the URL**: GitHub will display it on the Pages settings page,
   typically `https://doordash.github.io/staples-wbr-archive/`.

After that, every Monday: regenerate the deck via the WBR generator and run
`python3 publish.py`. The new week appears at the top of the index within
~1 minute (Pages build time).

## Removing or replacing a deck

Just delete the PDF from `decks/` (or overwrite it) and run
`python3 publish.py --rebuild` to refresh the index.
