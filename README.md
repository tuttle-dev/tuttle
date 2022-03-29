# tuttle - painless business planning for freelancers

> HARRY TUTTLE: Bloody paperwork. Huh!
>
> SAM LOWRY: I suppose one has to expect a certain amount.
>
> HARRY TUTTLE: Why? I came into this game for the action, the excitement. Go anywhere, travel light, get in, get out, wherever there's trouble, a man alone.


**Tuttle is an open-source software project supported by the [Prototype Fund](https://prototypefund.de/en/about-2/). We develop a finance and business planning tool tailored for the requirements of freelancers.**


## Which challenges does the project address?

The working world is changing, the trend is towards freelancing: software developers, designers and journalists appreciate the freedom and creative possibilities of solo self-employment. More and more professionals are choosing it for themselves. It allows them to specialize and gain experience with many projects and clients.

With freelancing, there are many side activities: Marketing, client communication, legal and financial planning - although the latter probably appeals to few solo self-employed people. But neglected financial planning carries the risk of insolvency, debt, precarious self-employment, or poverty in old age. This also creates burdens for the social systems.

But what if software could make financial planning in freelancing almost as easy as being an employee? Our tool minimizes risks and makes the financial part of the job easy. Freelancing becomes more efficient, less risky, and therefore more beginner-friendly.

## How are you tackling the problem?

With Tuttle, we are developing a financial planning tool that is tailored to the needs of solo freelancers. We automate and give freelancers more time to do the work they love.
The application provides analysis and forecasting functions on income, expenses, disposable income, uncertainty management or explainability of the forecast and convinces with portability, among other things.

We develop the solution as a GUI application based on web technologies. Sensitive financial data is processed locally on the end device without central data collection. For data analysis, we rely on open source tools from the Python ecosystem.


## What is the product vision?

Desktop apps are great - let's have more of them. We are consciously developing a desktop app with local data storage, not a web app, since your business data is none of our business.

For this purpose, the Tuttle project is split across several repositories:

- This repository contains the core library, written in Python.
- The desktop application frontend, based on Electron.js, is being developed in [tuttle-dev/tuttle-app](https://github.com/tuttle-dev/tuttle-app)


## Prototype Test

A demo of the core functionality is available as a series of Jupyter notebooks at [`notebooks/walkthrough/`](https://github.com/tuttle-dev/tuttle/tree/main/notebooks/walkthrough). If you have basic Python programming skills you will be able to test this. We appreciate your feedback.


## Setup

1. Clone or download the current version from the `main` branch.

2. We recommend installation into a new [virtual environment](https://calmcode.io/virtualenv/intro.html).

3. Install the Python module in development mode:

```shell
$ python setup.py develop
```

4. To verify, run the unit tests:

```shell
$ pytest
```


## Contributing

Your contributions are welcome. Please follow the [guide (CONTRIBUTING.md)](https://github.com/tuttle-dev/tuttle/blob/main/CONTRIBUTING.md).

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)



## Acknowledgements

This project is funded by the [Prototype Fund](https://prototypefund.de).

![](https://vframe.io/about/funding/prototype-fund/assets/index.jpg)
