## ADDED Requirements

### Requirement: DashScope API integration
The system SHALL call the Aliyun DashScope API using the OpenAI-compatible interface at `https://dashscope.aliyuncs.com/compatible-mode/v1` with model `qwen-plus`.

#### Scenario: Successful API call
- **WHEN** sending a prompt to the DashScope API with valid DASHSCOPE_API_KEY
- **THEN** the system SHALL receive a text response and return it

#### Scenario: API key missing
- **WHEN** DASHSCOPE_API_KEY is not configured
- **THEN** the system SHALL return an error message "未配置 DASHSCOPE_API_KEY"

#### Scenario: API call failure
- **WHEN** the DashScope API returns an error
- **THEN** the system SHALL log the error and return a user-friendly error message

### Requirement: Multi-step analysis pipeline
The system SHALL analyze a project in 5 sequential steps, each producing a specific knowledge card section.

#### Scenario: Step 1 — Project overview and design thinking
- **WHEN** analyzing with README and documentation content
- **THEN** the system SHALL produce `summary` (one-paragraph overview) and `design_thinking` (design rationale and approach)

#### Scenario: Step 2 — Technology stack analysis
- **WHEN** analyzing with configuration files and framework code
- **THEN** the system SHALL produce `tech_stack` (languages, frameworks, AI models used, and why they were chosen)

#### Scenario: Step 3 — Architecture description
- **WHEN** analyzing with directory structure and core module code
- **THEN** the system SHALL produce `architecture` (system architecture, module relationships, data flow)

#### Scenario: Step 4 — Key code snippets
- **WHEN** analyzing with core source code files
- **THEN** the system SHALL produce `key_code_snippets` as a JSON array, each with `file`, `code`, and `explanation` fields

#### Scenario: Step 5 — Lessons learned
- **WHEN** analyzing with all previous step results and original README
- **THEN** the system SHALL produce `lessons_learned` (reusable insights, pitfalls, best practices)

### Requirement: Analysis result storage
The system SHALL store all analysis results in the project's database record and update `analyzed_at` timestamp and `status` to "analyzed".

#### Scenario: Successful full analysis
- **WHEN** all 5 analysis steps complete successfully
- **THEN** the project record SHALL contain all 6 result fields (summary, design_thinking, tech_stack, architecture, key_code_snippets, lessons_learned) and status SHALL be "analyzed"

#### Scenario: Partial failure
- **WHEN** one analysis step fails mid-pipeline
- **THEN** the system SHALL store completed step results, set status to "partial", and return which step failed

### Requirement: Chinese output
All AI-generated analysis content SHALL be in Chinese (简体中文), matching the platform's user interface language.

#### Scenario: Analysis language
- **WHEN** AI analysis completes for any project
- **THEN** all generated text (summary, design_thinking, tech_stack, architecture, key_code_snippets explanations, lessons_learned) SHALL be in Chinese
