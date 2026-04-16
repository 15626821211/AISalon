## ADDED Requirements

### Requirement: Environment variable configuration
The system SHALL read configuration from environment variables, loaded via `python-dotenv` from a `.env` file at the project root.

#### Scenario: All required variables set
- **WHEN** `.env` contains `SECRET_KEY`, `DATABASE_URL`, and `DASHSCOPE_API_KEY`
- **THEN** the application SHALL use these values for Flask secret key, database connection, and AI API authentication respectively

#### Scenario: SECRET_KEY not set
- **WHEN** `SECRET_KEY` is not in environment
- **THEN** the application SHALL use a generated fallback value

### Requirement: Sensitive values never hardcoded
The system SHALL NOT hardcode API keys, database passwords, or secret keys in source code. All sensitive values SHALL come from environment variables.

#### Scenario: Source code review
- **WHEN** inspecting source code files
- **THEN** no literal API keys, database passwords, or secret key values SHALL appear
