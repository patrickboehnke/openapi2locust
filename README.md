# OpenAPI2Locust

🚀 **Generate Locust load testing scripts from OpenAPI 3.0 specifications**

OpenAPI2Locust is a powerful Python tool that automatically converts OpenAPI 3.0 specifications into ready-to-use [Locust](https://locust.io/) load testing scripts. It handles authentication, request generation, and response validation while following security best practices.

## ✨ Features

- **🔄 Full OpenAPI 3.0 Support**: Parses paths, parameters, request bodies, and responses
- **🔐 Authentication Handling**: Supports API Key, Bearer Token, Basic Auth, and OAuth2
- **🛡️ Security First**: Built-in security headers and input sanitization
- **⚙️ Configurable**: YAML/JSON configuration files for customization
- **🧪 Test Data Generation**: Automatic fake data generation based on schemas
- **📊 Smart Load Distribution**: Configurable task weights based on HTTP methods
- **🎯 Response Validation**: Automatic response structure validation
- **📝 Comprehensive Logging**: Professional logging with configurable levels

## 🚀 Quick Start

### Installation

```bash
pip install openapi2locust
```

### Basic Usage

```bash
# Generate from OpenAPI spec
openapi2locust api-spec.yaml

# Custom output directory and filename
openapi2locust api-spec.yaml -o ./tests -f my_loadtest.py

# Use configuration file
openapi2locust api-spec.yaml -c config.yaml

# Validate spec only
openapi2locust api-spec.yaml --validate-only
```

### Run Generated Tests

```bash
# Run the load test
locust -f locustfile_api-spec.py

# Run with specific parameters
locust -f locustfile_api-spec.py --host https://api.example.com -u 10 -r 2
```

## 📖 CLI Reference

### Main Command

```bash
openapi2locust [OPTIONS] SPEC_FILE
```

**Options:**
- `-o, --output PATH`: Output directory (default: current directory)
- `-f, --filename TEXT`: Output filename (default: `locustfile_<spec_name>.py`)
- `-c, --config PATH`: Configuration file path (YAML or JSON)
- `--validate-only`: Only validate the OpenAPI spec
- `-v, --verbose`: Enable verbose logging
- `--help`: Show help message

### Utility Commands

```bash
# Show API information
openapi2locust info api-spec.yaml

# List all endpoints
openapi2locust endpoints api-spec.yaml
```

## ⚙️ Configuration

Create a `config.yaml` file to customize generation:

```yaml
# Output settings
output_dir: "./output"

# Load test parameters
min_wait: 1
max_wait: 5

# Task weights for different HTTP methods
default_weight:
  GET: 10
  POST: 3
  PUT: 2
  DELETE: 1

# Security headers (included by default)
include_security_headers: true
security_headers:
  X-Content-Type-Options: "nosniff"
  X-Frame-Options: "DENY"
  X-XSS-Protection: "1; mode=block"
  Referrer-Policy: "strict-origin-when-cross-origin"
  Cache-Control: "no-cache, no-store, must-revalidate"

# Data generation settings
data_faker:
  locale: "en_US"

# Template options
template:
  add_response_validation: true
  include_test_data_helpers: true
```

## 🔐 Authentication Setup

The tool automatically detects authentication schemes from your OpenAPI spec and generates appropriate setup code.

### Environment Variables

Set these environment variables before running your tests:

```bash
# API Key Authentication
export MY_API_KEY="your-api-key-here"

# Bearer Token
export MY_BEARER_TOKEN="your-bearer-token"

# Basic Authentication
export MY_USERNAME="username"
export MY_PASSWORD="password"

# OAuth2
export MY_ACCESS_TOKEN="your-oauth2-token"
```

### Supported Authentication Types

- **API Key**: Header, query parameter, or cookie-based
- **HTTP Basic**: Username/password authentication
- **HTTP Bearer**: Bearer token authentication
- **OAuth2**: All OAuth2 flows with scope support
- **OpenID Connect**: OIDC token authentication

## 📝 Generated Test Structure

The generated Locust script includes:

```python
class APIUser(HttpUser):
    wait_time = between(1, 3)
    host = "https://api.example.com"
    
    def on_start(self):
        # Authentication setup
        # Test data initialization
        
    @task(10)
    def get_users(self):
        # GET /users endpoint test
        
    @task(3)
    def create_user(self):
        # POST /users endpoint test
        
    # Helper methods for data generation
```

## 🛡️ Security Features

- **Path Traversal Protection**: Secure filename validation
- **Input Sanitization**: HTML escaping and control character removal
- **Security Headers**: Automatic security header injection
- **Safe Defaults**: Secure configuration defaults
- **Authentication Security**: Proper credential handling

## 🧪 Examples

### Basic API

```yaml
# api-spec.yaml
openapi: 3.0.0
info:
  title: User API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: Success
    post:
      summary: Create user
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                email:
                  type: string
      responses:
        '201':
          description: Created
```

### Generated Output

```python
import random
import logging
from locust import HttpUser, task, between

class UserAPIUser(HttpUser):
    """Load test for User API"""
    
    wait_time = between(1, 3)
    host = "http://localhost"
    
    def on_start(self):
        """Setup authentication and initial data."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_test_data()
    
    @task(10)
    def get_users(self):
        """List users"""
        headers = {
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }
        
        response = self.client.get(
            "/users",
            headers=headers,
            name="GET /users"
        )
        
        if response.status_code in [200]:
            pass
        else:
            self.logger.error(f"Unexpected status code {response.status_code} for GET /users")
    
    @task(3)
    def post_users(self):
        """Create user"""
        headers = {
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }
        
        data = {"name": "John Doe", "email": "john@example.com"}
        
        response = self.client.post(
            "/users",
            headers=headers,
            json=data,
            name="POST /users"
        )
        
        if response.status_code in [201]:
            pass
        else:
            self.logger.error(f"Unexpected status code {response.status_code} for POST /users")
```

## 🏗️ Architecture

```
openapi2locust/
├── cli.py              # Command-line interface
├── generator.py        # Main script generation logic
├── parser.py           # OpenAPI specification parser
├── auth_handler.py     # Authentication handling
├── data_faker.py       # Test data generation
├── config.py           # Configuration management
└── templates/
    └── locustfile.py.j2 # Jinja2 template for Locust scripts
```

## 🔧 Development

### Setup

```bash
git clone <repository-url>
cd openapi2locust
pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=openapi2locust

# Run specific test file
pytest tests/test_generator.py
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
flake8 src/

# Formatting
black src/
```

## 📚 Advanced Usage

### Custom Templates

You can customize the generated Locust scripts by modifying the Jinja2 template or providing your own.

### Performance Tuning

- Adjust task weights in configuration
- Modify wait times for different load patterns
- Configure data generation parameters
- Enable/disable response validation for performance

### Integration

OpenAPI2Locust can be integrated into CI/CD pipelines:

```bash
# Generate and run tests in pipeline
openapi2locust api-spec.yaml -o tests/
locust -f tests/locustfile_api-spec.py --headless -u 50 -r 10 -t 300s
```

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

### Areas for Contribution

- Additional authentication schemes
- More data generation strategies  
- Template customization options
- Performance optimizations
- Documentation improvements

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Issues and Support

- **Bug Reports**: Open an issue with detailed reproduction steps
- **Feature Requests**: Describe the use case and expected behavior
- **Questions**: Check existing issues or open a new discussion

## 🙏 Acknowledgments

- [Locust](https://locust.io/) - Modern load testing framework
- [OpenAPI Initiative](https://www.openapis.org/) - API specification standard
- [Faker](https://faker.readthedocs.io/) - Test data generation library
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine

---

**Happy Load Testing!** 🚀
