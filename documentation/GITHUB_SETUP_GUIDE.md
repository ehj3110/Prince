# GitHub Setup Guide for Prince Project

## Prerequisites

### 1. Install Git for Windows
1. Download Git from: https://git-scm.com/download/win
2. Run the installer with default settings
3. After installation, restart PowerShell
4. Verify installation:
   ```powershell
   git --version
   ```

### 2. Configure Git
```powershell
# Set your name and email (use your GitHub email)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Verify configuration
git config --list
```

## Initial Repository Setup

### 1. Initialize Git Repository
```powershell
# Navigate to project directory
cd "c:\Users\ehunt\OneDrive\Documents\Prince\Prince_Segmented_20250926"

# Initialize git repository
git init

# Check status
git status
```

### 2. Create .gitignore File
Before adding files, create a `.gitignore` to exclude unnecessary files:

```powershell
# Create .gitignore file
@"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
*.egg

# Virtual environments
venv/
env/
.conda/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Data files (large CSV files)
*.csv
!test_*.csv
!**/MASTER_*.csv

# Plots and output
*.png
!documentation/**/*.png

# Logs
*.log
output.log

# OS files
.DS_Store
Thumbs.db
desktop.ini

# Backup files
*~
*.bak
*.backup

# Large data directories
PrintingLogs_Backup/
archived_files/

# Temporary files
*.tmp
*.temp
"@ | Out-File -FilePath .gitignore -Encoding utf8
```

### 3. Stage and Commit Files
```powershell
# Add all files (respecting .gitignore)
git add .

# Check what will be committed
git status

# Make initial commit
git commit -m "Initial commit: Prince Segmented printing system with adhesion analysis"
```

## Create GitHub Repository

### 1. On GitHub Website
1. Go to https://github.com and sign in
2. Click the "+" icon → "New repository"
3. Repository name: `prince-segmented-printing`
4. Description: "3D DLP printing system with real-time adhesion force monitoring and analysis"
5. Choose "Private" or "Public"
6. **DO NOT** initialize with README, .gitignore, or license (we already have files)
7. Click "Create repository"

### 2. Connect Local Repository to GitHub
GitHub will show you commands. Use these:

```powershell
# Add remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/prince-segmented-printing.git

# Verify remote
git remote -v

# Push to GitHub (first time)
git push -u origin master
```

If you're using the newer default branch name:
```powershell
# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Subsequent Updates

### Daily Workflow

```powershell
# 1. Check what changed
git status

# 2. Add specific files
git add path/to/file.py
git add path/to/another_file.py

# Or add all changes
git add .

# 3. Commit with descriptive message
git commit -m "Add sandwich routine for glass contact safety"

# 4. Push to GitHub
git push
```

### Example: Pushing Today's Changes

```powershell
# Navigate to project
cd "c:\Users\ehunt\OneDrive\Documents\Prince\Prince_Segmented_20250926"

# Add new files
git add support_modules/SandwichRoutine.py
git add documentation/technical/SANDWICH_ROUTINE.md
git add documentation/README.md

# Add batch processing updates
git add batch_process_steppedcone.py

# Commit
git commit -m "Add SandwichRoutine for glass contact detection

- Implements force-based glass contact detection
- Prevents stage from punching through glass window
- Configurable approach and retract speeds
- Safety limit of 0.5mm beyond estimate
- Comprehensive documentation added
- Updated batch processing for SteppedCone tests with area-based analysis"

# Push to GitHub
git push
```

## Advanced Git Operations

### View Commit History
```powershell
git log --oneline --graph --decorate
```

### Create a New Branch (for experimental features)
```powershell
# Create and switch to new branch
git checkout -b feature/new-analysis-method

# Work on files...

# Commit changes
git add .
git commit -m "Experimental analysis method"

# Push branch to GitHub
git push -u origin feature/new-analysis-method

# Switch back to main branch
git checkout main

# Merge branch (if successful)
git merge feature/new-analysis-method
```

### Undo Changes
```powershell
# Discard changes to a file (before staging)
git checkout -- filename.py

# Unstage a file (after git add, before commit)
git reset HEAD filename.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes) - DANGEROUS!
git reset --hard HEAD~1
```

### Pull Changes from GitHub
```powershell
# Get latest changes from GitHub
git pull

