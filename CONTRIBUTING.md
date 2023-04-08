# Contributing

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

# Types of Contributions

## Report Bugs

Report bugs at <https://github.com/tuttle-dev/tuttle/issues>.

If you are reporting a bug, please include:

-   Your operating system name and version.
-   Any details about your local setup that might be helpful in
    troubleshooting.
-   Detailed steps to reproduce the bug.

## Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with \"bug\"
and \"help wanted\" is open to whoever wants to implement it.

## Implement Features

Look through the GitHub issues for features. Anything tagged with
\"enhancement\" and \"help wanted\" is open to whoever wants to
implement it.

## Write Documentation

tuttle could always use more documentation, whether as part of the
official tuttle docs, in docstrings, or even on the web in blog posts,
articles, and such.

## Submit Feedback

The best way to send feedback is to file an issue at
<https://github.com/tuttle-dev/tuttle/issues>.

If you are proposing a feature:

-   Explain in detail how it would work.
-   Keep the scope as narrow as possible, to make it easier to
    implement.
-   Remember that this is a volunteer-driven project, and that
    contributions are welcome :)

# Get Started!

Ready to contribute? Here\'s how to set up [tuttle]{.title-ref} for
local development.

1.  Fork the [tuttle]{.title-ref} repo on GitHub.

2.  Clone your fork locally:

    ``` shell
    $ git clone git@github.com:your_name_here/tuttle.git
    ```

3.  Install your local copy into a virtualenv. Assuming you have
    virtualenvwrapper installed, this is how you set up your fork for
    local development:

    ``` shell
    $ mkvirtualenv tuttle
    $ cd tuttle/
    $ python setup.py develop
    ```

4.  Create a branch for local development:

    ``` shell
    $ git checkout -b name-of-your-bugfix-or-feature
    ```

    Now you can make your changes locally.


    **Install the pre-commit hooks before making your first commit to ensure that you match the code style**:

    ``` shell
    $ pre-commit install
    ```
5.  If you haven't done so already, install and/or activate
    [pyright](https://github.com/microsoft/pyright).
    The "basic" level should suffice and help you to avoid type errors.
    If you are getting a type error, ask yourself:
    Can this occur at runtime?

    No -> add `#type: ignore` to the end of the line

    Yes -> ensure that it doesn't, e.g. by using an `assert` statement

    Oftentimes, type errors indicate bad design,
    so keep refactoring in mind as a third option.

6.  When you\'re done making changes, check that your changes pass
    code style checks and the tests:

    ``` shell
    $ pytest
    ```


7.  Commit your changes and push your branch to GitHub:

    ``` shell
    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature
    ```

8.  Submit a pull request through the GitHub website.

# Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1.  The pull request should include tests.
2.  If the pull request adds functionality, the docs should be updated.
    Put your new functionality into a function with a docstring, and add
    the feature to the list in README.rst.
3.  The pull request should work for Python  3.8, 3.9, 3.10.

# Tips

To run a subset of tests:

``` shell
$ pytest tests.test_tuttle
```

# Deploying

A reminder for the maintainers on how to deploy. Make sure all your
changes are committed (including an entry in HISTORY.rst). Then run:

``` shell
$ bump2version patch # possible: major / minor / patch
$ git push
$ git push --tags
```

Travis will then deploy to PyPI if tests pass.


## Architecture Notes

**The View**

- builds Ui,
- reacts to data changes (by updating the Ui)
- listens for events and forwards them to the Intent

**The Intent**

- receives events
- if some data is affected by the event, figure out which data source corresponds to that data
- transforms the event data to the data format required by the data source
- transform returned data source data to the data format required by the Ui
- else, no data is affected by the event, handle the event (often using a util class).
- an example of this is sending invoices by mail.

**The Model (a.k.a data layer)**

- defines the entity
- define the entity source (file, remote API, local database, in-memory cache, etc)
- if a relational database is used, define the entity's relationship to other entities
- maintain the integrity of that relation (conflict strategies for insert operations are defined here, and integrity errors are thrown here, for example)
- defines classes that manipulate this source (open, read, write, ....)


As you go outer in layers (the outmost layer is the Ui, the innermost is the data layer), communication can occur down_ward across layers, and horizontally (for lack of a better word) BUT a layer cannot skip the layer directly below it. This is to say:

* Data sources can communicate with each other. Thus `ClientDatasource.delete_client` can call. `ContractDatasource.get_contract ` for example.

* Intents can communicate with each other, and with any data source. Thus `ClientIntent` can call `ContractIntent` or  `ContractDatasource` for example.
The Ui can communicate with any intent (though often the Ui is tied to only a single intent, and the intent can instead call the 'other' intent). But it cannot communicate with a data source -> this would violate the do not skip layers rule.
An inner layer cannot have a dependency on the layer above it. Thus an intent cannot instantiate a Ui class, and a data source cannot instantiate an Intent class.

![](assets/images/mvi-concept.png)
