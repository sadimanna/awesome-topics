#!/bin/bash
echo $1
# git checkout main && git pull origin main && git merge origin/main
git add . && git commit -m "$1" && git push --force origin main