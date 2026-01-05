# Antigravity Development Guide: The "No-VS Code" Setup

Since you are building **exclusively inside Antigravity**, we need to swap out the "Desktop App" tools (like VS Code extensions) for "Command Line" superpowers.

This guide will set you up to code, visualize data, and manage versions entirely from here.

---

## 1. GitHub Setup (Remote Repo)
We already ran `git init` locally. Now we need to safeguard your code on the cloud (GitHub.com).

**Step 1: Create the Repo on GitHub**
1.  Go to [github.com/new](https://github.com/new) in your browser.
2.  Repository Name: `ludi_bot`
3.  **Important:** Select **Private**.
4.  Do **NOT** add a README, .gitignore, or License (we already have them locally).
5.  Click "Create repository".

**Step 2: Connect Antigravity to GitHub**
Copy the commands GitHub gives you under "…or push an existing repository from the command line". They will look like this:

```bash
git remote add origin https://github.com/YOUR_USERNAME/ludi_bot.git
git branch -M main
git push -u origin main
```

**Step 3: Paste them here.**
Just paste those 3 lines into the chat, and I will execute them to link our work to the cloud.

---

## 2. Viewing Data (The "SQLite Viewer" Replacement)
In VS Code, you'd click a file to see a table. In Antigravity (a terminal environment), we use **Queries** or **Scripts**.

**Option A: The "Quick Peek" (I do it for you)**
You can just ask me: *"Show me the top 5 scorers in the players table"* or *"Check if King James is in the database."*
I will run the SQL and show you the result.

**Option B: The "Data Inspector" Script (You run it)**
I have created a simple script called `inspect_db.py`.
Run it to see a clean summary of your data without knowing SQL.

*Command to run:*
```bash
./venv/bin/python inspect_db.py
```

**(I will create this script for you in the next step!)**

---

## 3. Essential Tools for Web App Building
As we build the Streamlit app, here are the tools we will use inside Antigravity:

*   **`Streamlit` (The Web Server):**
    *   We can't "open" a local host URL (localhost:8501) inside this chat window easily.
    *   **Workflow:** We will verify the *code* here, but to see the *visuals*, we will deploy to **Streamlit Community Cloud** early. It connects to your GitHub and updates automatically.
    *   *Why:* It allows you to see your app on the real internet, not just abstract code.

*   **`Pytest` (The Safety Net):**
    *   We installed this earlier. It checks if our logic breaks.
    *   *Usage:* I will run this constantly to ensure the "engine" doesn't explode when we change things.

---

## Summary Checklist
1.  **Repo:** Go create the empty repo on GitHub.com and give me the link.
2.  **Data:** I will build `inspect_db.py` so you can see your data anytime.
3.  **Web:** We will set up Streamlit Cloud as soon as we push code to GitHub.

**Ready to create `inspect_db.py`?**
