#!/bin/bash

MSG=${1:-"update: vault notes"}

cp ~/MyVault/02\ -\ System\ Design/Concepts/*.md "vault/02 - System Design/Concepts/"
cp ~/MyVault/02\ -\ System\ Design/Diagrams/*.svg "vault/02 - System Design/Diagrams/"
cp ~/MyVault/02\ -\ System\ Design/ADRs/*.md "vault/02 - System Design/ADRs/"
cp ~/MyVault/01\ -\ Projects/ContentPilot/*.md "vault/01 - Projects/ContentPilot/"

git add .
git commit -m "$MSG"
git push

echo "✓ Vault synced to GitHub"
