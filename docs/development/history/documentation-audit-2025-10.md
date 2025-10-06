# Documentation Audit & Cleanup Plan

**Date**: 2025-10-02
**Status**: Planning

## Current Documentation Inventory

### Root Level Documentation (9 files)

| File | Lines | Purpose | Status | Action |
|------|-------|---------|--------|--------|
| `README.md` | 522 | Main project overview | ✅ Keep | Update |
| `CHANGELOG.md` | 257 | Version history | ✅ Keep | Current |
| `CLAUDE.md` | 527 | AI assistant guidelines | ✅ Keep | Update |
| `INSTALLATION.md` | 251 | Install guide | ✅ Keep | New, current |
| `RUNNING_TESTS.md` | 184 | Test execution guide | ⚠️ Consolidate | Merge to docs/development/testing.md |
| `DEPENDENCY_MODERNIZATION.md` | 347 | Dependency upgrade log | ⚠️ Archive | Move to docs/development/history/ |
| `MODERNIZATION_SUMMARY.md` | 493 | Complete modernization overview | ⚠️ Archive | Move to docs/development/history/ |
| `REFACTORING_SUMMARY.md` | 300 | Refactoring documentation | ⚠️ Archive | Move to docs/development/history/ |
| `TERMINOLOGY_REFACTORING.md` | 275 | Terminology changes log | ⚠️ Archive | Move to docs/development/history/ |
| `TESTING_IMPLEMENTATION_SUMMARY.md` | 417 | Test implementation log | ⚠️ Archive | Move to docs/development/history/ |
| `todo.md` | 62 | Task list | ❌ Remove | Temporary file |

### docs/ Directory (19 files)

#### Top Level (3 files)
| File | Lines | Purpose | Status | Action |
|------|-------|---------|--------|--------|
| `docs/README.md` | 85 | Documentation index | ⚠️ Outdated | Rebuild |
| `docs/TERMINOLOGY_CLARIFICATION.md` | 215 | Slot vs hours explanation | ✅ Keep | Current |
| `docs/DASHBOARD_ENTITY_IDS.md` | 95 | Dashboard entity reference | ⚠️ Consolidate | Merge to dashboard-setup-guide.md |
| `docs/dashboard-setup-guide.md` | 194 | Dashboard setup instructions | ✅ Keep | Update |

#### docs/development/ (9 files)
| File | Lines | Purpose | Status | Action |
|------|-------|---------|--------|--------|
| `docs/development/features.md` | 326 | Feature documentation | ✅ Keep | Update |
| `docs/development/testing.md` | 96 | Testing guide | ✅ Keep | Expand with RUNNING_TESTS.md |
| `docs/development/release-process.md` | 266 | Release workflow | ✅ Keep | Current |
| `docs/development/test-results.md` | 153 | Test execution log | ⚠️ Archive | Move to history/ |
| `docs/development/code-review-dashboard-entities.md` | 314 | Code review notes | ⚠️ Archive | Move to history/ |
| `docs/development/dashboard-completeness-audit.md` | 367 | Dashboard audit | ⚠️ Archive | Move to history/ |
| `docs/development/multi-peak-discharge-analysis.md` | 554 | Feature analysis | ⚠️ Archive | Move to history/ |
| `docs/development/multi-peak-implementation-summary.md` | 535 | Implementation log | ⚠️ Archive | Move to history/ |
| `docs/development/refactoring-summary.md` | 233 | Refactoring notes | ⚠️ Archive | Move to history/ |
| `docs/development/refactoring-sungrow-entity-detection.md` | 263 | Refactoring log | ⚠️ Archive | Move to history/ |
| `docs/development/refactoring-dashboard-completeness.md` | 475 | Refactoring log | ⚠️ Archive | Move to history/ |

#### docs/integrations/ (2 files)
| File | Lines | Purpose | Status | Action |
|------|-------|---------|--------|--------|
| `docs/integrations/sungrow.md` | 508 | Sungrow integration guide | ✅ Keep | Current |
| `docs/integrations/sungrow-entity-reference.md` | 381 | Sungrow entity reference | ✅ Keep | Current |

#### docs/refactoring/ (2 files)
| File | Lines | Purpose | Status | Action |
|------|-------|---------|--------|--------|
| `docs/refactoring/consolidate-base-entity-helpers.md` | 167 | Refactoring log | ⚠️ Archive | Move to development/history/ |
| `docs/refactoring/manual-testing-guide.md` | 283 | Testing checklist | ⚠️ Consolidate | Merge to development/testing.md |

### Other Locations (2 files)
| File | Lines | Purpose | Status | Action |
|------|-------|---------|--------|--------|
| `dashboards/README.md` | 47 | Dashboard folder readme | ✅ Keep | Current |
| `tests/README.md` | 38 | Test folder readme | ✅ Keep | Current |

## Summary Statistics

- **Total Files**: 32 markdown files
- **Total Lines**: ~9,264 lines of documentation
- **Status Breakdown**:
  - ✅ Keep as-is: 10 files (31%)
  - ⚠️ Archive/Consolidate: 21 files (66%)
  - ❌ Remove: 1 file (3%)

## Issues Identified

### 1. Historical/Temporary Documents Cluttering Root
Files like `DEPENDENCY_MODERNIZATION.md`, `REFACTORING_SUMMARY.md`, etc. are valuable historical records but shouldn't be in the root directory.

### 2. Duplicate Information
- `RUNNING_TESTS.md` vs `docs/development/testing.md`
- `DASHBOARD_ENTITY_IDS.md` vs `dashboard-setup-guide.md`
- Multiple refactoring logs with overlapping information

### 3. Outdated Index
`docs/README.md` doesn't reflect current documentation structure.

