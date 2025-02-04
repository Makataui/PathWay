<h1 align="center"> PathWay [WIP]</h1>
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

Currently it's just being set up but I thought I'd document the journey publicly here rather than building it and then just releasing 0.1.0. 

### Elevator Pitch

It's an easily deployable containerised solution that can take synoptic reports in FHIR and attach them to DICOM images, standardise to a custom ruleset, or take synoptic reports and attach them to other WSI types (please see below for supported types) and convert them to DICOM. 

It can then send these onwards or store them for you.

#### How?

Well, it's a combination of an API, several other open sources tools which this would not be possible without and a lot of other inputs.

#### How is the Synoptic Report defined?

#### What is Structured Data Capture (SDC)?

### DICOM SR (Structured Reporting) vs SDC vs XML datasets vs FHIR/FHIR SDC/Questionnaires

#### What is Unstructured Data?

### What It Is Not:

It is not designed to be a universal viewer or converter - the viewer provided is just for demonstration purposes of the capabilities of the software and to help visualise it for users - which is why things like Postgres are provided as part of the Docker Compose but ideally you will map these to your own databases, softwares, APIs and middlewares. 


### Quick Note About File Security and File Validation: 

This setup uses a basic AV to validate files against. Security of uploaded and mapped files is not guaranteed and is the end users responsibility - there is only a basic check here. 


## 0. Features

- XML Importer and Mapper For Datasets/SDC
- Docker Startup for easy, cloud agnostic cloud deployment in any stack
- FHIR Server and REST API, following latest standardise
- Support for SNOMED

### 0.1 Inspiration

### 0.2 International Profiles

### 0.3 Radiologists

### 0.4 IMR - Interactive Multimedia Report Presentation

### 0.5 Saving And Embedding IMRs

### 0.6 FHIR Structure

### 0.7 HL7 Conversion / Mapping

### 0.8 Mapping Other Clinical Data And Imaging

### 0.9 Dealing With Challenges of IMR, specifically in Digital Pathology

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
0. [PathWay](#what-is-pathway)
0. [Pathway's Features](#0-features)
    1. [PathWay's Inspiration](#01-inspiration)
    1. [International Profiles](#02-international-profiles)
    1. [Radiologists](#03-radiologists)
    1. [IMR](#04-imr---interactive-multimedia-report-presentation)
    1. [Saving And Embedding IMRs](#05-saving-and-embedding-imrs)
    1. [FHIR Structure](#06-fhir-structure)
    1. [HL7 Conversion / Mapping](#07-hl7-conversion--mapping)
1. [About The Tech](#1-about---tech-stack-and-open-source-libraries)
1. [Tech Features](#2-tech-features)
1. [Contents](#3-contents)
1. [Prerequisites](#4-prerequisites)
   1. [Environment Variables (.env)](#41-environment-variables-env)
   1. [Docker Compose](#42-docker-compose-preferred)
   1. [From Scratch](#43-from-scratch)
1. [Terminology](#5-terminology)
    1. [Term Definition](#51-term-definition)
1. [Imaging](#6-other-imaging)
    1. [Other Clinical Imaging](#61-clinical-imaging)
    1. [Grossing / Specimen Macro Imaging](#62-grossingcut-upspecimen-macro-imaging)
1. [Data Control And Privacy](#7-data-control-and-privacy)
    1. [Data Pipelines](#71-data-pipelines)
    1. [Data Anonymisation](#72-anonymisation---data-identifier)
    1. [WSI Labels](#73-label)
1. [Testing](#8-testing)
1. [Contributing](#9-contributing)
1. [References](#10-references)
1. [License](#11-license)
1. [Contact](#12-contact)

______________________________________________________________________

## 4. Prerequisites

### 4.0 Start

### 4.1 Environment Variables

### 4.2 Docker Compose (Preferred)

### 4.3 From Scratch Setup

## 5. Terminology

### 5.1 Term Definition

## 6. Other Imaging

### 6.1 Clinical Imaging

### 6.2 Grossing/Cut-up/Specimen Macro Imaging

## 7. Data Control And Privacy

### 7.1 Data Pipelines

### 7.2 Anonymisation - Data Identifier

### 7.3 Label 

## 8. Testing

## 9. Contributing

## 10. References

## 11. License

[`MIT`](LICENSE.md)

## 12. Contact

Ferenc Igali – [@Makataui]
[github.com/Makataui](https://github.com/Makataui/)
