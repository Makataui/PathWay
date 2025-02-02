<h1 align="center"> PathWay</h1>
<p align="center" markdown=1>
  <i>A bridge for your digital pathology files</i>
  <br>
  <i>Built loving with help a starting template from: FastAPI-Boilerplate</i>
</p>


<p align="center">
  <a href="">
      <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://fastapi.tiangolo.com">
      <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI">
  </a>
  <a href="https://docs.pydantic.dev/2.4/">
      <img src="https://img.shields.io/badge/Pydantic-E92063?logo=pydantic&logoColor=fff&style=for-the-badge" alt="Pydantic">
  </a>
  <a href="https://www.postgresql.org">
      <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  </a>
  <a href="https://redis.io">
      <img src="https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=fff&style=for-the-badge" alt="Redis">
  </a>
  <a href="https://docs.docker.com/compose/">
      <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff&style=for-the-badge" alt="Docker">
  </a>
  <a href="https://nginx.org/en/">
      <img src="https://img.shields.io/badge/NGINX-009639?logo=nginx&logoColor=fff&style=for-the-badge" alt=NGINX>
  </a>
</p>

<p align="center">
  <a href="https://pydicom.github.io/">
      <img src="https://img.shields.io/badge/PyDicom-blue" alt="PyDicom">
  </a>
  <a href="https://openslide.org/">
      <img src="https://img.shields.io/badge/OpenSlide-red" alt="OpenSlide">
  </a>
</p>

# What is PathWay?

PathWay is many things but at it's heart, it has the following idea: to help build a bridge for pathology reporting of the future, combining WSI(Whole Slide Imaging/Images) with Synoptic Reporting. 

### Elevator Pitch

It's an easily deployable containerised solution that can take synoptic reports in FHIR and attach them to DICOM images, standardise to a custom ruleset, or take synoptic reports and attach them to other WSI types (please see below for supported types) and convert them to DICOM. 

It can then send these onwards or store them for you.

## 0. Features

## 1. About - Tech Stack and Open Source Libraries

**FastAPI boilerplate** creates an extendable async API using FastAPI, Pydantic V2, SQLAlchemy 2.0 and PostgreSQL:

- [`FastAPI`](https://fastapi.tiangolo.com): modern Python web framework for building APIs
- [`Pydantic V2`](https://docs.pydantic.dev/2.4/): the most widely used data Python validation library, rewritten in Rust [`(5x-50x faster)`](https://docs.pydantic.dev/latest/blog/pydantic-v2-alpha/)
- [`SQLAlchemy 2.0`](https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html): Python SQL toolkit and Object Relational Mapper
- [`PostgreSQL`](https://www.postgresql.org): The World's Most Advanced Open Source Relational Database
- [`Redis`](https://redis.io): Open source, in-memory data store used by millions as a cache, message broker and more.
- [`ARQ`](https://arq-docs.helpmanual.io) Job queues and RPC in python with asyncio and redis.
- [`Docker Compose`](https://docs.docker.com/compose/) With a single command, create and start all the services from your configuration.
- [`NGINX`](https://nginx.org/en/) High-performance low resource consumption web server used for Reverse Proxy and Load Balancing.

> \[!TIP\] 
> If you want the `SQLModel` version instead, head to [SQLModel-boilerplate](https://github.com/igorbenav/SQLModel-boilerplate).

## 2. Tech Features

- ⚡️ Fully async
- 🚀 Pydantic V2 and SQLAlchemy 2.0
- 🔐 User authentication with JWT
- 🍪 Cookie based refresh token
- 🏬 Easy redis caching
- 👜 Easy client-side caching
- 🚦 ARQ integration for task queue
- ⚙️ Efficient and robust queries with <a href="https://github.com/igorbenav/fastcrud">fastcrud</a>
- ⎘ Out of the box offset and cursor pagination support with <a href="https://github.com/igorbenav/fastcrud">fastcrud</a>
- 🛑 Rate Limiter dependency
- 👮 FastAPI docs behind authentication and hidden based on the environment
- 🦾 Easily extendable
- 🤸‍♂️ Flexible
- 🚚 Easy running with docker compose
- ⚖️ NGINX Reverse Proxy and Load Balancing

## 3. Contents
0. [PathWay]
0. [Pathway's Features](#0-features)
1. [About The Tech](#1-about---tech-stack-and-open-source-libraries)
1. [Tech Features](#2-tech-features)
1. [Contents](#3-contents)
1. [Prerequisites](#4-prerequisites)
   1. [Environment Variables (.env)](#41-environment-variables-env)
   1. [Docker Compose](#42-docker-compose-preferred)
   1. [From Scratch](#43-from-scratch)
1. [Testing](#8-testing)
1. [Contributing](#9-contributing)
1. [References](#10-references)
1. [License](#11-license)
1. [Contact](#12-contact)

______________________________________________________________________

## 4. Prerequisites

### 4.0 Start


## 11. License

[`MIT`](LICENSE.md)

## 12. Contact

Ferenc Igali – [@Makataui]
[github.com/Makataui](https://github.com/Makataui/)
