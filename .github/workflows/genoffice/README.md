# GenOffice native Arch Linux package builder

The workflow checks `genspark-ai/genoffice` at 17:00 UTC / 00:00 Asia/Jakarta
every day. Manual dispatch and workflow pushes also run the pipeline. Pull
requests run validation.

The package is built from source inside a disposable `archlinux:base-devel`
container using `makepkg`. Unchanged upstream commits and packaging inputs skip
compilation before downloading source archives. Failed builds never advance the
published checkpoint. Source snapshots and lockfiles come from pinned upstream
revisions; no upstream source tree or vendored dependencies are committed here.

```sh
curl -fsSL https://github.com/zamkara/genoffice/releases/latest/download/install.sh | bash
```

Each published release contains the validated `.pkg.tar.zst` package,
`install.sh`, `PKGBUILD`, `SRCINFO`, `upstream.json`, `CHANGELOG.md`, and
`SHA256SUMS`. The complete asset set is uploaded and verified as a draft before
becoming public and latest.

Snapshots use `upstream-version.rCOMMITTIMESTAMP.gCOMMIT` and packaging changes
increment `pkgrel`. Builds, caches, and source archives remain disposable runner
files, not repository content. The repository root contains only `LICENSE`,
`README.md`, and `.github`.
