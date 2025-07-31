# gh-tagger

A GitHub Composite Action to validate a version against SemVer rules and create a Git tag.

## Inputs

| Name               | Required | Default | Description                                                                 |
|--------------------|----------|---------|-----------------------------------------------------------------------------|
| `version`          | Yes      | -       | Version string (e.g., `v1.0.0`, `2.3.4-rc.1`).                             |
| `allow-empty-prefix`| No       | `false` | If `true`, allows versions without `v` prefix (e.g., `1.0.0`).             |

## Usage

### Example Workflow (Manual Trigger)
```yaml
name: Manual Tag Validation

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version (e.g., v1.0.0, 2.3.4-rc.1)'
        required: true

jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - name: Validate and tag
        uses: midnattsol/gh-tagger@main
        with:
          version: ${{ inputs.version }}