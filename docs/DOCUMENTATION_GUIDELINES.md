# Documentation Guidelines

Guidelines for creating, organizing, and maintaining documentation in the Battery Energy Trading project.

**Last Updated**: 2025-10-02

---

## Table of Contents

1. [Documentation Structure](#documentation-structure)
2. [File Naming Conventions](#file-naming-conventions)
3. [Directory Organization](#directory-organization)
4. [Writing Guidelines](#writing-guidelines)
5. [When to Archive Documentation](#when-to-archive-documentation)
6. [Index Files](#index-files)
7. [Cross-References and Links](#cross-references-and-links)
8. [Maintenance Workflow](#maintenance-workflow)

---

## Documentation Structure

### Root Level Documentation

Files in the project root should be:
- **Essential project files**: README.md, CHANGELOG.md, LICENSE, INSTALLATION.md
- **Project meta-documentation**: CLAUDE.md (AI guidelines), DOCUMENTATION_AUDIT.md (planning)
- **Temporary project-specific**: Keep to minimum, archive when complete

**What NOT to put in root**:
- ❌ Implementation logs (move to `docs/development/history/`)
- ❌ Temporary todo lists (use issue tracker instead)
- ❌ Refactoring notes (move to `docs/development/history/` when done)
- ❌ Test results logs (move to `docs/development/history/`)

### Documentation Directory (`docs/`)

```
docs/
├── README.md                          # Master documentation index
├── TERMINOLOGY.md                     # Key concepts glossary
│
├── user-guide/                        # End-user documentation
│   ├── README.md                      # User guide index
│   ├── dashboard-setup.md
│   └── dashboard-entity-reference.md
│
├── integrations/                      # Third-party integration guides
│   ├── README.md                      # Integrations index
│   ├── sungrow.md
│   └── sungrow-reference.md
│
├── development/                       # Developer documentation
│   ├── README.md                      # Development index
│   ├── testing.md
│   ├── manual-testing-checklist.md
│   ├── features.md
│   ├── release-process.md
│   │
│   └── history/                       # Historical implementation logs
│       ├── README.md                  # History index
│       ├── dependency-modernization-2025-10.md
│       ├── refactoring-summary-2025-10.md
│       └── *.md
│
└── api/                               # API reference documentation
    ├── README.md                      # API index
    └── [future API docs]
```

---

## File Naming Conventions

### General Rules

1. **Use kebab-case**: `dashboard-setup.md`, `getting-started.md`
2. **Be descriptive**: `sungrow-integration-guide.md` not `sungrow.md`
3. **Avoid abbreviations**: `configuration.md` not `config.md`
4. **Use `.md` extension**: All documentation in Markdown format

### Historical Documents

Historical implementation logs use date-stamped naming:

**Format**: `{topic}-{yyyy-mm}.md`

**Examples**:
- `dependency-modernization-2025-10.md`
- `refactoring-summary-2025-10.md`
- `multi-peak-implementation-2025-10.md`

**When to use date stamps**:
- Implementation logs/diaries
- Refactoring documentation
- Historical test results
- Migration documentation

**When NOT to use date stamps**:
- Current reference guides
- Ongoing feature documentation
- API documentation
- User guides

### Index Files

Every directory MUST have a `README.md` that serves as an index:

**Purpose**:
- Lists all documents in directory
- Provides brief description of each
- Links to related sections
- Guides navigation

**Example structure**:
```markdown
# Section Title

Brief description of this documentation section.

## Available Documents

- **[Document Title](document-name.md)** - Brief description
- **[Another Document](another-document.md)** - Brief description

## Related Sections

- [User Guide](../user-guide/README.md)
- [Development](../development/README.md)
```

---

## Directory Organization

### `docs/user-guide/`

**Purpose**: End-user documentation for installation, configuration, and usage

**Contains**:
- Installation guides
- Configuration wizards
- Dashboard setup
- Troubleshooting
- Entity reference lists

**Does NOT contain**:
- Code architecture
- Development setup
- Test documentation
- Implementation details

### `docs/integrations/`

**Purpose**: Third-party integration guides (inverters, battery systems)

**Contains**:
- Integration setup guides
- Entity reference documentation
- Automation examples
- Hardware specifications

**Naming pattern**: `{system-name}.md` for guides, `{system-name}-reference.md` for entity references

### `docs/development/`

**Purpose**: Developer documentation for contributing and extending

**Contains**:
- Development environment setup
- Testing guides
- Feature documentation
- Release process
- Architecture overview

**Does NOT contain**:
- Historical logs (use `history/` subdirectory)
- Temporary planning documents
- Implementation diaries

### `docs/development/history/`

**Purpose**: Historical implementation logs and context

**Contains**:
- Completed implementation logs
- Refactoring documentation
- Migration guides (when complete)
- Test result archives
- Code review notes

**When to move here**:
1. Implementation is complete
2. Document is a log/diary format
3. Information is context, not current guidance
4. Document describes "how we got here" vs "how to do it"

### `docs/api/`

**Purpose**: Technical API documentation and code reference

**Contains** (future):
- Class and method documentation
- API signatures and parameters
- Code examples
- Integration patterns

---

## Writing Guidelines

### Structure

1. **Start with a title**: Clear H1 heading
2. **Add metadata**: Last updated date for reference docs
3. **Include TOC**: For documents >100 lines
4. **Use sections**: Clear H2/H3 hierarchy
5. **End with links**: Related documentation, next steps

### Style

- **Be concise**: Get to the point quickly
- **Use examples**: Show, don't just tell
- **Code blocks**: Always specify language for syntax highlighting
- **Screenshots**: Use sparingly, describe in alt text
- **Callouts**: Use blockquotes for important notes

**Example callout**:
```markdown
> **Note**: This feature requires Home Assistant 2024.1.0 or newer.
```

### Technical Writing

- **Use present tense**: "The optimizer selects slots" not "will select"
- **Use active voice**: "Configure the entity" not "The entity should be configured"
- **Be specific**: "Set to 10kW" not "Set to a high value"
- **Define terms**: Link to `TERMINOLOGY.md` for domain-specific terms

### Code Examples

Always include:
1. **Language identifier**: ```python, ```yaml, ```bash
2. **Comments**: Explain non-obvious parts
3. **Complete examples**: Show full context when possible
4. **Working code**: Test examples before documenting

**Good example**:
```yaml
# automation.yaml
automation:
  - alias: "Battery - Forced Discharge"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
        to: "on"
    action:
      - service: select.select_option
        target:
          entity_id: select.sungrow_ems_mode
        data:
          option: "Forced Mode"
```

---

## When to Archive Documentation

### Move to `docs/development/history/` when:

1. **Implementation is complete**
   - Feature has been implemented and tested
   - No ongoing development work
   - Document served as planning/implementation log

2. **Document is historical context**
   - Describes why decisions were made
   - Implementation diary or log format
   - Useful for understanding evolution, not current usage

3. **Information is outdated**
   - Describes old implementation approach
   - Superseded by newer documentation
   - Still valuable as historical reference

### Keep in main docs when:

1. **Information is actively used**
   - Reference material for current features
   - How-to guides for users/developers
   - Part of daily workflow

2. **Document will be updated**
   - Living documentation
   - Ongoing feature documentation
   - Current best practices

3. **Required for onboarding**
   - New user setup guides
   - Developer getting started
   - Core concepts and architecture

### Examples

**Archive these**:
- ✅ "Multi-peak Discharge Implementation Log (2025-10)"
- ✅ "Dependency Modernization Process"
- ✅ "Refactoring Summary - Base Entity Helpers"
- ✅ "Test Results - October 2025"

**Keep these**:
- ✅ "Testing Guide" (actively used)
- ✅ "Features Documentation" (living document)
- ✅ "Release Process" (ongoing workflow)
- ✅ "Dashboard Setup" (user onboarding)

---

## Index Files

Every directory MUST have a `README.md` index file.

### Index File Requirements

1. **Section title** - Clear H1 heading
2. **Section description** - What this documentation covers
3. **Document list** - All docs in directory with descriptions
4. **Navigation links** - Links to parent/sibling sections
5. **Quick reference** - Optional quick links for common tasks

### Index File Template

```markdown
# Section Title

Brief description of what this documentation section covers.

## Available Documents

- **[Document Title](document-name.md)** - Brief description
- **[Another Document](another-name.md)** - Brief description

## Quick Reference

Optional section for frequently accessed content.

## Related Sections

- [Parent Section](../README.md)
- [Sibling Section](../sibling/README.md)
```

### Updating Index Files

**When to update**:
- Adding new documentation
- Removing outdated documentation
- Restructuring sections
- Changing document names

**What to update**:
1. Document list (add/remove entries)
2. Descriptions (keep current)
3. Links (verify still valid)
4. Related sections (add new cross-refs)

---

## Cross-References and Links

### Relative Links

Always use relative paths, not absolute URLs:

**Good**:
```markdown
[Testing Guide](../development/testing.md)
[Installation](../../INSTALLATION.md)
```

**Bad**:
```markdown
[Testing Guide](https://github.com/Tsopic/battery_energy_trading/blob/main/docs/development/testing.md)
```

### Section Links

Link to specific sections when possible:

```markdown
[Installation Prerequisites](../../INSTALLATION.md#prerequisites)
[Running Tests](../development/testing.md#running-tests)
```

### Updating Links

**When moving/renaming files**:
1. Use search to find all references
2. Update all cross-references
3. Verify links work after move
4. Update index files

**Search command**:
```bash
# Find all references to a file
grep -r "sungrow.md" docs/
```

---

## Maintenance Workflow

### When Adding New Documentation

1. **Choose correct directory**
   - User guide? → `docs/user-guide/`
   - Integration? → `docs/integrations/`
   - Developer? → `docs/development/`
   - API? → `docs/api/`

2. **Follow naming convention**
   - Kebab-case: `feature-name.md`
   - Descriptive: `sungrow-integration-guide.md`
   - Historical: `implementation-2025-10.md`

3. **Update index file**
   - Add entry to directory `README.md`
   - Include brief description
   - Maintain alphabetical or logical order

4. **Update master index**
   - Add to `docs/README.md` if major document
   - Update relevant section index

5. **Cross-reference**
   - Link from related documents
   - Add to relevant navigation

### When Archiving Documentation

1. **Move to history**
   ```bash
   mv docs/development/implementation-log.md \
      docs/development/history/implementation-log-2025-10.md
   ```

2. **Update date stamp**
   - Add `{yyyy-mm}` to filename
   - Update "Last Updated" metadata

3. **Update index files**
   - Remove from current section index
   - Add to history index
   - Update master index if needed

4. **Update cross-references**
   - Search for references to file
   - Update or remove links
   - Add "archived" note if keeping reference

5. **Add archive note**
   - Add note at top of archived file:
     ```markdown
     > **Note**: This document has been archived as of 2025-10-02.
     > For current documentation, see [Testing Guide](../testing.md).
     ```

### When Removing Documentation

1. **Verify safe to delete**
   - Check for cross-references
   - Confirm no valuable unique info
   - Ensure content exists elsewhere

2. **Search for references**
   ```bash
   grep -r "filename.md" docs/
   ```

3. **Remove references**
   - Update index files
   - Remove cross-references
   - Update navigation

4. **Delete file**
   ```bash
   rm docs/path/to/file.md
   ```

### Regular Maintenance

**Quarterly review**:
- [ ] Verify all links work
- [ ] Update outdated information
- [ ] Archive completed implementation logs
- [ ] Remove temporary documentation
- [ ] Update index files
- [ ] Check for duplicate content

**Before each release**:
- [ ] Update CHANGELOG.md
- [ ] Review user-facing documentation
- [ ] Update version numbers
- [ ] Verify installation guide is current
- [ ] Test all code examples

---

## Examples

### Good Documentation Practices

✅ **Clear structure**:
```markdown
# Dashboard Setup Guide

Complete guide for installing and configuring the dashboard.

## Prerequisites

- Battery Energy Trading integration installed
- Nord Pool integration configured

## Installation

1. Copy dashboard YAML...
```

✅ **Descriptive filenames**:
- `dashboard-setup-guide.md`
- `sungrow-integration-guide.md`
- `manual-testing-checklist.md`

✅ **Proper archiving**:
- `docs/development/history/refactoring-summary-2025-10.md`
- `docs/development/history/test-results-2025-10.md`

### Bad Documentation Practices

❌ **Poor structure**:
```markdown
# Setup

Here's how to setup...
(no prerequisites, no sections, jumps right in)
```

❌ **Vague filenames**:
- `guide.md`
- `setup.md`
- `notes.md`

❌ **Root clutter**:
- `REFACTORING_NOTES.md` (should be archived)
- `todo.md` (should be in issue tracker)
- `TEST_RESULTS.md` (should be archived)

---

## Documentation Checklist

Use this checklist when creating or updating documentation:

### New Document
- [ ] File in correct directory (`user-guide/`, `development/`, etc.)
- [ ] Follows naming convention (kebab-case, descriptive)
- [ ] Has clear title (H1)
- [ ] Includes TOC if >100 lines
- [ ] Uses proper markdown formatting
- [ ] Code examples have language specified
- [ ] Updated directory `README.md` index
- [ ] Updated `docs/README.md` master index (if major doc)
- [ ] Links use relative paths
- [ ] Cross-referenced from related docs

### Archiving Document
- [ ] Moved to `docs/development/history/`
- [ ] Added date stamp to filename (`-2025-10.md`)
- [ ] Added archive note at top of document
- [ ] Updated all cross-references
- [ ] Removed from current section index
- [ ] Added to history index
- [ ] Verified no broken links

### Removing Document
- [ ] Verified safe to delete (content exists elsewhere)
- [ ] Searched for all references
- [ ] Updated/removed cross-references
- [ ] Updated index files
- [ ] Committed deletion with clear message

---

## Questions?

For questions about documentation:

1. Check existing documentation in `docs/`
2. Review this guidelines document
3. Look at recent commits for examples
4. Ask in GitHub Discussions

For suggesting improvements to these guidelines:

- Open a GitHub Issue with label `documentation`
- Submit a Pull Request with proposed changes
