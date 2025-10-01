# Release Process

This document describes the **fully automated** release process for the Battery Energy Trading integration.

## 🚀 Automated Release Process

**Releases are 100% automatic!** Just merge your PR to main, and the system handles everything:

1. ✅ Analyzes commit messages to determine version bump type
2. ✅ Bumps version in `manifest.json`
3. ✅ Updates `CHANGELOG.md` with commit history
4. ✅ Creates and pushes git tag
5. ✅ Creates GitHub Release with ZIP archive
6. ✅ HACS auto-detects within 24 hours

## How It Works

### Commit Message Convention

The automation determines the version bump type from your commit messages:

- **`feat:`** or **`feature:`** → Minor version bump (0.X.0)
- **`fix:`** or **`bugfix:`** → Patch version bump (0.0.X)
- **`breaking:`** or **`major:`** → Major version bump (X.0.0)

Examples:
```bash
git commit -m "feat: add multi-day optimization"      # → 0.8.0 to 0.9.0
git commit -m "fix: correct entity detection"         # → 0.8.0 to 0.8.1
git commit -m "breaking: remove deprecated API"       # → 0.8.0 to 1.0.0
```

### Workflow Sequence

```
1. Merge PR to main
   ↓
2. Auto-release workflow triggers
   ↓
3. Analyzes commits since last tag
   ↓
4. Calculates new version (major.minor.patch)
   ↓
5. Updates manifest.json + CHANGELOG.md
   ↓
6. Commits with [skip ci] to prevent loop
   ↓
7. Creates and pushes git tag (vX.Y.Z)
   ↓
8. Dispatches repository_dispatch event
   ↓
9. Release workflow triggers
   ↓
10. Creates GitHub Release with ZIP
```

## Manual Release (Rarely Needed)

If you need to manually create a release for an existing tag:

```bash
# Using GitHub CLI
gh workflow run release.yml -f tag=v0.8.0

# Or via GitHub UI
# Go to Actions → Release → Run workflow → Enter tag → Run
```

## Prerequisites for Auto-Release

The auto-release workflow triggers when:

- ✅ Push to `main` branch
- ✅ At least one commit since last tag
- ❌ Skips changes to: `**.md`, `docs/**`, `.github/**`, `tests/**`, `dashboards/**`

## Version Numbering

### 6. Verify Release

1. Go to https://github.com/Tsopic/battery_energy_trading/releases
2. Verify the release was created
3. Download and test the .zip file
4. Check that release notes are correct

### 7. HACS Update (Automatic)

HACS will automatically detect the new release within 24 hours.

Users can then update via:
- HACS → Integrations → Battery Energy Trading → Update

## Release Workflow

The release is triggered when you push a tag matching `v*.*.*`:

```yaml
on:
  push:
    tags:
      - 'v*.*.*'
```

### What the Workflow Does

1. **Version Verification**
   - Checks that manifest.json version matches the tag
   - Fails if versions don't match

2. **Changelog Extraction**
   - Extracts relevant section from CHANGELOG.md
   - Uses this as release notes

3. **Archive Creation**
   - Creates `battery_energy_trading-X.Y.Z.zip`
   - Includes only the integration files

4. **Release Creation**
   - Creates GitHub release
   - Attaches archive
   - Includes installation instructions

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0): Breaking changes, major features
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes, minor improvements

Examples:
- `v0.4.0` - Added Sungrow auto-detection (new feature)
- `v0.4.1` - Fixed config flow bug (bug fix)
- `v1.0.0` - First stable release (major milestone)

## Validation Workflow

On every push/PR to main branches, GitHub Actions validates:

- ✅ HACS compatibility
- ✅ Home Assistant integration standards (hassfest)
- ✅ manifest.json validity
- ✅ hacs.json validity
- ✅ Python syntax
- ✅ Code quality checks

## Manual Release (If Needed)

If you need to create a release manually:

1. Go to https://github.com/Tsopic/battery_energy_trading/releases/new
2. Choose tag: `v0.4.0` (or create new tag)
3. Set release title: `Battery Energy Trading v0.4.0`
4. Add release notes (copy from CHANGELOG.md)
5. Upload `battery_energy_trading-0.4.0.zip`
6. Click "Publish release"

## Troubleshooting

### Release Workflow Not Triggering

**Fixed as of October 2025**: The repository now uses `repository_dispatch` events to trigger releases automatically. If you encounter issues:

1. Check that both workflows are up to date:
   - `.github/workflows/auto-release.yml` - dispatches `tag-created` event
   - `.github/workflows/release.yml` - listens for `repository_dispatch`

2. Verify workflow logs show:
   ```
   Dispatched tag-created event for v0.X.Y
   ```

3. If release still doesn't trigger, manually trigger it:
   ```bash
   gh workflow run release.yml -f tag=v0.X.Y
   ```

**Root cause**: GitHub prevents `GITHUB_TOKEN` from triggering workflows to avoid infinite loops. Solution: Use `repository_dispatch` which is an exception to this rule.

### Tag Already Exists

```bash
# Delete local tag
git tag -d v0.4.0

# Delete remote tag
git push origin :refs/tags/v0.4.0

# Recreate and push
git tag -a v0.4.0 -m "Release v0.4.0"
git push origin v0.4.0
```

### Version Mismatch Error

If the workflow fails with version mismatch:

1. Update manifest.json to match the tag
2. Commit and push the change
3. Delete and recreate the tag
4. Push the tag again

### Release Failed

1. Check workflow logs in GitHub Actions
2. Fix any errors
3. Delete the failed release (if created)
4. Re-run the workflow:
   ```bash
   gh workflow run release.yml -f tag=v0.X.Y
   ```

## Post-Release

After a successful release:

1. ✅ Announce in Home Assistant community forums
2. ✅ Update README.md if needed
3. ✅ Close related GitHub issues
4. ✅ Monitor for user feedback

## Example: Complete Release Flow

```bash
# 1. Update version
vim custom_components/battery_energy_trading/manifest.json
# Change version to "0.4.0"

# 2. Update changelog
vim CHANGELOG.md
# Add version 0.4.0 section

# 3. Commit
git add custom_components/battery_energy_trading/manifest.json CHANGELOG.md
git commit -m "chore: bump version to 0.4.0"
git push origin main

# 4. Create and push tag
git tag -a v0.4.0 -m "Release v0.4.0: Sungrow auto-detection"
git push origin v0.4.0

# 5. Wait for GitHub Actions to complete
# 6. Verify release at github.com/Tsopic/battery_energy_trading/releases

# Done! 🎉
```

## Release Checklist

Before creating a release:

- [ ] All tests passing
- [ ] Version updated in manifest.json
- [ ] CHANGELOG.md updated
- [ ] Documentation updated (if needed)
- [ ] README.md updated (if needed)
- [ ] No uncommitted changes
- [ ] On main/master branch

After creating release:

- [ ] Release appears on GitHub
- [ ] Archive downloads correctly
- [ ] Release notes are accurate
- [ ] HACS will detect it (wait 24h)
- [ ] Announce to community
