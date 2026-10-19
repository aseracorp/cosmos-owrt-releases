# Cosmos Cloud OpenWrt

Public download index for **Cosmos Cloud OpenWrt** images.

**Note:** This repository contains **no binary files**. It is an automatically generated download index (GitHub Pages).

- Images are hosted as GitHub **Release assets** and linked from this site.
- Every release of [`aseracorp/cosmos-owrt`](https://github.com/aseracorp/cosmos-owrt) is mirrored here automatically.
- The [`generate-site`](.github/workflows/generate-site.yml) workflow rebuilds this site whenever a release is pushed or mirrored.

## Site

- Site: <https://aseracorp.github.io/cosmos-owrt-releases/>
- Auto-links: `latest/` (latest Cosmos Cloud overall) and `latest/<openwrt>` (per OpenWrt version).
- Only the **latest** release of each Cosmos Cloud/OpenWrt combo gets download links; older files are listed without links.

## Structure

```
<openwrt>/            e.g. 25.12.5  (OpenWrt version)
  <cosmos>/           e.g. v0.23.4   (Cosmos Cloud version, dir name from release name)
    files             download links (latest release of that combo only)
latest/               latest Cosmos Cloud overall (auto-updating)
  <openwrt>/…/files
latest/<openwrt>/      latest Cosmos Cloud for each OpenWrt (auto-updating)
```

## For maintainers

In the *private* source repo `aseracorp/cosmos-owrt`, a workflow mirrors every release to this repo and triggers a rebuild. Building your own copy of the index:

```
./scripts/generate.py --source aseracorp/cosmos-owrt-releases --root . --branch main
```