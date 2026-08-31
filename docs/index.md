# Fathom: Manage the Release of Documentation

## Introduction

Fathom is a tool for automatically deploying built documentation resources of your software projects to a central location. It provides a simple way to publish and maintain documentation across multiple projects, making it easy to keep your documentation accessible and up-to-date.

The Fathom project consists of three main components:

- **Client**: A Python command-line application that packages and deploys documentation. Also provides an API for programmatic interaction.
- **Server**: A web server application that receives and deploys documentation resources to the appropriate location.
- **Base Package**: Common code shared between client and server.

Fathom simplifies the documentation release workflow by:

- **Automating deployment**: Package and deploy with a single command
- **Centralizing documentation**: Deploy multiple projects to a single documentation server
- **Integrating with CI/CD**: Deploy from your build server or GitHub Actions
- **Filtering content**: Selectively include or exclude files based on patterns
- **Version management**: Track documentation versions alongside your project releases
- **User management**: Support for dedicated user authentication to control access

## Installation

### Requirements

- Python 3.10 or higher

## Configuration

### 1. Create a User Configuration

Create a `${HOME}/.config/fathom/user.cfg` configuration file and specify the Fathom servers your system user has access to:

```ini
[User]
logging.enabled=true

[Server-1]
name=MyFathomServer
domain=localhost
username=myuser
password=mypassword
port=8080
transport.secure=false

```

Change the `domain` config entry to the domain name or IP address of your Fathom server. Other entries can optionally be omitted as they come with default values. If you don't specify a username and/or password, you will be prompted to enter those values on the command-line when using the client.

### 2. Create a Project Configuration

Create a `fathom.cfg` file in your project root or under a `docs` subdirectory:

```ini
[Project]
id=my-project
name=My Project
description=A project description
version=1.2.3
domain=docs.example.com
assets=build/site

[Server]
name=MyFathomServer
```

The `assets` configuration entry tells Fathom where the built documentation resources reside.

The specified server will be used by a Fathom client when deploying resources for that project.

For more details on how to configure Fathom, see the [Configuration Documentation](configuration.md).

## Usage

### Basic Deployment

Deploy documentation using command-line options:

```bash
fathom deploy
```

You'll be prompted for your password if you didn't specify the `password` in the configuration file, and then Fathom will package and deploy your documentation resources.

### Examples

#### Deploy from Current Directory

```bash
cd /path/to/my-project
fathom deploy --server https://fathom.example.com --user myuser
```

#### Deploy from Specific Directory

```bash
fathom deploy \
  --server https://fathom.example.com \
  --user myuser \
  --project-directory /path/to/project
```

## Advanced Usage

### Programmatic Usage

You can use Fathom's client API directly in your Python scripts:

```python
from raven.fathom.client import DocumentationResource, DocsDir
from raven.fathom.client import FathomDeployment
from raven.fathom.client import ServerLocator
from raven.fathom.client import Project
from raven.fathom.base import ClientAuthentication

# Set up project
project = Project("my-project")
project.name = "My Project"
project.version = "1.0.0"
project.domain = "docs.example.com"

# Create documentation resource
docs = DocumentationResource()
docs += DocsDir("build/site")

# Configure server
locator = ServerLocator("fathom.example.com")
locator.port = 443
locator.secure_connection = True

# Set up authentication
auth = ClientAuthentication("username", "password")

# Create and execute deployment
deployment = FathomDeployment(locator)
deployment.set_project(project)
deployment.add_resource(docs)
deployment.use_authentication(auth)

result = deployment.deploy()
if result.is_successful():
    print("Deployment successful!")
else:
    print(f"Deployment failed: {result.info_message}")
```

For detailed API documentation, see the [API Reference](api.md).

## Best Practices

### Security

- **Don't commit passwords**: Leave the `password` field empty in configuration files
- **Use environment variables**: In CI/CD, use secure environment variables for credentials
- **Enable secure transport**: Always use `transport.secure=true` in production

### Configuration Management

- **Version control `fathom.cfg`**: Include it in your repository
- **Keep user config private**: Store `~/.config/fathom/config` securely
- **Use meaningful IDs**: Choose descriptive, unique project identifiers
- **Document domains**: Clearly specify where documentation will be accessible

### Deployment Strategy

- **Automate deployment**: Integrate with your CI/CD pipeline
- **Deploy on release**: Trigger deployment when you tag a release
- **Version documentation**: Update the `version` field in your config for each release
- **Use filters wisely**: Exclude unnecessary files to reduce deployment size
