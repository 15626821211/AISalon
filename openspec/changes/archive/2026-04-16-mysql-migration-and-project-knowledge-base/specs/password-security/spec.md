## ADDED Requirements

### Requirement: Password hashing on registration
The system SHALL hash user passwords using `werkzeug.security.generate_password_hash` before storing in the database. Plaintext passwords SHALL NOT be stored.

#### Scenario: User registers with password
- **WHEN** a user registers with password "mypassword123"
- **THEN** the stored `password_hash` SHALL NOT equal "mypassword123"
- **THEN** `check_password_hash(stored_hash, "mypassword123")` SHALL return True

### Requirement: Password verification on login
The system SHALL verify login passwords using `werkzeug.security.check_password_hash` against the stored hash.

#### Scenario: Correct password login
- **WHEN** a user logs in with the correct password
- **THEN** the system SHALL authenticate successfully and create a session

#### Scenario: Incorrect password login
- **WHEN** a user logs in with an incorrect password
- **THEN** the system SHALL return 401 with error message "用户名或密码错误"
