# Git Push Troubleshooting Guide

**Date:** December 22, 2024  
**Issue:** `push_to_github.bat` not working  
**Repository:** dinglab_printer_notebook

---

## Quick Diagnosis

### **Step 1: Run the diagnostic script**

Double-click: `check_git_config.bat`

This will tell you:
- ? If Git is installed
- ? If your username/email are configured
- ? If the remote repository is set up correctly
- ? Current repository status

---

## Common Issues & Solutions

### **Issue 1: Git user not configured**

**Symptoms:**
```
*** Please tell me who you are.
```

**Solution:**
1. Double-click `setup_git.bat`
2. Enter your GitHub username (e.g., `edwinclement08`)
3. Enter your email (e.g., `eclement@wpi.edu`)

**Or manually:**
```cmd
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

### **Issue 2: Not authenticated with GitHub**

**Symptoms:**
```
remote: Support for password authentication was removed on August 13, 2021.
fatal: Authentication failed
```

**Solution Option A: GitHub Desktop (Easiest)**
1. Install GitHub Desktop: https://desktop.github.com/
2. Sign in with your GitHub account
3. GitHub Desktop handles authentication automatically
4. Try `push_to_github.bat` again

**Solution Option B: Personal Access Token**
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: "RED Lab Printer"
4. Select scopes: `repo` (full control)
5. Click "Generate token"
6. Copy the token (you won't see it again!)
7. When `push_to_github.bat` asks for password, paste the token

**Solution Option C: GitHub CLI**
```cmd
gh auth login
```
Follow the prompts to authenticate.

---

### **Issue 3: Repository not set up correctly**

**Symptoms:**
```
fatal: not a git repository
```

**Solution:**
```cmd
cd C:\printer_code\dinglab_printer_notebook
git remote -v
```

Should show:
```
origin  https://github.com/edwinclement08/dinglab_printer_notebook (fetch)
origin  https://github.com/edwinclement08/dinglab_printer_notebook (push)
```

If not, run:
```cmd
git remote add origin https://github.com/edwinclement08/dinglab_printer_notebook
```

---

### **Issue 4: No changes to commit**

**Symptoms:**
```
nothing to commit, working tree clean
```

**This is actually GOOD!** It means:
- Either the files were already committed, OR
- The changes are already on GitHub

**Check with:**
```cmd
git status
git log --oneline -5
```

---

### **Issue 5: Merge conflicts**

**Symptoms:**
```
error: Your local changes to the following files would be overwritten by merge
```

**Solution:**
```cmd
git stash
git pull origin main
git stash pop
```

Then resolve any conflicts and try pushing again.

---

## Manual Push Instructions

If the batch file doesn't work, try manually in PowerShell or Git Bash:

### **PowerShell:**
```powershell
cd C:\printer_code\dinglab_printer_notebook

# Stage files
git add printer_helper_force_sensing.py
git add support_modules/SensorDataWindow.py
git add *.md

# Commit
git commit -m "feat: Add automated layer logging integration for RED Lab"

# Push
git push origin main
```

### **Git Bash:**
```bash
cd /c/printer_code/dinglab_printer_notebook

git add printer_helper_force_sensing.py
git add support_modules/SensorDataWindow.py
git add *.md

git commit -m "feat: Add automated layer logging integration for RED Lab"

git push origin main
```

---

## Check What Would Be Pushed

Before pushing, you can check what will be committed:

```cmd
cd C:\printer_code\dinglab_printer_notebook

# See what files changed
git status

# See what changes were made
git diff printer_helper_force_sensing.py

# See staged changes
git diff --cached
```

---

## Alternative: Use GitHub Desktop

If command-line Git is problematic, GitHub Desktop is much easier:

1. **Install:** https://desktop.github.com/
2. **Open the repository:**
   - File ? Add Local Repository
   - Choose: `C:\printer_code\dinglab_printer_notebook`
3. **Review changes:**
   - You'll see all modified files in the left panel
4. **Commit:**
   - Check the files you want to commit
   - Enter commit message
   - Click "Commit to main"
5. **Push:**
   - Click "Push origin" button at the top

---

## Verification After Push

After successfully pushing, verify on GitHub:

1. Go to: https://github.com/edwinclement08/dinglab_printer_notebook
2. Click "Commits" to see your latest commit
3. Check the files were updated with the correct changes

---

## Common Git Commands Cheat Sheet

```cmd
# Check status
git status

# See commit history
git log --oneline -10

# See what changed
git diff

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo all changes to a file
git checkout -- filename.py

# Pull latest from GitHub
git pull origin main

# See remote URLs
git remote -v

# Check current branch
git branch
```

---

## Still Not Working?

If none of the above work, let me know what error message you see and I can help further. Common things to check:

1. ? Git is installed: `git --version`
2. ? You're in the right directory: `cd C:\printer_code\dinglab_printer_notebook`
3. ? Remote is set up: `git remote -v`
4. ? You're authenticated with GitHub
5. ? You have permission to push to the repository

---

**Quick Test:**
```cmd
cd C:\printer_code\dinglab_printer_notebook
git status
```

This should show you the modified files. If it does, Git is working and you just need to authenticate!

---

*Troubleshooting Guide Created: December 22, 2024*  
*For: RED Lab Printer - dinglab_printer_notebook repository*
