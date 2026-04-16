## ADDED Requirements

### Requirement: Project CRUD operations
The system SHALL support creating, reading, updating, and deleting AI projects via REST API under `/projects/`.

#### Scenario: Create a new project
- **WHEN** a logged-in user POSTs to `/projects/` with `{name, github_url, team, wiki_url, tags}`
- **THEN** the system SHALL create a project with status "draft" and return 201 with project data

#### Scenario: List all projects
- **WHEN** a user GETs `/projects/`
- **THEN** the system SHALL return a JSON array of all projects with their basic info and analysis status

#### Scenario: Get project detail
- **WHEN** a user GETs `/projects/<id>`
- **THEN** the system SHALL return the full project data including all analysis fields

#### Scenario: Update project info
- **WHEN** the project creator PUTs to `/projects/<id>` with updated fields
- **THEN** the system SHALL update the project and return 200

#### Scenario: Delete project
- **WHEN** the project creator DELETEs `/projects/<id>`
- **THEN** the system SHALL delete the project and return 204

### Requirement: Project list page
The system SHALL render a project list page at `/projects/page` showing all projects as cards with name, team, tags, status, and summary preview.

#### Scenario: View project list
- **WHEN** a logged-in user navigates to `/projects/page`
- **THEN** the page SHALL display all projects as cards in a grid layout
- **THEN** each card SHALL show project name, team, tags, and analysis status

#### Scenario: Filter projects by tag
- **WHEN** a user clicks a tag on the project list page
- **THEN** the list SHALL filter to show only projects with that tag

### Requirement: Project knowledge card page
The system SHALL render a project detail page at `/projects/<id>/page` showing the full knowledge card with all analysis sections.

#### Scenario: View analyzed project
- **WHEN** a user navigates to `/projects/<id>/page` for an analyzed project
- **THEN** the page SHALL display: 项目概览, 设计思路, 技术选型, 架构描述, 核心代码解读, 经验教训
- **THEN** each section SHALL render markdown-formatted content

#### Scenario: View draft project
- **WHEN** a user navigates to `/projects/<id>/page` for a draft (unanalyzed) project
- **THEN** the page SHALL show basic info and a "开始分析" button

### Requirement: Project discussion
The system SHALL support comments on projects, accessible via `/projects/<id>/comments` (GET/POST).

#### Scenario: Post a comment
- **WHEN** a logged-in user POSTs to `/projects/<id>/comments` with `{content}`
- **THEN** the comment SHALL be saved and return 201

#### Scenario: View comments
- **WHEN** a user GETs `/projects/<id>/comments`
- **THEN** the system SHALL return all comments for that project with username, content, and timestamp

### Requirement: Trigger AI analysis
The system SHALL support manually triggering AI analysis via POST `/projects/<id>/analyze`. Only the project creator SHALL be able to trigger analysis.

#### Scenario: Trigger analysis on draft project
- **WHEN** the project creator POSTs to `/projects/<id>/analyze`
- **THEN** the system SHALL fetch GitHub content, run AI analysis, store results, update status to "analyzed", and return 200

#### Scenario: Re-analyze project
- **WHEN** the project creator POSTs to `/projects/<id>/analyze` on an already analyzed project
- **THEN** the system SHALL re-run analysis, overwrite previous results, and update `analyzed_at`

#### Scenario: Non-creator triggers analysis
- **WHEN** a non-creator POSTs to `/projects/<id>/analyze`
- **THEN** the system SHALL return 403 with message "只有项目创建者可触发分析"

### Requirement: Navigation integration
The system SHALL add a "项目知识库" link in the navigation bar, visible to all logged-in users.

#### Scenario: Logged-in user sees navigation
- **WHEN** a logged-in user views any page
- **THEN** the navigation bar SHALL include a "项目知识库" link pointing to `/projects/page`
