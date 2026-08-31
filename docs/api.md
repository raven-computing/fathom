# API Reference

This section provides detailed API documentation for the Fathom client library. Use these classes and functions when you need programmatic control over deployments or want to integrate Fathom into your own Python applications.

## Overview

The Fathom client API is organized into several key modules:

- **Documentation Resources**: Create and manage documentation files and directories
- **Deployment**: Execute deployments to a Fathom server
- **Configuration**: Load and manage project and user configurations
- **Authentication**: Handle client authentication
- **Filtering**: Apply file filters to control what gets deployed
- **Server Location**: Specify and locate Fathom servers

## Quick Reference

### Basic Deployment Flow

```python
from raven.fathom.client import DocumentationResource, DocsDir
from raven.fathom.client import FathomDeployment
from raven.fathom.client import ServerLocator
from raven.fathom.base import ClientAuthentication

# 1. Create documentation resource
docs = DocumentationResource()
docs += DocsDir("build/site")

# 2. Configure server location
locator = ServerLocator("fathom.example.com")
locator.secure_connection = True

# 3. Create deployment
deployment = FathomDeployment(locator)
deployment.use_authentication(ClientAuthentication("user", "password"))
deployment.add_resource(docs)

# 4. Deploy
result = deployment.deploy()
```

## Documentation Resources

::: raven.fathom.client.documentation

## Deployment

::: raven.fathom.client.deployment

## Project Management

::: raven.fathom.client.project

## Server Location

::: raven.fathom.client.locator

## Authentication

::: raven.fathom.client.authentication

## Configuration

::: raven.fathom.client.config

## File Filtering

::: raven.fathom.client.filter

::: raven.fathom.client.filter_loader

## Exceptions

::: raven.fathom.client.exceptions
