<h1 align="center"> PathWay</h1>
<p align="center" markdown=1>
  <i>A bridge for your digital pathology files</i>
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

PathWay is ... 

## 0. About - Tech Stack and Open Source Libraries

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

## 1. Features

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

## 2. Contents

0. [About](#0-about)
1. [Features](#1-features)
1. [Contents](#2-contents)
1. [Prerequisites](#3-prerequisites)
   1. [Environment Variables (.env)](#31-environment-variables-env)
   1. [Docker Compose](#32-docker-compose-preferred)
   1. [From Scratch](#33-from-scratch)
1. [Usage](#4-usage)
   1. [Docker Compose](#41-docker-compose)
   1. [From Scratch](#42-from-scratch)
      1. [Packages](#421-packages)
      1. [Running PostgreSQL With Docker](#422-running-postgresql-with-docker)
      1. [Running Redis with Docker](#423-running-redis-with-docker)
      1. [Running the API](#424-running-the-api)
   1. [Creating the first superuser](#43-creating-the-first-superuser)
   1. [Database Migrations](#44-database-migrations)
1. [Extending](#5-extending)
   1. [Project Structure](#51-project-structure)
   1. [Database Model](#52-database-model)
   1. [SQLAlchemy Models](#53-sqlalchemy-models)
   1. [Pydantic Schemas](#54-pydantic-schemas)
   1. [Alembic Migrations](#55-alembic-migrations)
   1. [CRUD](#56-crud)
   1. [Routes](#57-routes)
      1. [Paginated Responses](#571-paginated-responses)
      1. [HTTP Exceptions](#572-http-exceptions)
   1. [Caching](#58-caching)
   1. [More Advanced Caching](#59-more-advanced-caching)
   1. [ARQ Job Queues](#510-arq-job-queues)
   1. [Rate Limiting](#511-rate-limiting)
   1. [JWT Authentication](#512-jwt-authentication)
   1. [Running](#513-running)
   1. [Create Application](#514-create-application)
   2. [Opting Out of Services](#515-opting-out-of-services)
1. [Running in Production](#6-running-in-production)
   1. [Uvicorn Workers with Gunicorn](#61-uvicorn-workers-with-gunicorn)
   1. [Running With NGINX](#62-running-with-nginx)
      1. [One Server](#621-one-server)
      1. [Multiple Servers](#622-multiple-servers)
1. [Testing](#7-testing)
1. [Contributing](#8-contributing)
1. [References](#9-references)
1. [License](#10-license)
1. [Contact](#11-contact)

______________________________________________________________________

## 3. Prerequisites

### 3.0 Start


## 10. License

[`MIT`](LICENSE.md)

## 11. Contact

Ferenc Igali – [@Makataui]
[github.com/Makataui](https://github.com/Makataui/)
