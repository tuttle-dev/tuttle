<br />
<div align="center">
  <h1>Tuttle</h1>

  [![License](https://img.shields.io/github/license/tuttle-dev/tuttle?color=green&style=flat-square)](https://github.com/tuttle-dev/tuttle/blob/main/LICENSE)
  [![Commit Activity](https://img.shields.io/github/commit-activity/m/tuttle-dev/tuttle?style=flat-square)]()


  <p><b>Time and money management for freelancers</b></p>

  <p align="center">
    <blockquote align="left">
    HARRY TUTTLE: Bloody paperwork. Huh!
    <br />
    SAM LOWRY: I suppose one has to expect a certain amount.
    <br />
    HARRY TUTTLE: Why? I came into this game for the action, the excitement. Go anywhere, travel light, get in, get out, wherever there's trouble, a man alone.
    </blockquote>
    <br />
  </p>
  <p>
    </p>
</div>

> **Note**: Tuttle is currently in development. The current version is a prototype, not quite ready for production use. However, we are happy to receive feedback from testers.

## Mission Statement

The working world is changing, the trend is towards freelancing: software developers, designers and journalists appreciate the freedom and creative possibilities of solo self-employment. More and more professionals are choosing it for themselves. It allows them to specialize and gain experience with many projects and clients.

With freelancing, there are many side activities: Marketing, client communication, legal and financial planning - although the latter probably appeals to few solo self-employed people. But what if software could make financial planning in freelancing almost as easy as being an employee? Our tool minimizes risks and makes the financial part of the job easy. Freelancing becomes more efficient, less risky, and therefore more beginner-friendly.

With Tuttle, we are developing a financial planning tool that is tailored to the needs of solo freelancers. We automate and give freelancers more time to do the work they love.
The application provides analysis and forecasting functions on income, expenses, disposable income, uncertainty management or explainability of the forecast and convinces with portability, among other things.

We develop the solution as a desktop application. Sensitive financial data is processed locally on the end device without central data collection. For data analysis, we rely on open source tools from the Python ecosystem. We are consciously developing a desktop app with local data storage, not a web app, since your business data is none of our business.


## Features


### Business Data Management

Manage your business contacts and contract terms for your project - all in one place.

<img src="assets/images/screenshot-contract.png" width=768 />

### Time Tracking

Track the time you spend on your projects. Import from your cloud calendar or from your favorite time tracking tool.

<img src="assets/images/screenshot-timetracking.png" width=768 />


### Invoicing

Generate invoices and timesheets automatically from your time tracking data. Export to PDF and send via email.

<img src="assets/images/screenshot-invoicing.png" width=768 />


## Roadmap

### Income Forecasting

Project your income for the next months based on your project planning. See how changes in your schedule affect your bottom line.

### Expense Tracking & Forecasting

Track regular expenses, taxes and social security contributions. Estimate them for the future based on expected revenue.

### Safe to Spend

Calculate your effective income and see how much you can spend without risking your financial security.


## Prototype Test

### Setup

1. Clone or download the current version.

2. We recommend installation into a new [virtual environment](https://calmcode.io/virtualenv/intro.html).

3. Install the Python module in development mode:

```shell
pip install -e .
```

1. To verify, run the unit tests:

```shell
$ pytest
```

1. Start the app with

```shell
$ python app/app.py
```

## Installation

### macOS

### Linux

### Windows

1. Requires [GTK](https://www.gtk.org).


## Build

To build an app bundle, run

```shell
python scripts/pack_app.py
```


## Contributing

Your contributions are welcome. Please follow the [guide (CONTRIBUTING.md)](https://github.com/tuttle-dev/tuttle/blob/main/CONTRIBUTING.md).

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)



## Acknowledgements

This project has received funding by the [Prototype Fund](https://prototypefund.de) in 2022.

<img src="assets/images/pf_funding_logos.svg" width="512px">
