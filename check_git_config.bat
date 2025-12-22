@echo off
echo ========================================
echo Git Configuration Diagnostic
echo ========================================
echo.

cd C:\printer_code\dinglab_printer_notebook

echo Checking Git installation...
git --version
echo.

echo Checking Git user configuration...
echo User name:
git config user.name
echo User email:
git config user.email
echo.

echo Checking remote repository...
git remote -v
echo.

echo Checking current branch...
git branch
echo.

echo Checking repository status...
git status
echo.

echo Checking if changes are staged...
git diff --cached --name-only
echo.

echo ========================================
echo Diagnostic complete!
echo ========================================
echo.
echo If you see errors above, you may need to:
echo 1. Configure Git username: git config --global user.name "Your Name"
echo 2. Configure Git email: git config --global user.email "your.email@example.com"
echo 3. Authenticate with GitHub (use GitHub Desktop or gh auth login)
echo.
pause
