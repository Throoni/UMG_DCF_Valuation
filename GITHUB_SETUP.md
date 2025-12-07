# GitHub Setup Guide

Your local Git repository has been initialized and the initial commit has been created. Follow these steps to push to GitHub:

## Step 1: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the "+" icon in the top right corner
3. Select "New repository"
4. Repository name: `UMG_DCF_Valuation` (or your preferred name)
5. Description: "DCF Valuation Model for Universal Music Group - CFA Research Challenge"
6. Choose visibility (Public or Private)
7. **DO NOT** initialize with README, .gitignore, or license (we already have these)
8. Click "Create repository"

## Step 2: Connect Local Repository to GitHub

After creating the repository, GitHub will show you commands. Use these commands:

```bash
cd "/Users/gord/Desktop/MBA 1SEM/Financial Analysis and valuation/UMG_Challenge"

# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/UMG_DCF_Valuation.git

# Rename branch to main (if not already)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Alternative: Using SSH

If you have SSH keys set up with GitHub:

```bash
git remote add origin git@github.com:YOUR_USERNAME/UMG_DCF_Valuation.git
git branch -M main
git push -u origin main
```

## Step 3: Verify

After pushing, refresh your GitHub repository page. You should see all your files including:
- All Python modules
- README.md
- .gitignore
- requirements.txt
- tests/
- utils/

## Future Updates

When you make changes to the code:

```bash
# Check what changed
git status

# Add changed files
git add .

# Commit with descriptive message
git commit -m "Description of changes"

# Push to GitHub
git push
```

## Notes

- The `.gitignore` file ensures that generated Excel files, data files, and other temporary files are NOT uploaded to GitHub
- Only source code, configuration, and documentation are tracked
- Your `outputs/` and `data/` directories will be empty in the repository (as intended)

