# GEMINI.md

## Project Overview

This project aims to create a FastAPI-based API for the `microsoft/graphrag` library. The project is inspired by the backend of `severian42/GraphRAG-Local-UI`, but will be a fresh implementation focusing solely on the API.

## Key Decisions

*   **Dependency Management:** We are using a `pyproject.toml` file to manage dependencies, which are installed in a virtual environment.
*   **Python Version:** The project uses Python 3.12.
*   **Project Structure:** The project follows a standard Python project structure, with the source code located in a `src` directory.
*   **Version Control:** The project is hosted on GitHub at [https://github.com/pierregrothe/graphrag-api](https://github.com/pierregrothe/graphrag-api).
*   **Documentation:** The `README.md` file will be the main source of documentation and will include Mermaid diagrams to illustrate the architecture. This `GEMINI.md` file will be updated with key decisions made during the development process.

## Building and Running

1.  **Activate the virtual environment:**
    ```bash
    .\.venv\Scripts\activate
    ```
2.  **Run the FastAPI application:**
    ```bash
    uvicorn graphrag_api.main:app --reload
    ```

## Development Conventions

*   **Virtual Environment:** All dependencies are installed and managed within the `.venv` virtual environment.
*   **Coding Style:** We will follow the PEP 8 style guide for Python code.