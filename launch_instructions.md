# MPLA Project Server Launch Instructions

This document provides definitive instructions for launching the backend and frontend servers for the MPLA project. Following these steps will help avoid common issues related to module pathing and concurrent execution.

## Important Pre-requisites
- You must have the Python virtual environment set up in `.venv/`.
- You must have the NodeJS dependencies installed in `webapp/` by running `npm install`.

---

## 1. Launching the Backend Server (Uvicorn)

The backend server must be launched from the **project root directory** to ensure Python can find all necessary modules, but it needs to be pointed at the application inside the `server` directory.

**Instructions:**

1.  Open a terminal.
2.  Ensure you are in the project root directory (`Ai_Agents`).
3.  Run the following command. Note that we use the `--app-dir` flag to specify the location of the application, which is crucial.

    ```powershell
    # Make sure to use the python executable from the virtual environment
    ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir server/
    ```
Keep this terminal open. The backend server is now running.

---

## 2. Launching the Frontend Server (Vite)

The frontend server must be launched from its own `webapp` directory.

**Instructions:**

1.  Open a **new, separate terminal**.
2.  Navigate into the `webapp` directory:
    ```powershell
    cd webapp
    ```
3.  Start the development server:
    ```powershell
    npm run dev
    ```
Keep this terminal open as well. You can now access the web application in your browser at the address provided by the Vite server (usually `http://localhost:5173`).

---
> **Note for AI/Automation:** When automating, execute these commands in separate, non-blocking processes. Do not use `&&` to chain them, as this will not work in PowerShell and the first command would block the second anyway. 