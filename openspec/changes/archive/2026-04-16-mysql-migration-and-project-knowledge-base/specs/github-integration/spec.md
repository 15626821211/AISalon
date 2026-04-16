## ADDED Requirements

### Requirement: Fetch repository file tree
The system SHALL retrieve the complete file tree of a GitHub repository using the GitHub REST API (`GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1`).

#### Scenario: Public repository
- **WHEN** analyzing a public GitHub repository
- **THEN** the system SHALL successfully retrieve the file tree without authentication

#### Scenario: Rate-limited request
- **WHEN** GitHub API returns 403 (rate limited)
- **THEN** the system SHALL return an error message indicating GitHub API rate limit exceeded and suggest setting GITHUB_TOKEN

### Requirement: Fetch file contents
The system SHALL retrieve individual file contents using the GitHub REST API (`GET /repos/{owner}/{repo}/contents/{path}`), decoding base64-encoded content.

#### Scenario: Read a markdown file
- **WHEN** fetching a README.md file
- **THEN** the system SHALL return the decoded UTF-8 text content

#### Scenario: Binary file skipped
- **WHEN** encountering a binary file (image, archive, etc.)
- **THEN** the system SHALL skip it without error

### Requirement: Intelligent file selection
The system SHALL apply a file selection strategy to choose the most relevant files for AI analysis, keeping total content under 100KB.

#### Scenario: File priority selection
- **WHEN** scanning a repository file tree
- **THEN** the system SHALL prioritize in order: README.md → docs/*.md → configuration files (package.json, pyproject.toml, requirements.txt, Dockerfile) → core source files (src/*, app/*, lib/*)
- **THEN** the system SHALL skip: node_modules/*, .git/*, __pycache__/*, binary files, image files

#### Scenario: Content size limit
- **WHEN** total selected file content exceeds 100KB
- **THEN** the system SHALL truncate the least-priority files to stay within the limit

### Requirement: Parse GitHub URL
The system SHALL parse a GitHub URL (e.g., `https://github.com/owner/repo`) to extract owner and repo name.

#### Scenario: Standard GitHub URL
- **WHEN** given URL `https://github.com/myorg/myrepo`
- **THEN** the system SHALL extract owner="myorg" and repo="myrepo"

#### Scenario: GitHub URL with trailing slash or .git
- **WHEN** given URL `https://github.com/myorg/myrepo.git` or `https://github.com/myorg/myrepo/`
- **THEN** the system SHALL correctly extract owner="myorg" and repo="myrepo"
