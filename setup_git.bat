@echo off
echo ========================================
echo Git Setup Helper for RED Lab
echo ========================================
echo.
echo This script will help you configure Git for pushing to GitHub.
echo.

cd C:\printer_code\dinglab_printer_notebook

echo Step 1: Configure Git username
echo.
set /p username="Enter your Git username (e.g., edwinclement08): "
git config --global user.name "%username%"
echo Username set to: %username%
echo.

echo Step 2: Configure Git email
echo.
set /p email="Enter your Git email (e.g., eclement@wpi.edu): "
git config --global user.email "%email%"
echo Email set to: %email%
echo.

echo Step 3: Verify configuration
echo.
echo Current Git configuration:
git config --global user.name
git config --global user.email
echo.

echo ========================================
echo Git configuration complete!
echo ========================================
echo.
echo Next steps:
echo 1. If this is your first time, you may need to authenticate with GitHub
echo 2. Try running push_to_github.bat again
echo 3. If prompted for credentials, use your GitHub username and Personal Access Token
echo    (NOT your password - create a token at: https://github.com/settings/tokens)
echo.
pause
