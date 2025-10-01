# Release Process

This document describes how to create a new release of the Battery Energy Trading integration.

## Prerequisites

- Write access to the repository
- All changes merged to main/master branch
- Tests passing
- Documentation updated

## Release Steps

### 1. Update Version

Update the version in `manifest.json`:

```json
{
  "version": "0.4.0"
}
```

### 2. Update CHANGELOG.md

Add a new version section to `CHANGELOG.md`:

```markdown
## [0.4.0] - 2025-01-15

### Added
- Automatic Sungrow inverter detection
- One-click auto-configuration for Sungrow users
- Service to sync Sungrow parameters
- Comprehensive test suite

### Changed
- Enhanced config flow with intelligent routing
- Number entities now use auto-detected rates

### Fixed
- (list any bug fixes)
```

### 3. Commit Changes

```bash
git add custom_components/battery_energy_trading/manifest.json CHANGELOG.md
git commit -m "chore: bump version to 0.4.0"
git push origin main
```

### 4. Create and Push Tag

```bash
# Create annotated tag
git tag -a v0.4.0 -m "Release v0.4.0"

# Push tag to trigger release workflow
git push origin v0.4.0
```

### 5. Automated Release

The GitHub Actions workflow will automatically:
1. ✅ Verify version in manifest.json matches tag
2. ✅ Extract changelog for this version
3. ✅ Create release archive (.zip)
4. ✅ Generate release notes
5. ✅ Create GitHub Release
6. ✅ Attach release archive

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
3. Delete the failed release
4. Delete and recreate the tag
5. Push again

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
