# Contributing to BlueHub

## Development Guidelines

### Coding Standards

- **Python:** Follow PEP 8 and PEP 257 conventions
  - Use `black` for code formatting (line length 100)
  - Use `ruff` for linting
  - Use `mypy` for type checking
  - Use `isort` for import sorting
- **TypeScript/React:** Follow project ESLint and Prettier configs
- **Documentation:** Write docstrings for all public functions and classes
- **Testing:** Write unit tests for all new features using pytest
- **Migrations:** Always create Alembic migrations for schema changes

### Branch Strategy

- `main` - Production-ready code (protected)
- `dev` - Active development branch
- `legacy` - Archived legacy bot code
- Feature branches: `feature/TASK-XXX-description`
- Bug fixes: `fix/TASK-XXX-description`

### Commit Convention

Follow conventional commits:
```
feat: Add user authentication
fix: Resolve database connection timeout
docs: Update API documentation
test: Add unit tests for billing module
refactor: Reorganize module structure
chore: Update dependencies
```

### Pull Request Process

1. Create a feature branch from `dev`
2. Implement changes with tests
3. Run `black .`, `ruff check .`, and `pytest` before committing
4. Submit PR to `dev` with description and linked task
5. Ensure CI checks pass
6. Request code review from maintainer
7. Squash merge to `dev` after approval

### Project Structure Conventions

- **API routes:** Place route handlers in `api/v1/<module>.py`
- **Business logic:** Place in `core/<module>/service.py`
- **Schemas:** Place in `core/<module>/schemas.py` or `shared/schemas/`
- **Models:** Place in `shared/models/` for shared ORM models
- **Module-specific models:** Place in `modules/<module>/models.py`
- **Tests:** Mirror source structure in `tests/unit/` and `tests/integration/`

### Testing

Run tests:
```bash
# All tests
python run_tests.py

# Specific test file
pytest tests/unit/test_auth.py -v

# With coverage
pytest --cov=. --cov-report=html
```

### Database Migrations

```bash
# Create migration (auto-generate)
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

Hooks configured:
- `black` - Code formatting
- `ruff` - Linting
- `mypy` - Type checking (for staged Python files)

## Getting Help

For questions about the project architecture or development workflow, refer to:
- `ARCHITECTURE_UPDATE_SUMMARY.md` - Architecture overview
- `GETTING_STARTED.md` - Initial setup guide
- `.Blue/specs/tasks.md` - Task tracking and implementation plan