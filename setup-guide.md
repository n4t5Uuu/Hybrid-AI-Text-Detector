# Setup Guide: Hybrid AI Framework

This guide will walk you through setting up the development environment for the **hybrid-ai-framework** project.

The project is structured to support a Next.js frontend/backend (TypeScript/React) combined with Python-based AI capabilities in the backend.

---

## Prerequisites

Before starting, make sure you have the following installed on your machine:

1. **Node.js**: Version 18.x or higher (LTS recommended).
2. **Package Manager**: `npm` (comes with Node.js), `yarn`, `pnpm`, or `bun`.
3. **Python**: Version 3.10 or higher.
4. **Git**: For version control.

---

## Step-by-Step Installation

### 1. Clone the Repository
Clone the project repository to your local machine and navigate into the project directory:
```bash
git clone <repository-url>
cd hybrid-ai-framework
```

### 2. Node.js (Frontend) Setup
Install the project's JavaScript dependencies:
```bash
npm install
```
This installs the dependencies configured in [package.json](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/package.json), which include:
- **Next.js** (v16.2.10)
- **React** & **React-DOM** (v19.2.4)
- **Tailwind CSS** (v4) with PostCSS
- TypeScript and ESLint configuration.

### 3. Python (Backend/AI) Setup
This project supports a Python virtual environment to manage AI and backend models.

1. **Create a Virtual Environment**:
   Run the following command in the project root:
   ```bash
   python -m venv venv
   ```
2. **Activate the Virtual Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   - **macOS/Linux**:
     ```bash
     source venv/bin/activate
     ```
3. **Install Python Dependencies**:
   Once Python packages are needed, you can install them from a `requirements.txt` file (if present):
   ```bash
   pip install --upgrade pip
   # pip install -r requirements.txt
   ```

---

## Configuration & Environment Variables

Create your local environment files by copying the environment files. Currently, the environment configuration files are:
- [.env.local](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/.env.local) - For local-only secrets/keys.
- [.env.production](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/.env.production) - For production settings.

Configure any API keys (e.g. OpenAI, Gemini, Hugging Face) or custom backend endpoints in your local environment files.

---

## Running the Project

### Next.js Development Server
To start the Next.js development server:
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to view the application.

---

## Directory Structure Overview

Here is a quick look at the directory structure:
- [src/app/frontend/](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/src/app/frontend) - Place UI components, styling, hooks, and client-side integrations here.
- [src/app/backend/](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/src/app/backend) - Place backend API integrations, Python scripts, or microservices here.
- [package.json](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/package.json) - Contains frontend scripts and dependency details.
- [tsconfig.json](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/tsconfig.json) - TypeScript compiler options.
- [postcss.config.mjs](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/postcss.config.mjs) - Tailwind CSS postcss integration.

---

## Git Best Practices
To avoid committing your virtual environment files or other build artifacts:
1. Ensure `venv/` is included in your [.gitignore](file:///c:/Users/Alden%20Olmedo/Documents/VSCode/hybrid-ai-framework/.gitignore) file.
2. Never commit local `.env.*` files containing raw API credentials.
