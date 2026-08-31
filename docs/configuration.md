# Configuration

## User Configuration

The user configuration file `~/.config/fathom/config/user.cfg` is used to store personal settings:

```ini
[User]
logging.enabled=true

[Server-1]
name=Production
domain=fathom.example.com
username=myuser
password=mypassword
port=443
location=/api
transport.secure=true

[Server-2]
name=Development
domain=fathom-devel.example.com
username=myuser
```

**[User] Section:**

- `logging.enabled`: Enable logging to a user-specific file (default: `false`)
- `username`: Default username for authentication
- `password`: Default password (leave empty to be prompted interactively)

**[Server] Section (repeatable):**

Define multiple servers for different environments:

- `name`: Server identifier (used to reference this server)
- `domain`: Server domain or IP address
- `username`: Username for this server
- `password`: Password for this server (leave empty to be prompted interactively)
- `port`: Server port
- `location`: Path location on the server (e.g., `/api`)
- `transport.secure`: Use a secure network connection (default: `true`)


## Project Configuration

The `fathom.cfg` file defines your project and deployment settings. It must be placed in your project root directory or under a `docs` subdirectory.

#### [Project] Section

The `[Project]` section contains essential project information:

```ini
[Project]
id=unique-project-id
name=Project Display Name
description=Brief description of the project
version=1.0.0
domain=docs.example.com
assets=build/site
```

**Configuration Keys:**

- `id` (required): Unique identifier for your project
- `name` (optional): Human-readable project name
- `description` (optional): Brief project description
- `version` (optional): Version string for the documentation
- `domain` (required): Domain where documentation will be accessible
- `assets` (required): Path to the directory containing built documentation files (relative or absolute)

#### File Filters

File filters allow you to include or exclude specific files from your deployment.

##### Include Filter

Include only files matching specific criteria:

```ini
[Filter-Include]
file.type=any
file.names=["index.html", "404.html"]
file.extensions=[".html", ".css", ".js"]
file.prefixes=["search", "api"]
file.size.min=1
file.size.max=10MB
file.ignore.nonexistent=false
```

##### Exclude Filter

Exclude files matching specific criteria:

```ini
[Filter-Exclude]
file.type=any
file.names=["draft.html", "internal.html"]
file.extensions=[".tmp", ".bak"]
file.prefixes=["_draft"]
```

**Filter Options:**

- `file.type`: Type of files to match (`any`, `file`, `directory`)
- `file.names`: List of exact file names to match
- `file.extensions`: List of file extensions to match (include the dot)
- `file.prefixes`: List of filename prefixes to match
- `file.size.min`: Minimum file size (supports units: B, KB, MB, GB)
- `file.size.max`: Maximum file size
- `file.ignore.nonexistent`: Whether to ignore files that don't exist (default: `false`)