# Or fetch and merge separately
git fetch origin
git merge origin/main
```

## Recommended Commit Message Format

```
[Type]: Brief summary (50 chars or less)

Detailed explanation of what changed and why.
- Bullet points for multiple changes
- Reference issue numbers if applicable

Examples:
- Fix: Correct force threshold in sandwich routine
- Add: SteppedCone batch processing with area plots
- Update: Documentation for sandwich routine safety
- Refactor: Simplify adhesion metrics calculator
- Test: Add unit tests for peak force logger
```

## GitHub Best Practices

### DO:
✅ Commit frequently with clear messages
✅ Push to GitHub regularly (at least daily)
✅ Use .gitignore to exclude large data files
✅ Write descriptive commit messages
✅ Keep commits focused (one feature/fix per commit)
✅ Document major changes in commit messages

### DON'T:
❌ Commit large CSV data files (use .gitignore)
❌ Commit passwords or API keys
❌ Use vague commit messages ("fix stuff", "update")
❌ Commit broken/untested code to main branch
❌ Wait weeks between commits

## Troubleshooting

### "Authentication failed" Error
GitHub no longer allows password authentication. You need a Personal Access Token:

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo` (full control of private repositories)
4. Copy the token
5. When pushing, use token instead of password

Or set up SSH keys (recommended):
```powershell
# Generate SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

# Copy public key
Get-Content ~/.ssh/id_ed25519.pub | clip

# Add to GitHub: Settings → SSH and GPG keys → New SSH key
# Then change remote URL:
git remote set-url origin git@github.com:YOUR_USERNAME/prince-segmented-printing.git
```

### Large File Error
If you accidentally committed large files:
```powershell
# Remove from git but keep file locally
git rm --cached large_file.csv

# Add to .gitignore
echo "large_file.csv" >> .gitignore

# Commit the change
git commit -m "Remove large file from tracking"
```

### Merge Conflicts
If you edited the same file on two computers:
```powershell
# Pull changes
git pull

# If conflict, edit the file to resolve
# Look for <<<<<<, =======, >>>>>> markers
# Keep the version you want
# Remove the markers

# Stage resolved file
git add resolved_file.py

# Complete merge
git commit -m "Resolve merge conflict in resolved_file.py"
```

## Files to Commit (Recommended)

### Always Commit:
- `*.py` - Python source code
- `*.md` - Documentation
- `README.md` - Project readme
- `requirements.txt` - Python dependencies (if you create one)
- Configuration files

### Never Commit:
- `__pycache__/` - Python cache
- `*.csv` - Data files (except small test files)
- `*.png` - Generated plots
- `*.log` - Log files
- Large backup directories
- Virtual environments

### Selective Commit:
- Small test data files (< 1 MB)
- Example output files for documentation
- Configuration templates

## Creating requirements.txt

To help others set up the same Python environment:

```powershell
# If using conda
conda list --export > requirements.txt

# Or create manually
@"
numpy>=1.20.0
pandas>=1.3.0
matplotlib>=3.4.0
scipy>=1.7.0
zaber-motion>=2.0.0
"@ | Out-File -FilePath requirements.txt -Encoding utf8

# Commit it
git add requirements.txt
git commit -m "Add Python package requirements"
git push
```

## Next Steps After Setup

1. **Clone on other computer**:
   ```powershell
   git clone https://github.com/YOUR_USERNAME/prince-segmented-printing.git
   ```

2. **Set up Python environment on new computer**:
   ```powershell
   cd prince-segmented-printing
   conda create -n prince python=3.8
   conda activate prince
   pip install -r requirements.txt
   ```

3. **Keep both computers in sync**:
   - Computer 1: Make changes, commit, push
   - Computer 2: Pull changes before working
   - Repeat

## Summary Commands Quick Reference

```powershell
# Daily workflow
git status                    # Check what changed
git add .                     # Stage all changes
git commit -m "message"       # Commit with message
git push                      # Push to GitHub

# Setup (one-time)
git init                      # Initialize repository
git remote add origin URL     # Connect to GitHub
git push -u origin main       # First push

# Sync between computers
git pull                      # Get latest changes
git push                      # Send your changes

# Check status
git status                    # See what's changed
git log --oneline             # View commit history
git remote -v                 # View remote URLs
```

## Getting Help

```powershell
git help                      # General help
git help commit               # Help for specific command
git status                    # Always a good first step
```
