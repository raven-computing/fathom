# Fathom: Manage the Release of Documentation

Fathom is a tool to automate the deployment of built documentation resources of all of your software projects to a central place. It can be used either directly from your workstation, your build server, or a GitHub Action. The Fathom project is composed of three components, the client, the server, and a base package. The base package contains the common code that is shared between the client and server. The client is a Python command-line application that interacts with the server component over the network. When you deploy documentation resources, the client packages all the resources and sends them to the server. The server then deploys them to the appropriate location in the filesystem of the server (usually the web root directory of some file server) so that the documentation becomes available to consumers online.

> [!NOTE]
> This project is currently in Beta.

## Getting Started

We do not yet provide pre-built packages. You'll need to build from source and install your own package. Both the client and server package depend on the base package, so make sure you also install it alongside.

Installing the Fathom client provides the `fathom` command. Usually, one would run that command from the source root directory of the underlying software project where the corresponding `fathom.cfg` project configuration file is located. See the docs for how to set up such a configuration file for your project.

Installing the Fathom server provides the `fathom-server` command. Currently, you'll have to set up the working directory manually before you can start the server. Check the `devel/server` directory in the build tree to see how a server working directory looks like. For a production environment, you'll also need to either mark such a working directory explicitly by creating an empty `.fathom_home` file in it, or set the `A_FATHOM_HOME` environment variable to the absolute path of the working directory. All of this will be fully automated until the production release of Fathom.


## Compatibility

This application requires Python **3.10** or higher. It is only officially supported and tested with *CPython*.

Even though Fathom is written in pure Python, we only officially support **Debian-based GNU/Linux** distributions and **Windows**. Fathom might run on other platforms as well, however, we do not provide official support for that.

Compatibility of the application CLI and client API is managed according to semantic versioning. Currently, as the project is still in a Beta stage, backwards compatibility between versions is not yet guaranteed.


## Documentation

The project documentation is located under the `docs` directory.

You can build the documentation resources with:
```shell
./build.sh --docs
```


## Build

Use the ```build.sh``` script to build installable application wheels:
```shell
./build.sh
```
See ```build.sh --help``` for available options.

All built distribution packages are placed in the `build/dist` directory.


## Development

> [!NOTE]
> This project is still under active development.

Most common tasks within the development workflow are automated by project control code, i.e. all executable shell scripts located in the project's source root directory. By default, they do the most common thing you would expect. Invoke the scripts with the `--help` argument to see all available options.

### Setup

It is recommended to use virtual environments (virtualenv) and the [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) utilities for developing Python projects. By default, all project control code assumes you have installed this properly on your system. If you want to manage your virtual environment with another tool, or not use one at all, then use the `--no-virtualenv` option when building or testing. Alternatively, you can utilise Docker for virtualization, skip the next setup step and instead append the `--isolated` option when invoking the build or test script.

Set up your development environment by sourcing the ```setup.sh``` script. This will create a virtual environment *fathom* for you and install all dependencies:
```shell
source setup.sh
```

This project offers *Visual Studio Code* integration. Open the project in VS Code from the project's source root directory with:
```shell
code .
```

Then import the provided profile from `.vscode/Fathom.code-profile`.  
If you want to utilise Docker for virtualization, we provide support for Dev Containers. When opening the project in VS Code, select *Reopen in Container* and you can develop, build, test and run the application fully isolated inside a Docker container.


### Tests

We use *Pyright* for static type checking and *Pylint* for general static code analysis.

The executable test suite consists of unit tests, integration tests and end-to-end functionality tests.

Execute the entire test suite including all checks and static code analysis with:
```shell
./test.sh --all
```

See ```test.sh --help``` for available options. You might want to use some of them during development to speed up your development cycles.

To start the server manually, you can use:
```shell
./test.sh --interactive server
```

To run and test the client manually, you can use:
```shell
./test.sh --interactive client
```

The project control code conveniently handles activation of the virtual environment for you under the hood, so you don't need to remember to do this manually with the `workon` command. Alternatively, while your virtual environment is active, you can also run the client and server by running the corresponding module as a script, so either `python -m raven.fathom.client` or `python -m raven.fathom.server`. 

When running in a development environment, all files are written under the `build/devel` directory. You may inspect them there manually if necessary.


## License

This project is licensed under Apache License 2.0.
