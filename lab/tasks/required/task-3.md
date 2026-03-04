# Add Front-end

<h4>Time</h4>

~50 min

<h4>Purpose</h4>

Understand the difference between a dev server and production static files, and use an AI agent to modify front-end code.

<h4>Context</h4>

The back-end API is running on the VM. You will add a front-end that connects to it.
First you will run it locally with a dev server, then build and deploy a production version served by [`Caddy`](../../../wiki/caddy.md#what-is-caddy).
Finally, you will use an AI agent to add a new feature to the front-end.

<h4>Table of contents</h4>

- [1. Steps](#1-steps)
  - [1.1. Follow the `Git workflow`](#11-follow-the-git-workflow)
  - [1.2. Create a `Lab Task` issue](#12-create-a-lab-task-issue)
  - [1.3. Part A: Dev version](#13-part-a-dev-version)
    - [1.3.1. Navigate to the front-end project directory](#131-navigate-to-the-front-end-project-directory)
    - [1.3.2. Configure the environment for frontend](#132-configure-the-environment-for-frontend)
    - [1.3.3. Start the dev server](#133-start-the-dev-server)
    - [1.3.2. Edit a source file and observe hot reload](#132-edit-a-source-file-and-observe-hot-reload)
  - [1.4. Part B: Prod version](#14-part-b-prod-version)
    - [1.4.1. Deploy the front-end to the VM](#141-deploy-the-front-end-to-the-vm)
    - [1.4.2. Verify in the browser](#142-verify-in-the-browser)
  - [1.5. Part C: Modify the front-end with an AI agent](#15-part-c-modify-the-front-end-with-an-ai-agent)
    - [1.5.1. Add a type filter](#151-add-a-type-filter)
    - [1.5.2. Verify in the dev server](#152-verify-in-the-dev-server)
    - [1.5.3. Deploy the change to the VM](#153-deploy-the-change-to-the-vm)
  - [1.6. Finish the task](#16-finish-the-task)
  - [1.7. Check the task using the autochecker](#17-check-the-task-using-the-autochecker)
- [2. Acceptance criteria](#2-acceptance-criteria)

## 1. Steps

### 1.1. Follow the `Git workflow`

Follow the [`Git workflow`](../../../wiki/git-workflow.md) to complete this task.

### 1.2. Create a `Lab Task` issue

Title: `[Task] Add Front-end`

### 1.3. Part A: Dev version

> [!NOTE]
> A dev server serves the front-end with hot reload: the browser updates automatically when you save a file.
> This is for local development only — it is not meant to be deployed to production.

Complete these steps:

<!-- no toc -->
1. [Navigate to the front-end project directory](#131-navigate-to-the-front-end-project-directory)
2. [Configure the environment for frontend](#132-configure-the-environment-for-frontend)
3. [Start the dev server](#133-start-the-dev-server)
4. [Edit a source file and observe hot reload](#132-edit-a-source-file-and-observe-hot-reload)

#### 1.3.1. Navigate to the front-end project directory

> [!NOTE]
> The dev server proxies API requests (e.g., `/items`) to the `VITE_API_TARGET` URL.
> The [API key](../../../wiki/api.md#api-key) is entered at runtime through the front-end UI — it is not stored in the `frontend/.env.secret` file.

1. [Open a new `VS Code Terminal`](../../../wiki/vs-code.md#open-a-new-vs-code-terminal).
2. To navigate to the front-end project directory,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cd frontend
   ```

#### 1.3.2. Configure the environment for frontend

1. To copy the environment file template,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cp .env.example .env.secret
   ```

2. [Open the file](../../../wiki/vs-code.md#open-the-file): `frontend/.env.secret`.

3. Set `VITE_API_TARGET` to the [URL](../../../wiki/computer-networks.md#url) of your back-end [API](../../../wiki/api.md#what-is-an-api): `http://<your-vm-ip-address>:<caddy-port>`.

   Replace:

   - [`<your-vm-ip-address>`](../../../wiki/vm.md#your-vm-ip-address)
   - [`<caddy-port>`](../../../wiki/caddy.md#caddy-port)

4. To install dependencies,

   <!-- TODO move to the setup? -->

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   npm install
   ```

#### 1.3.3. Start the dev server

1. To start the dev server,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   npm run dev
   ```

   The output should be similar to this:

   ```terminal
   ➜  Local:   http://localhost:5173/
   ```

2. Open the URL shown in the terminal output in a browser: `http://localhost:5173/`

   Verify that the front-end loads and asks for an API key.

3. Log in to the app

#### 1.3.2. Edit a source file and observe hot reload

1. Open the file [`frontend/src/App.tsx`](../../../frontend/src/App.tsx) ([how to open a file](../../../wiki/vs-code.md#open-the-file)).

2. Make a small visible change, for example change the `Items` heading text to something else.

3. Save the file.

   Verify that the text you changed updates in the browser without you refreshing the page.

4. Undo the change (press `Ctrl+Z` until the heading is back to its original text) and save the file.

   Verify that the browser shows the original heading.

### 1.4. Part B: Prod version

<!-- no toc -->
- [1.4.1. Deploy the front-end to the VM](#141-deploy-the-front-end-to-the-vm)
- [1.4.2. Verify in the browser](#142-verify-in-the-browser)

> [!NOTE]
> A production build compiles the front-end into static [`HTML`](../../../wiki/file-formats.md#html), [`CSS`](../../../wiki/file-formats.md#css), and [`JavaScript`](../../../wiki/programming-language.md#javascript) files.
>
> In this project, [`Caddy`](../../../wiki/caddy.md#what-is-caddy) runs in a [`Docker`](../../../wiki/docker.md#what-is-docker) container that builds the front-end and serves the static files.
>
> The [`Caddyfile`](../../../wiki/caddy.md#caddyfile) routes API requests to the back-end and serves the front-end for all other paths.

#### 1.4.1. Deploy the front-end to the VM

1. [Connect to your VM](../../../wiki/vm.md#connect-to-the-vm).

2. To navigate to the project directory,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cd se-toolkit-lab-4
   ```

3. To switch to the task branch,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   git switch <task-branch>
   ```

   Replace [`<task-branch>`](../../../wiki/git-workflow.md#task-branch).

4. To pull the latest changes from `GitHub`,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   git pull
   ```

5. To rebuild and restart the `caddy` service,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   docker compose --env-file .env.docker.secret up --build caddy -d
   ```

   The output should be similar to this:

   ```terminal
   [+] Building ...
   ...
   [+] Running 1/1
    ✔ Container caddy  Started
   ```

   <details><summary>Troubleshooting</summary>

   <h4>Container build fails</h4>

   Check that the `frontend/` directory exists and contains a valid `Dockerfile`.

   <h4>Port conflict (<code>port is already allocated</code>)</h4>

   Stop the process that uses the port, then retry.

   </details>

> [!NOTE]
> The `caddy` service uses a multi-stage `Dockerfile` ([`frontend/Dockerfile`](../../../frontend/Dockerfile)).
> Stage 1 builds the front-end (`npm run build`), and stage 2 copies the output into the `Caddy` image.
> Rebuilding the container is how you deploy front-end changes — there is no need to copy files manually.

#### 1.4.2. Verify in the browser

1. Open in a browser the [URL](../../../wiki/computer-networks.md#url): `http://<your-vm-ip-address>:<caddy-port>`.

   Replace:

   - [`<your-vm-ip-address>`](../../../wiki/vm.md#your-vm-ip-address)
   - [`<caddy-port>`](../../../wiki/caddy.md#caddy-port)

   Verify that the front-end loads and displays data from the API.

### 1.5. Part C: Modify the front-end with an AI agent

<!-- no toc -->
- [1.5.1. Add a type filter](#151-add-a-type-filter)
- [1.5.2. Verify in the dev server](#152-verify-in-the-dev-server)
- [1.5.3. Deploy the change to the VM](#153-deploy-the-change-to-the-vm)

> [!NOTE]
> The AI agent can read all front-end source files and find the right component to modify.
> Your job is to write a clear prompt and verify that the result is correct.

#### 1.5.1. Add a type filter

1. Open the AI agent in the `frontend/` directory.

2. Write a prompt that instructs the agent to add a dropdown that filters table rows by type. A good prompt tells the agent:

   - What the dropdown should list (unique types from the loaded items, plus an `All` option).
   - What happens when a type is selected (only rows with that type are shown).
   - What happens when `All` is selected (all rows are shown).
   - Where to place the dropdown (above the table).

   <details><summary>Hint: example prompt</summary>

   > "Add a filter dropdown above the table that lists all unique item types plus an 'All' option. When a type is selected, only rows with that type are shown. When 'All' is selected, all rows are shown. Derive the list of types from the loaded items — do not hardcode them."

   </details>

3. Wait for the agent to make the changes.

4. Review the changes the agent made. Verify that all of the following are true:

   - A `useState` hook tracks the selected type.
   - A `<select>` dropdown lists unique types derived from `items`, with an `All` option.
   - The table rows are filtered to show only the selected type (or all rows when `All` is selected).
   - The dropdown is placed above the table.

   If any of these are missing or incorrect, prompt the agent again to fix the specific issue.

   <details><summary>Fallback: make the changes manually</summary>

   If the AI agent is not available, make the changes manually:

   1. Open the file [`frontend/src/App.tsx`](../../../frontend/src/App.tsx) ([how to open a file](../../../wiki/vs-code.md#open-the-file)).
   2. Add a `useState` hook for the selected type, initialized to `'All'`.
   3. Derive the list of unique types from `items`.
   4. Add a `<select>` dropdown above the table that lists `All` and each unique type.
   5. Filter the rows displayed in the table by the selected type.

   </details>

<!-- TODO add button for copying the full table as comma-separated CSV 

paste the table in the PR summary
-->

#### 1.5.2. Verify in the dev server

1. Check that the dev server is still running (or restart it with `npm run dev`).
2. Open the front-end in the browser.

   Verify that the filter dropdown appears above the table and filters rows correctly.

> [!NOTE]
> The dev server picks up the changes automatically — no rebuild is needed.

#### 1.5.3. Deploy the change to the VM

1. [Commit changes](../../../wiki/git-workflow.md#commit-changes).

   Use the following commit message:

   ```text
   feat: add type filter to the front-end table

   - Add filter dropdown with unique types derived from items
   - Show all items when "All" is selected
   - Filter table rows client-side by selected type
   ```

2. [Push your changes](../../../wiki/git-workflow.md#push-commits).
3. [Connect to your VM](../../../wiki/vm.md#connect-to-the-vm).
4. To navigate to the project directory,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cd se-toolkit-lab-4
   ```

5. To fetch and checkout your task branch,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   git fetch origin && git checkout <task-branch>
   ```

   Replace [`<task-branch>`](../../../wiki/git-workflow.md#task-branch).

   **Note:** The VM's repository is currently on `main` from Part B. This switches it to your task branch to get the type filter changes you just pushed.

6. To rebuild and restart the `caddy` service,

   [run in the `VS Code Terminal`](../../../wiki/vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   docker compose --env-file .env.docker.secret up --build caddy -d
   ```

   The output should be similar to this:

   ```terminal
   [+] Building ...
   ...
   [+] Running 1/1
    ✔ Container caddy  Started
   ```

   <details><summary>Troubleshooting</summary>

   <h4>Container build fails</h4>

   Check that your changes are committed and pushed, and that you checked out the correct branch.

   <h4>Port conflict (<code>port is already allocated</code>)</h4>

   Stop the process that uses the port, then retry.

   </details>

7. Open in the browser: `http://<your-vm-ip-address>:<caddy-port>`.

   Replace:

   - [`<your-vm-ip-address>`](../../../wiki/vm.md#your-vm-ip-address)
   - [`<caddy-port>`](../../../wiki/caddy.md#caddy-port)

   Verify the filter dropdown appears and works in the production build.

### 1.6. Finish the task

1. [Create a PR](../../../wiki/git-workflow.md#create-a-pr-to-the-main-branch-in-your-fork) with your changes.

   In the PR description, include a screenshot of the front-end table with the type filter in use (a type selected, rows filtered).

2. [Get a PR review](../../../wiki/git-workflow.md#get-a-pr-review) and complete the subsequent steps in the `Git workflow`.

### 1.7. Check the task using the autochecker

[Check the task using the autochecker `Telegram` bot](../../../wiki/autochecker.md#check-the-task-using-the-autochecker-bot).

---

## 2. Acceptance criteria

- [ ] Issue has the correct title.
- [ ] A filter dropdown is present in `frontend/src/App.tsx` that filters rows by `type`.
- [ ] The dropdown includes an option to show all items.
- [ ] The PR description includes a screenshot of the front-end table with the type filter in use (a type selected, rows filtered).
- [ ] PR is approved.
- [ ] PR is merged.
