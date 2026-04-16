## ADDED Requirements

### Requirement: MySQL database persistence for all entities
The system SHALL store all data (users, events, signups, comments, projects) in MySQL via SQLAlchemy ORM. In-memory dict storage SHALL be fully replaced.

#### Scenario: Application startup creates tables
- **WHEN** the Flask application starts
- **THEN** all database tables SHALL be created if they do not exist (via `db.create_all()`)

#### Scenario: User data persists across restarts
- **WHEN** a user registers and the application restarts
- **THEN** the user account SHALL still exist and be queryable

#### Scenario: Event data persists across restarts
- **WHEN** an event is created and the application restarts
- **THEN** the event SHALL still exist with all its data (title, description, tags, signups, comments)

### Requirement: Database connection configuration
The system SHALL read the MySQL connection string from the `DATABASE_URL` environment variable. The format SHALL be `mysql+pymysql://user:pass@host:port/db`.

#### Scenario: Valid connection string
- **WHEN** `DATABASE_URL` is set to `mysql+pymysql://root:root@localhost:3306/ai_salon`
- **THEN** the application SHALL connect to the specified MySQL database

#### Scenario: Missing connection string
- **WHEN** `DATABASE_URL` is not set
- **THEN** the application SHALL fall back to `mysql+pymysql://root:root@localhost:3306/ai_salon`

### Requirement: ORM model definitions
The system SHALL define SQLAlchemy models in a unified `src/models.py` file to avoid circular imports. Models SHALL include: User, Event, EventSignup, EventComment, Project, ProjectComment.

#### Scenario: Model relationships
- **WHEN** querying a User
- **THEN** the system SHALL be able to access the user's events, signups, and comments via relationship attributes

### Requirement: Service layer adaptation
All existing Service classes (EventService, UserService) SHALL be refactored to use SQLAlchemy session operations instead of in-memory dict operations, preserving all existing API behavior.

#### Scenario: EventService CRUD via ORM
- **WHEN** calling `EventService.create_event_from_dict(data)`
- **THEN** the event SHALL be persisted to the MySQL events table and returned as a dict

#### Scenario: UserService CRUD via ORM
- **WHEN** calling `UserService.register(username, password)`
- **THEN** the user SHALL be persisted to the MySQL users table with hashed password
