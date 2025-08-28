# graphrag-api

A FastAPI-based API for the `microsoft/graphrag` library.

This project provides a robust and scalable API to interact with the `microsoft/graphrag` engine, allowing you to build applications that leverage the power of graph-based retrieval-augmented generation.

## High-Level Architecture

```mermaid
graph TD
    A[Client] --> B{FastAPI Server};
    B --> C[GraphRAG Engine];
    C --> D[Knowledge Graph];
```

## Features

* **FastAPI Backend:** A modern, fast (high-performance), web framework for building APIs with Python 3.11+ based on standard Python type hints.
* **GraphRAG Integration:** Seamless integration with the `microsoft/graphrag` library.
* **Scalable Architecture:** Designed to be scalable and easy to deploy.
* **Poetry:** Dependency management with [Poetry](https://python-poetry.org/).

## Getting Started

1. **Clone the repository:**

    ```bash
    git clone https://github.com/pierregrothe/graphrag-api.git
    cd graphrag-api
    ```

2. **Install dependencies:**

    ```bash
    poetry install
    ```

3. **Run the application:**

    ```bash
    poetry run uvicorn src.graphrag_api_service.main:app --reload
    ```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