### 4. No Clear Documentation Hierarchy
Hard to find specific information - need better organization.

### 5. Temporary Files in Repository
`todo.md` should not be committed.

## Proposed New Structure

```
battery_energy_trading/
├── README.md                           # Main project overview
├── CHANGELOG.md                        # Version history
├── LICENSE                             # License file
├── INSTALLATION.md                     # Installation guide
├── CLAUDE.md                           # AI assistant guidelines
│
├── docs/
│   ├── README.md                       # Documentation index (rebuilt)
│   ├── TERMINOLOGY.md                  # Slot vs hours (renamed)
│   │
│   ├── user-guide/
│   │   ├── README.md                   # User guide index
│   │   ├── installation.md             # Link to root INSTALLATION.md
│   │   ├── configuration.md            # Setup wizard guide
│   │   ├── dashboard-setup.md          # Dashboard setup (from dashboard-setup-guide.md)
│   │   └── troubleshooting.md          # Common issues (new)
│   │
│   ├── integrations/
│   │   ├── README.md                   # Integrations index
│   │   ├── sungrow.md                  # Sungrow guide (current)
│   │   └── sungrow-reference.md        # Entity reference (current)
│   │
│   ├── development/
│   │   ├── README.md                   # Development index
│   │   ├── getting-started.md          # Dev setup (new)
│   │   ├── testing.md                  # Testing guide (expanded)
│   │   ├── features.md                 # Feature docs (current)
│   │   ├── release-process.md          # Release workflow (current)
│   │   ├── architecture.md             # System architecture (new)
│   │   ├── contributing.md             # Contribution guide (new)
│   │   │
│   │   └── history/                    # Historical documents
│   │       ├── README.md               # History index
│   │       ├── dependency-modernization-2025-10.md
│   │       ├── refactoring-base-entity-2025-10.md
│   │       ├── multi-peak-implementation-2025-10.md
│   │       ├── dashboard-completeness-2025-10.md
│   │       └── terminology-refactoring-2025-10.md
│   │
│   └── api/
│       ├── README.md                   # API documentation index
│       ├── energy-optimizer.md         # EnergyOptimizer class
│       ├── sensors.md                  # Sensor entities
│       ├── binary-sensors.md           # Binary sensor entities
│       └── services.md                 # Available services
│
├── dashboards/
│   └── README.md                       # Dashboard documentation (current)
│
└── tests/
    └── README.md                       # Test documentation (current)
```

## Action Plan

### Phase 1: Create New Structure ✅
- [ ] Create new directory structure
- [ ] Create index files (README.md) for each section

### Phase 2: Reorganize Existing Files ✅
- [ ] Move historical documents to `docs/development/history/`
- [ ] Consolidate duplicate documentation
- [ ] Rename files for consistency
- [ ] Update cross-references

### Phase 3: Create Missing Documentation ✅
- [ ] User guide sections (configuration, troubleshooting)
- [ ] Development guide (getting started, architecture, contributing)
- [ ] API documentation

### Phase 4: Update Navigation ✅
- [ ] Rebuild `docs/README.md` as master index
- [ ] Add navigation to all index files
- [ ] Update `CLAUDE.md` with documentation workflow

### Phase 5: Cleanup ✅
- [ ] Remove temporary files (todo.md)
- [ ] Update root README.md with new structure
- [ ] Verify all links work

## Documentation Guidelines (To Be Created)

### File Naming Convention
- Use kebab-case: `user-guide.md`, `getting-started.md`
- Be descriptive: `sungrow-integration-guide.md` not `sungrow.md`
- Historical files: `{topic}-{yyyy-mm}.md` (e.g., `refactoring-2025-10.md`)

### Directory Structure
- `user-guide/` - End-user documentation
- `integrations/` - Third-party integration guides
- `development/` - Developer documentation
- `development/history/` - Historical implementation logs
- `api/` - API and code reference

### Index Files
Every directory must have a `README.md` that:
- Lists all documents in that directory
- Provides brief description of each
- Links to related sections

### Cross-References
- Use relative links: `[Testing Guide](../development/testing.md)`
- Always link to specific sections: `[Installation](#installation)`
- Keep links up to date when moving files

### When to Archive
Move to `history/` when:
- Implementation is complete
- Document is a log/diary of changes
- Information is historical context, not current guidance

### When to Keep in Main Docs
Keep in main docs when:
- Information is actively used
- Document is reference material
- Content is part of user/developer workflow

## Benefits of New Structure

### For Users
✅ Clear separation of user vs developer docs
✅ Easy to find installation and configuration guides
✅ Troubleshooting section for common issues

### For Developers
✅ Development workflow clearly documented
✅ Historical context preserved but organized
✅ API documentation separated from guides

### For Maintenance
✅ Clear guidelines for where to add new docs
✅ Consistent naming and structure
✅ Easy to keep documentation current

## Implementation Checklist

- [ ] Create directory structure
- [ ] Move 21 files to appropriate locations
- [ ] Create 8 new documentation files
- [ ] Update 15+ cross-references
- [ ] Remove 1 temporary file
- [ ] Update CLAUDE.md with workflow
- [ ] Test all documentation links
- [ ] Create DOCUMENTATION_GUIDELINES.md

## Estimated Effort

- **Planning**: 1 hour ✅ (Complete)
- **Reorganization**: 2-3 hours
- **New Documentation**: 3-4 hours
- **Testing/Verification**: 1 hour
- **Total**: 7-9 hours

## Next Steps

1. Get approval for proposed structure
2. Begin Phase 1: Create new directory structure
3. Proceed through phases systematically
4. Document changes in CHANGELOG.md
